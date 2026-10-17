"""Audit observed outcomes and existing dropout probabilities without fitting a model."""

from decimal import Decimal, ROUND_CEILING

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def _review_count(review_share, records):
    """Round a declared decimal share upward without binary-float artifacts."""
    return int((Decimal(str(review_share)) * records).to_integral_value(rounding=ROUND_CEILING))


def audit_predictions(
    dataset,
    target_column,
    positive_value,
    score_column,
    group_columns=None,
    entity_id_column=None,
    review_share=0.20,
):
    """Audit one scored record per decision unit; scores must be probabilities.

    This function does not split data or fit a model. The caller is responsible
    for supplying predictions made without training on these outcomes.
    New audit submissions should use audit_validated_predictions from
    eduai_validated_audit, which checks outcome mapping and decision keys.
    """
    if not isinstance(dataset, pd.DataFrame) or dataset.empty:
        raise ValueError("dataset must be a non-empty pandas DataFrame")
    if not 0 < review_share <= 1:
        raise ValueError("review_share must be greater than 0 and at most 1")
    if isinstance(group_columns, str):
        group_columns = [group_columns]
    group_columns = list(group_columns or [])
    if len(group_columns) != len(set(group_columns)):
        raise ValueError("group_columns contains duplicates")
    if target_column == score_column or score_column in group_columns:
        raise ValueError("The score column must be separate from outcome and groups")

    required = [target_column, score_column, *group_columns]
    if entity_id_column is not None:
        required.append(entity_id_column)
    missing = [column for column in required if column not in dataset.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if dataset[target_column].isna().any():
        raise ValueError("Target column contains missing values")
    if positive_value not in dataset[target_column].unique():
        raise ValueError(f"Positive value not found: {positive_value}")
    if entity_id_column is not None and dataset[entity_id_column].isna().any():
        raise ValueError("Entity ID column contains missing values")

    try:
        probabilities = pd.to_numeric(dataset[score_column], errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Score column must contain numeric probabilities") from exc
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Score column must contain finite probabilities between 0 and 1")
    actual = dataset[target_column].eq(positive_value).to_numpy(dtype=int)
    if np.unique(actual).size != 2:
        raise ValueError("Dataset must contain both outcome classes")

    records_to_review = _review_count(review_share, len(actual))
    ranked_positions = np.argsort(-probabilities, kind="stable")
    selected = np.zeros(len(actual), dtype=bool)
    selected[ranked_positions[:records_to_review]] = True
    found = int(((actual == 1) & selected).sum())
    false_alarms = int(((actual == 0) & selected).sum())
    total_positives = int((actual == 1).sum())
    review = {
        "review_share_pct": 100 * review_share,
        "records": len(actual),
        "selected_records": records_to_review,
        "found_positives": found,
        "false_alarms": false_alarms,
        "missed_positives": total_positives - found,
        "precision_pct": 100 * found / records_to_review,
        "recall_pct": 100 * found / total_positives,
    }
    if entity_id_column is not None:
        ids = dataset[entity_id_column].to_numpy()
        review["unique_entities_to_review"] = len(np.unique(ids[selected]))

    group_rows = []
    for column in group_columns:
        values = dataset[column].astype("object").fillna("Unknown").astype(str).to_numpy()
        for group_value in np.unique(values):
            in_group = values == group_value
            positives = in_group & (actual == 1)
            negatives = in_group & (actual == 0)
            group_size = int(in_group.sum())
            total_group_positives = int(positives.sum())
            total_group_negatives = int(negatives.sum())
            found_group = int((positives & selected).sum())
            false_group = int((negatives & selected).sum())
            group_rows.append({
                "group_column": column,
                "group_value": group_value,
                "records": group_size,
                "total_positives": total_group_positives,
                "total_negatives": total_group_negatives,
                "positive_rate_pct": 100 * total_group_positives / group_size,
                "selected_records": int((in_group & selected).sum()),
                "selection_rate_pct": 100 * (in_group & selected).sum() / group_size,
                "found_positives": found_group,
                "false_alarms": false_group,
                "recall_pct": (
                    100 * found_group / total_group_positives
                    if total_group_positives else np.nan
                ),
                "false_positive_rate_pct": (
                    100 * false_group / total_group_negatives
                    if total_group_negatives else np.nan
                ),
            })
    group_audit = pd.DataFrame(group_rows)
    minimum_group_records = max(100, int(np.ceil(0.05 * len(actual))))
    minimum_outcomes_per_class = 30
    gap_rows = []
    small_groups = pd.DataFrame(columns=[
        "group_column", "group_value", "records", "total_positives", "total_negatives"
    ])
    if not group_audit.empty:
        size_check = group_audit.copy()
        size_check["passes_size_check"] = (
            (size_check["records"] >= minimum_group_records)
            & (size_check["total_positives"] >= minimum_outcomes_per_class)
            & (size_check["total_negatives"] >= minimum_outcomes_per_class)
        )
        small_groups = size_check.loc[
            ~size_check["passes_size_check"], small_groups.columns
        ]
        for column, groups in size_check.groupby("group_column"):
            comparable = groups[groups["passes_size_check"]]
            if len(comparable) < 2:
                continue
            for metric in ["recall_pct", "false_positive_rate_pct"]:
                lowest = comparable.loc[comparable[metric].idxmin()]
                highest = comparable.loc[comparable[metric].idxmax()]
                gap_rows.append({
                    "group_column": column,
                    "metric": metric,
                    "lowest_group": lowest["group_value"],
                    "lowest_pct": lowest[metric],
                    "highest_group": highest["group_value"],
                    "highest_pct": highest[metric],
                    "gap_pp": highest[metric] - lowest[metric],
                })
    group_gaps = pd.DataFrame(gap_rows)

    calibration_data = pd.DataFrame({"actual": actual, "probability": probabilities})
    if np.unique(probabilities).size == 1:
        calibration_data["risk_band"] = "All probabilities equal"
    else:
        calibration_data["risk_band"] = pd.qcut(
            calibration_data["probability"], q=5, duplicates="drop"
        )
    calibration = (
        calibration_data.groupby("risk_band", observed=True)
        .agg(
            records=("actual", "size"),
            mean_predicted_pct=("probability", lambda values: 100 * values.mean()),
            actual_positive_pct=("actual", lambda values: 100 * values.mean()),
        )
        .reset_index()
    )
    calibration["gap_pp"] = (
        calibration["actual_positive_pct"] - calibration["mean_predicted_pct"]
    )
    return {
        "configuration": {
            "target_column": target_column,
            "positive_value": positive_value,
            "score_column": score_column,
            "entity_id_column": entity_id_column,
            "group_columns": group_columns,
            "review_share": review_share,
            "selection_unit": "record",
        },
        "data": {
            "records": len(actual),
            "positive_rate_pct": 100 * actual.mean(),
        },
        "scores": {
            "roc_auc": roc_auc_score(actual, probabilities),
            "mean_predicted_pct": 100 * probabilities.mean(),
            "observed_positive_pct": 100 * actual.mean(),
        },
        "review": review,
        "group_audit": group_audit,
        "group_gaps": group_gaps,
        "small_groups": small_groups,
        "calibration": calibration,
        "screening_rule": {
            "minimum_group_records": minimum_group_records,
            "minimum_outcomes_per_class": minimum_outcomes_per_class,
            "is_statistical_test": False,
        },
    }
