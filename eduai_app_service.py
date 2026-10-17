"""CSV and configuration boundary for the observed-outcome audit app."""

import csv
from decimal import Decimal, InvalidOperation
from io import StringIO

import pandas as pd

from eduai_report import build_audit_report
from eduai_review_shares import audit_review_shares
from eduai_validated_audit import validate_audit_input


SOURCE_ROW_COLUMN = "__source_row_number__"


def _prepare_frame(frame, target_column, decision_id_columns, use_source_row_number):
    if use_source_row_number:
        if SOURCE_ROW_COLUMN in frame.columns:
            raise ValueError("The reserved source row column already exists.")
        frame = frame.copy()
        frame[SOURCE_ROW_COLUMN] = range(1, len(frame) + 1)
        decision_id_columns = [SOURCE_ROW_COLUMN]
    if target_column in frame.columns and frame[target_column].map(
        lambda value: isinstance(value, str) and not value.strip()
    ).any():
        raise ValueError("The outcome column contains blank values.")
    return frame, decision_id_columns


def preview_uploaded_audit(frame, config):
    """Run notebook input checks without ranking, intervals, or fitting a model."""
    frame, keys = _prepare_frame(frame, config["target_column"], config["decision_id_columns"], config["use_source_row_number"])
    prepared, validation = validate_audit_input(
        frame, **{name: config[name] for name in ("target_column", "positive_value", "negative_values", "excluded_values",
            "score_column", "decision_unit", "entity_id_column", "group_columns")},
        decision_id_columns=keys, review_share=config["focus_share"],
    )
    for column, reference in config["group_references"].items():
        if column not in config["group_columns"] or str(reference) not in prepared[column].astype("object").fillna("Unknown").astype(str).unique():
            raise ValueError(f"Reference group not found in audited rows: {column}")
    return {**validation,
            "positive_records": int(prepared[config["target_column"]].eq(config["positive_value"]).sum()),
            "negative_records": int(prepared[config["target_column"]].isin(config["negative_values"]).sum()),
            "unique_students": int(prepared[config["entity_id_column"]].nunique()) if config["entity_id_column"] else None}


def load_prediction_csv(contents, *, delimiter=",", encoding="utf-8-sig"):
    """Read one CSV without changing row order or silently renaming headers."""
    if not contents:
        raise ValueError("The CSV file is empty.")
    if delimiter not in (",", ";", "\t", "|"):
        raise ValueError("Choose a supported CSV delimiter.")
    if encoding not in ("utf-8-sig", "cp1251"):
        raise ValueError("Choose a supported CSV encoding.")
    try:
        text = contents.decode(encoding)
    except UnicodeError as exc:
        raise ValueError("The file cannot be decoded with the selected encoding.") from exc
    try:
        header = next(csv.reader(StringIO(text), delimiter=delimiter))
    except (csv.Error, StopIteration) as exc:
        raise ValueError("The CSV file has no readable header.") from exc
    if not header or any(not name.strip() for name in header):
        raise ValueError("Every CSV column must have a non-empty name.")
    if len(header) != len(set(header)):
        raise ValueError("The CSV header contains duplicate column names.")
    if SOURCE_ROW_COLUMN in header:
        raise ValueError(f"The CSV column name {SOURCE_ROW_COLUMN} is reserved.")
    try:
        # Preserve IDs and outcome codes exactly, including leading zeros.
        # The validated audit converts only the selected score column to float.
        frame = pd.read_csv(
            StringIO(text), sep=delimiter, dtype=str,
            keep_default_na=False, na_values=[""],
        )
    except (pd.errors.ParserError, UnicodeError) as exc:
        raise ValueError("The CSV file could not be parsed. Check its delimiter and rows.") from exc
    if frame.empty:
        raise ValueError("The CSV file has no data rows.")
    return frame


def parse_review_shares(text):
    """Parse comma-separated percentages into the audit's 0–1 shares."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter at least one review share, such as 15, 20, 30.")
    shares = []
    for part in text.split(","):
        value = part.strip().removesuffix("%").strip()
        try:
            percent = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Review shares must be comma-separated percentages.") from exc
        if not percent.is_finite() or not 0 < percent <= 100:
            raise ValueError("Each review share must be above 0% and at most 100%.")
        shares.append(float(percent / 100))
    if len(shares) != len(set(shares)):
        raise ValueError("Review shares must be unique.")
    return sorted(shares)


def build_uploaded_audit(
    frame, *, dataset_name, target_column, positive_value, negative_values,
    excluded_values, score_column, decision_unit, decision_id_columns,
    entity_id_column, group_columns, group_references, review_shares,
    focus_share, prediction_timing="", outcome_horizon="",
    use_source_row_number=False,
):
    """Run the unchanged notebook audit functions and format their result."""
    frame, decision_id_columns = _prepare_frame(frame, target_column, decision_id_columns, use_source_row_number)
    if focus_share not in review_shares:
        raise ValueError("The report focus share must be one of the compared shares.")
    comparison = audit_review_shares(
        frame,
        target_column=target_column,
        positive_value=positive_value,
        negative_values=negative_values,
        excluded_values=excluded_values,
        score_column=score_column,
        decision_unit=decision_unit,
        decision_id_columns=decision_id_columns,
        entity_id_column=entity_id_column,
        group_columns=group_columns,
        group_references=group_references,
        review_shares=review_shares,
    )
    context = {
        "Prediction Timing": prediction_timing.strip(),
        "Outcome Horizon": outcome_horizon.strip(),
    }
    if use_source_row_number:
        context["Decision Key Note"] = (
            "Technical source row number only; real student identity is not verified."
        )
    report = build_audit_report(
        comparison,
        dataset_name=dataset_name.strip(),
        focus_share=focus_share,
        context=context,
    )
    return comparison, report
