"""Descriptive comparison of two fixed score columns on one common cohort."""

from copy import deepcopy

import numpy as np
import pandas as pd

from eduai_app_service import _prepare_frame, build_uploaded_audit, preview_uploaded_audit
from eduai_prediction_audit import _review_count
from eduai_validated_audit import validate_audit_input


MODEL_CODES = ("A", "B")
OVERLAP_CATEGORIES = ("both", "only_A", "only_B", "neither")
DIFFERENCE_FIELDS = ("selected_records", "found_positives", "missed_positives", "false_alarms",
                     "recall_pct", "precision_pct", "false_positive_rate_pct")


def validate_comparison_columns(config, score_column_b):
    if not isinstance(score_column_b, str) or not score_column_b.strip():
        raise ValueError("Select a second probability column.")
    if score_column_b == config["score_column"]:
        raise ValueError("Choose two different probability columns.")
    roles = [config["target_column"], config["entity_id_column"], *config["decision_id_columns"], *config["group_columns"]]
    if score_column_b in roles:
        raise ValueError("The second probability column must be separate from outcomes, IDs, and groups.")


def preview_model_comparison(frame, config, score_column_b):
    validate_comparison_columns(config, score_column_b)
    primary = preview_uploaded_audit(frame, config)
    preview_uploaded_audit(frame, {**config, "score_column": score_column_b})
    return primary


def compare_uploaded_predictions(frame, config, score_column_b):
    """Use unchanged notebook audits twice; model differences have no inferential CI."""
    preview_model_comparison(frame, config, score_column_b)
    frame = frame.reset_index(drop=True)
    comparisons, reports = {}, {}
    for model, score in zip(MODEL_CODES, [config["score_column"], score_column_b]):
        comparisons[model], reports[model] = build_uploaded_audit(frame, **{**config, "score_column": score})
    primary, keys = _prepare_frame(frame, config["target_column"], config["decision_id_columns"], config["use_source_row_number"])
    prepared, _ = validate_audit_input(primary, **{name: config[name] for name in (
        "target_column", "positive_value", "negative_values", "excluded_values", "score_column", "decision_unit", "entity_id_column", "group_columns")},
        decision_id_columns=keys, review_share=config["focus_share"])
    actual = prepared[config["target_column"]].eq(config["positive_value"]).to_numpy()
    scores = {"A": prepared[config["score_column"]].to_numpy(dtype=float), "B": prepared[score_column_b].to_numpy(dtype=float)}
    rankings = {model: np.argsort(-values, kind="stable") for model, values in scores.items()}
    records = pd.DataFrame({"source_record": prepared.index.to_numpy() + 1,
                            "observed_outcome": prepared[config["target_column"]].to_numpy(),
                            "score_A": scores["A"], "score_B": scores["B"]})
    identities = list(dict.fromkeys([*keys, *([config["entity_id_column"]] if config["entity_id_column"] else [])]))
    for column in identities:
        records["key:" + column] = prepared[column].to_numpy()
    for column in config["group_columns"]:
        records["group:" + column] = prepared[column].to_numpy()
    overlap, differences, group_differences = [], [], []
    focus_flags = {}
    summaries = {model: audit["summary"].set_index("review_share_pct") for model, audit in comparisons.items()}
    for share in comparisons["A"]["configuration"]["review_shares"]:
        count = _review_count(share, len(prepared))
        flags = {}
        for model in MODEL_CODES:
            flags[model] = np.zeros(len(prepared), dtype=bool)
            flags[model][rankings[model][:count]] = True
        masks = {"both": flags["A"] & flags["B"], "only_A": flags["A"] & ~flags["B"],
                 "only_B": ~flags["A"] & flags["B"], "neither": ~flags["A"] & ~flags["B"]}
        row = {"review_share_pct": 100 * share, "audited_records": len(prepared), "selected_per_model": count}
        for name, mask in masks.items():
            row[name] = int(mask.sum())
            row["positives_" + name] = int((mask & actual).sum())
        overlap.append(row)
        left, right = summaries["A"].loc[100 * share], summaries["B"].loc[100 * share]
        differences.append({"review_share_pct": 100 * share,
                            **{name + "_B_minus_A": right[name] - left[name] for name in DIFFERENCE_FIELDS}})
        group_a = comparisons["A"]["reports"][share]["group_audit"]
        group_b = comparisons["B"]["reports"][share]["group_audit"]
        if not group_a.empty:
            joined = group_a.merge(group_b, on=["group_column", "group_value", "records", "total_positives", "total_negatives"],
                                   suffixes=("_A", "_B"), validate="one_to_one")
            joined.insert(0, "review_share_pct", 100 * share)
            for field in ["selected_records", "found_positives", "false_alarms", "recall_pct", "false_positive_rate_pct"]:
                joined[field + "_B_minus_A"] = joined[field + "_B"] - joined[field + "_A"]
            group_differences.append(joined)
        if share == config["focus_share"]:
            focus_flags = flags
            records["selection_category"] = np.select(list(masks.values()), list(masks), default="neither")
    for model in MODEL_CODES:
        records["selected_" + model] = focus_flags[model]
    summary_parts = []
    for model in MODEL_CODES:
        table = comparisons[model]["summary"].copy()
        table.insert(0, "model", model)
        table.insert(1, "score_column", config["score_column"] if model == "A" else score_column_b)
        summary_parts.append(table)
    return dict(config=deepcopy(config), score_column_b=score_column_b, comparisons=comparisons, reports=reports,
                summary=pd.concat(summary_parts, ignore_index=True), differences=pd.DataFrame(differences),
                overlap=pd.DataFrame(overlap), selection_records=records,
                group_differences=pd.concat(group_differences, ignore_index=True) if group_differences else
                    pd.DataFrame(columns=["review_share_pct", "group_column", "group_value"]))
