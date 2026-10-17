"""Validated entry point for auditing existing dropout probabilities."""

from numbers import Real

import numpy as np
import pandas as pd

from eduai_prediction_audit import audit_predictions
from eduai_uncertainty import calculate_audit_uncertainty


def _column_list(value, name, allow_empty=False):
    if isinstance(value, str):
        value = [value]
    if value is None:
        value = []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a column name or a list of column names")
    columns = list(value)
    if (not columns and not allow_empty) or any(
        not isinstance(c, str) or not c.strip() for c in columns
    ):
        raise ValueError(f"{name} must contain non-empty column names")
    if len(columns) != len(set(columns)):
        raise ValueError(f"{name} contains duplicate column names")
    return columns


def _outcome_values(value, name, allow_empty=False):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be an explicit list of outcome values")
    values = list(value)
    if not values and not allow_empty:
        raise ValueError(f"{name} must not be empty")
    for label in values:
        if not pd.api.types.is_scalar(label) or pd.isna(label):
            raise ValueError(f"{name} must contain non-missing scalar values")
    if len(pd.Index(values).unique()) != len(values):
        raise ValueError(f"{name} contains duplicate values")
    return values


def validate_audit_input(
    dataset, *, target_column, positive_value, negative_values,
    score_column, decision_unit, decision_id_columns,
    group_columns=None, entity_id_column=None, excluded_values=(),
    review_share=0.20,
):
    """Validate all submitted rows, then explicitly exclude declared outcomes.

    The key must identify one decision within the submitted batch. For student
    decisions with an entity ID, that ID must itself be unique. This function
    cannot verify that supplied IDs or outcome meanings are factually correct.
    Missing outcomes are rejected; this is the observed-outcome audit mode.
    """
    if not isinstance(dataset, pd.DataFrame) or dataset.empty:
        raise ValueError("dataset must be a non-empty pandas DataFrame")
    if not dataset.columns.is_unique:
        raise ValueError("Dataset contains duplicate column names")
    if isinstance(review_share, (bool, np.bool_)) or not isinstance(review_share, Real) or not np.isfinite(review_share) or not 0 < review_share <= 1:
        raise ValueError("review_share must be a finite number greater than 0 and at most 1")
    if decision_unit not in ("student", "course_enrollment", "student_period", "record"):
        raise ValueError("decision_unit must be student, course_enrollment, student_period, or record")
    if not pd.api.types.is_scalar(positive_value) or pd.isna(positive_value):
        raise ValueError("positive_value must be a non-missing scalar")
    negative_values = _outcome_values(negative_values, "negative_values")
    excluded_values = _outcome_values(excluded_values, "excluded_values", allow_empty=True)
    all_labels = [positive_value, *negative_values, *excluded_values]
    if len(pd.Index(all_labels).unique()) != len(all_labels):
        raise ValueError("Positive, negative, and excluded outcomes must not overlap")
    keys = _column_list(decision_id_columns, "decision_id_columns")
    groups = _column_list(group_columns, "group_columns", allow_empty=True)
    _column_list([target_column, score_column], "target_column and score_column")
    if entity_id_column is not None:
        _column_list(entity_id_column, "entity_id_column")
        if not isinstance(entity_id_column, str):
            raise ValueError("entity_id_column must be one column name")
    if target_column in groups or score_column in groups:
        raise ValueError("Outcome and score columns must be separate from group columns")
    if {target_column, score_column}.intersection(keys):
        raise ValueError("Decision keys must be separate from outcome and score columns")
    if entity_id_column in {target_column, score_column}:
        raise ValueError("Entity ID must be separate from outcome and score columns")
    required = list(dict.fromkeys([
        target_column, score_column, *keys, *groups,
        *([entity_id_column] if entity_id_column is not None else []),
    ]))
    missing = [column for column in required if column not in dataset.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if dataset[target_column].isna().any():
        raise ValueError("Target column contains missing outcomes; resolve them before auditing")
    unknown = ~dataset[target_column].isin(all_labels)
    if unknown.any():
        raise ValueError(f"{int(unknown.sum())} rows contain unmapped outcomes; declare them as positive, negative, or excluded")
    id_columns = list(dict.fromkeys(keys + ([entity_id_column] if entity_id_column else [])))
    for column in id_columns:
        values = dataset[column]
        blank = values.map(lambda v: isinstance(v, str) and not v.strip())
        if values.isna().any() or blank.any():
            raise ValueError(f"ID column contains missing or blank values: {column}")
    if dataset.duplicated(keys).any():
        raise ValueError("Duplicate decision keys; supply one row per decision unit")
    if decision_unit == "student" and entity_id_column is not None and dataset[entity_id_column].duplicated().any():
        raise ValueError("Student audit contains repeated entity IDs; aggregate or correct the records explicitly")
    if dataset[score_column].map(lambda v: isinstance(v, (bool, np.bool_))).any():
        raise ValueError("Scores must be probabilities, not boolean predictions")
    try:
        scores = pd.to_numeric(dataset[score_column], errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Score column must contain numeric probabilities") from exc
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Score column must contain finite probabilities between 0 and 1")
    excluded = dataset[target_column].isin(excluded_values)
    prepared = dataset.loc[~excluded].copy()
    prepared[score_column] = scores[~excluded.to_numpy()]
    if prepared[target_column].eq(positive_value).nunique() != 2:
        raise ValueError("Audited rows must contain both outcome classes after exclusions")
    validation = {
        "input_records": len(dataset),
        "audited_records": len(prepared),
        "excluded_records": int(excluded.sum()),
        "excluded_outcome_counts": dataset.loc[excluded, target_column].value_counts().to_dict(),
        "missing_group_records": {c: int(prepared[c].isna().sum()) for c in groups},
        "selection_population": "Audited rows after explicit outcome exclusions",
        "decision_unit": decision_unit,
        "decision_id_columns": keys,
        "identity_check": "Supplied decision keys are unique; real-world identity is not verified",
    }
    return prepared, validation


def audit_validated_predictions(
    dataset, *, target_column, positive_value, negative_values,
    score_column, decision_unit, decision_id_columns,
    group_columns=None, entity_id_column=None, excluded_values=(),
    review_share=0.20,
    confidence_level=0.95, n_resamples=2000, random_state=42,
    group_references=None,
):
    """Audit existing probabilities after checking explicit input rules.

    Excluded outcomes do not enter ranking, review capacity, or error metrics.
    Scores must estimate the positive outcome, using information available at
    prediction time. Validation cannot establish their provenance or horizon.
    """
    prepared, validation = validate_audit_input(
        dataset, target_column=target_column, positive_value=positive_value,
        negative_values=negative_values, score_column=score_column,
        decision_unit=decision_unit, decision_id_columns=decision_id_columns,
        group_columns=group_columns, entity_id_column=entity_id_column,
        excluded_values=excluded_values, review_share=review_share,
    )
    report = audit_predictions(
        prepared, target_column=target_column, positive_value=positive_value,
        score_column=score_column, group_columns=group_columns,
        entity_id_column=entity_id_column, review_share=review_share,
    )
    report["configuration"].update({
        "negative_values": list(negative_values),
        "excluded_values": list(excluded_values),
        "selection_unit": decision_unit,
        "decision_id_columns": list(validation["decision_id_columns"]),
    })
    report["input_validation"] = validation
    report.update(calculate_audit_uncertainty(
        prepared, target_column=target_column, positive_value=positive_value,
        score_column=score_column, decision_unit=decision_unit,
        group_columns=group_columns, entity_id_column=entity_id_column,
        review_share=review_share, confidence_level=confidence_level,
        n_resamples=n_resamples, random_state=random_state,
        group_references=group_references,
    ))
    return report
