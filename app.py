"""Bilingual local interface for audits of existing probability predictions."""

import hashlib
from pathlib import Path

import streamlit as st

from eduai_app_service import build_uploaded_audit, load_prediction_csv, parse_review_shares
from eduai_charts import capacity_chart
from eduai_i18n import error_text, tr
from eduai_presets import PRESETS, preset_defaults
from eduai_report_locale import present_report


def result_signature(parts):
    return hashlib.sha256(repr(parts).encode("utf-8")).hexdigest()


def select(label, options, key, default=None, **kwargs):
    """Retain valid canonical values when the display language changes."""
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default if default in options else options[0]
    if None in options and "format_func" in kwargs:
        kwargs.setdefault("placeholder", kwargs["format_func"](None))
    return st.selectbox(label, options, key=key, **kwargs)


def multi(label, options, key, default=(), language="en", **kwargs):
    values = st.session_state.get(key, list(default))
    st.session_state[key] = [value for value in values if value in options]
    return st.multiselect(label, options, key=key, placeholder=tr("Choose values", language), **kwargs)


def main():
    st.set_page_config(page_title="EduAI Audit", page_icon="📊", layout="wide")
    title_area, language_area = st.columns([4, 1])
    with language_area:
        language = st.selectbox("Language / Язык", ["en", "ru"],
                                format_func=lambda value: {"en": "English", "ru": "Русский"}[value], key="language")
    t = lambda text, **values: tr(text, language, **values)
    with title_area:
        st.title("EduAI Audit")
    st.write(t("Audit existing probability predictions against observed outcomes. Compare review capacities, inspect group results, and download a report."))
    st.caption(t("This app does not train a model or recommend a review capacity."))

    st.header(t("1. Upload predictions and outcomes"))
    left, right = st.columns([2, 1])
    with left:
        uploaded = st.file_uploader(t("CSV file"), type="csv", key="upload_file",
                                   help=t("One row per decision; include existing probabilities and observed outcomes."))
    with right:
        delimiter = st.selectbox(t("Delimiter"), [",", ";", "\t", "|"], key="delimiter",
                                format_func=lambda value: t({",": "Comma", ";": "Semicolon", "\t": "Tab", "|": "Pipe"}[value]))
        encoding = st.selectbox(t("Encoding"), ["utf-8-sig", "cp1251"], key="encoding",
                               format_func=lambda value: {"utf-8-sig": "UTF-8", "cp1251": "Windows-1251"}[value])
    sample_path = Path(__file__).parent / "examples" / "sample_predictions.csv"
    if uploaded is None:
        st.info(t("Upload a CSV file to configure an audit."))
        st.download_button(t("Download sample CSV"), sample_path.read_bytes(), "sample_predictions.csv", "text/csv", key="sample_download")
        st.caption(t("The sample contains synthetic data. Select the Synthetic example preset after uploading it."))
        return

    file_bytes = uploaded.getvalue()
    file_digest = hashlib.sha256(file_bytes).hexdigest()
    try:
        frame = load_prediction_csv(file_bytes, delimiter=delimiter, encoding=encoding)
    except ValueError as exc:
        st.error(error_text(exc, language))
        return
    st.success(t("Loaded {rows} rows and {columns} columns.", rows=f"{len(frame):,}", columns=len(frame.columns)))
    if len(frame.columns) == 1:
        st.warning(t("Only one column was found. Check the delimiter if you expected several columns."))
    with st.expander(t("Preview the first 10 rows")):
        st.dataframe(frame.head(10), width="stretch", hide_index=True)

    st.header(t("2. Configure the audit"))
    preset_id = st.selectbox(t("Configuration preset"), list(PRESETS), key="preset_id",
                            format_func=lambda value: t(PRESETS[value]["name"]))
    st.caption(t("Presets fill matching fields from PROTOTYPE. Review them for your file; every field remains editable."))
    if preset_id in {"upv_2022", "oulad", "uci"}:
        st.info(t({
            "upv_2022": "UPV 2022 requires one prepared row per student. Raw course rows must be checked and aggregated before prediction export.",
            "oulad": "OULAD selects course enrollments. One student may have several enrollments; use the composite decision key and student ID.",
            "uci": "UCI has no verified student identifier. A Source Row ID or an explicitly chosen technical row key cannot establish real student identity.",
        }[preset_id]))
    defaults = preset_defaults(preset_id, frame)
    prefix = file_digest[:16] + ":" + preset_id
    key = lambda name: prefix + ":" + name
    columns = frame.columns.tolist()
    preset = PRESETS[preset_id]
    expected = [c for c in [preset["target"], *preset["keys"]] if c]
    missing = [column for column in expected if column not in columns]
    if missing:
        st.warning(t("The selected preset could not find these expected columns: {columns}. Select available mappings or upload a prepared prediction export.", columns=", ".join(missing)))
    name_default = uploaded.name.rsplit(".", 1)[0] if preset_id == "custom" else preset["name"]
    dataset_name = st.text_input(t("Dataset name"), value=name_default, key=key("name"))
    mapping_left, mapping_right = st.columns(2)
    with mapping_left:
        target_column = select(t("Observed outcome column"), [None, *columns], key("target"), defaults["target_column"],
                               format_func=lambda value: value if value is not None else t("Select a column"))
    with mapping_right:
        score_column = select(t("Positive-outcome probability column"), [None, *columns], key("score"), defaults["score_column"],
                              format_func=lambda value: value if value is not None else t("Select a column"),
                              help=t("Scores must be existing probabilities from 0 to 1 for the positive outcome."))
    if score_column is None:
        st.warning(t("No recognized prediction column was found. Choose an existing probability column if it has another name. Raw dataset features are not prediction probabilities."))
        if preset_id in {"upv_2022", "oulad", "uci"}:
            with st.expander(t("How to export ready predictions from PROTOTYPE")):
                st.write(t("After the notebook's Input validation section has completed, run this cell in Colab and upload the downloaded CSV. It exports existing held-out scores without fitting another model."))
                filename = preset_id + "_predictions.csv"
                st.code(f'from google.colab import files\n\nvalidated_predictions[{preset["name"]!r}].to_csv({filename!r}, index=False)\nfiles.download({filename!r})', language="python")

    outcome_values = frame[target_column].dropna().unique().tolist() if target_column else []
    if target_column and frame[target_column].isna().any():
        st.warning(t("The outcome column contains missing values. Resolve them in the CSV before auditing."))
    if target_column and not outcome_values:
        st.warning(t("No observed outcome values were found."))
    positive_value = select(t("Positive outcome"), [None, *outcome_values], key("positive"), defaults["positive_value"],
                            format_func=lambda value: t("Select a value") if value is None else str(value),
                            help=t("Positive means the event being audited, such as dropout; it does not mean a desirable outcome."))
    remaining = [v for v in outcome_values if v != positive_value]
    negative_values = multi(t("Negative outcomes"), remaining, key("negative"), defaults["negative_values"], language=language,
                            help=t("Explicitly select the resolved outcomes that count as negative."))
    excluded_values = multi(t("Excluded outcomes"), [v for v in remaining if v not in negative_values], key("excluded"), defaults["excluded_values"], language=language,
                            help=t("These rows are counted, then removed before ranking and metric calculations."))
    st.caption(t("Every outcome value must be assigned to positive, negative, or excluded. Missing outcomes are rejected."))
    unmapped = [v for v in remaining if v not in negative_values and v not in excluded_values]
    if unmapped:
        st.warning(t("Unmapped outcomes: {values}.", values=", ".join(map(str, unmapped[:20]))))

    unit_left, unit_right = st.columns(2)
    with unit_left:
        decision_unit = select(t("Decision unit"), ["student", "course_enrollment", "student_period", "record"], key("unit"), defaults["decision_unit"],
                               format_func=lambda value: t(value.replace("_", " ").title()),
                               help=t("What does one CSV row represent? For prepared UPV 2022 this is a student; for OULAD it is a course enrollment."))
    id_options = [c for c in columns if c not in (target_column, score_column)]
    with unit_right:
        entity_id_column = select(t("Student ID column (optional)"), [None, *id_options], key("entity"), defaults["entity_id_column"],
                                  format_func=lambda value: t("Not supplied") if value is None else value,
                                  help=t("Needed to account for repeated records from the same student. Without it, intervals for non-student units are unavailable."))
    use_source_row_number = st.checkbox(t("Use source row number as a technical decision key"), key=key("row_key"),
                                       help=t("Use only when the CSV has no decision ID. Row order is preserved, but this cannot verify real student identity or duplicate students."))
    if use_source_row_number:
        decision_id_columns = []
        st.caption(t("The report will identify the technical key and its identity limitation."))
    else:
        decision_id_columns = multi(t("Decision key columns"), id_options, key("keys"), defaults["decision_id_columns"], language=language,
                                   help=t("Choose columns that together identify one decision. Duplicate or missing keys stop the audit."))
    group_options = [c for c in id_options if c != entity_id_column and c not in decision_id_columns]
    group_columns = multi(t("Group columns (optional)"), group_options, key("groups"), defaults["group_columns"], language=language,
                          help=t("Missing group values remain visible as Unknown in the audit."))
    references = {}
    if group_columns:
        st.write(t("Reference groups for signed comparisons (optional)"))
        st.caption(t("A reference is the baseline for differences: other group minus reference. It does not change scores, selections, or group metrics. For example, TP recall 40% minus TC recall 50% gives −10 percentage points."))
        for column in group_columns:
            group = frame.loc[~frame[target_column].isin(excluded_values), column] if target_column else frame[column]
            values = sorted(group.astype("object").fillna("Unknown").astype(str).unique().tolist())
            reference = select(t("Reference for {column}", column=column), [None, *values], key("reference:" + column), defaults["group_references"].get(column),
                               format_func=lambda value: t("No reference") if value is None else value)
            if reference is not None:
                references[column] = reference

    shares_text = st.text_input(t("Review shares (%)"), value="15, 20, 30", key=key("shares"),
                                help=t("Enter percentages separated by commas. Selection counts round upward after exclusions."))
    try:
        shares = parse_review_shares(shares_text)
    except ValueError as exc:
        st.error(error_text(exc, language))
        shares = []
    focus_share = select(t("Report focus share"), shares, key("focus"), 0.20,
                         format_func=lambda value: f"{100 * value:g}%") if shares else None
    st.caption(t("The focus share controls detailed group results. It is not a recommended capacity."))
    with st.expander(t("Dataset context (optional)")):
        timing = st.text_input(t("When were the predictions produced?"), key=key("timing"), placeholder=t("For example: at enrollment"))
        horizon = st.text_input(t("What outcome period do they cover?"), key=key("horizon"), placeholder=t("For example: by the end of the first year"))
        st.caption(t("These descriptions are supplied by you; the app cannot verify prediction timing or outcome definitions."))

    signature = result_signature((file_digest, delimiter, encoding, dataset_name, target_column, score_column,
                                  positive_value, negative_values, excluded_values, decision_unit, entity_id_column,
                                  use_source_row_number, decision_id_columns, group_columns, references, shares, focus_share, timing, horizon))
    st.header(t("3. Run audit"))
    if st.button(t("Run audit"), type="primary", key="run_audit", disabled=not shares):
        st.session_state.pop("audit_result_v2", None)
        if target_column is None or score_column is None or positive_value is None:
            st.error(t("Select the outcome, probability, and positive-outcome fields."))
        elif not negative_values:
            st.error(t("Select at least one negative outcome."))
        elif not use_source_row_number and not decision_id_columns:
            st.error(t("Select decision key columns or explicitly use source row numbers."))
        elif unmapped:
            st.error(t("Unmapped outcomes: {values}.", values=", ".join(map(str, unmapped[:20]))))
        else:
            try:
                with st.spinner(t("Calculating audit metrics and uncertainty intervals...")):
                    comparison, report = build_uploaded_audit(
                        frame, dataset_name=dataset_name, target_column=target_column,
                        positive_value=positive_value, negative_values=negative_values,
                        excluded_values=excluded_values, score_column=score_column, decision_unit=decision_unit,
                        decision_id_columns=decision_id_columns, entity_id_column=entity_id_column,
                        group_columns=group_columns, group_references=references, review_shares=shares,
                        focus_share=focus_share, prediction_timing=timing, outcome_horizon=horizon,
                        use_source_row_number=use_source_row_number,
                    )
                st.session_state["audit_result_v2"] = dict(signature=signature, comparison=comparison, report=report)
            except ValueError as exc:
                st.error(error_text(exc, language))

    saved = st.session_state.get("audit_result_v2")
    if not saved or saved["signature"] != signature:
        return
    comparison = saved["comparison"]
    report = present_report(saved["report"], comparison, language)
    review = comparison["reports"][focus_share]["review"]
    st.header(t("4. Results and report"))
    st.success(t("Audit complete. Results describe the submitted, outcome-filtered records."))
    areas = st.columns(5)
    for area, label, field in zip(areas,
        ["Audited records", "Selected records", "Found cases", "Missed cases", "False alarms"],
        ["records", "selected_records", "found_positives", "missed_positives", "false_alarms"]):
        area.metric(t(label), f"{review[field]:,}")
    st.subheader(t("Key findings"))
    for finding in report["findings"]:
        st.write("• " + finding["text"])

    st.subheader(t("Counts across review shares"))
    st.altair_chart(capacity_chart(comparison["summary"], "counts", language), width="stretch")
    st.subheader(t("Metrics across review shares"))
    st.altair_chart(capacity_chart(comparison["summary"], "rates", language), width="stretch")
    st.caption(t("Recall = found / all positive cases. Precision = found / selected. False-positive rate = false alarms / all negative cases."))
    st.caption(t("Lines connect observed results at the declared shares. They do not select an optimal capacity. Intervals and support notes are in the tables."))
    for title, table_key in [("Review capacities", "capacity_results"), ("Additional workload", "marginal_changes"),
                             ("Group comparisons at the focus share", "group_comparisons")]:
        if not report["tables"][table_key].empty:
            st.subheader(t(title))
            st.dataframe(report["tables"][table_key], width="stretch", hide_index=True)
    for title, table_key in [("Data and scope", "scope"), ("Group counts", "group_counts"),
                             ("Group metrics and uncertainty", "group_uncertainty")]:
        with st.expander(t(title)):
            if report["tables"][table_key].empty:
                st.write(t("No results for this section."))
            else:
                st.dataframe(report["tables"][table_key], width="stretch", hide_index=True)
    with st.expander(t("Reading notes and limits")):
        for note in report["limitations"]:
            st.write("• " + note)
    st.download_button(t("Download full HTML report"), report["html"].encode("utf-8"),
                       file_name=f"eduai-audit-report-{language}.html", mime="text/html", key="report_download")


if __name__ == "__main__":
    main()
