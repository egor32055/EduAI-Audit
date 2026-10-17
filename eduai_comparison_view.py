"""Bilingual comparison views and aggregate downloads for two existing predictions."""

from html import escape
from io import BytesIO
import json
import re
from zipfile import ZipFile, ZIP_DEFLATED

import altair as alt
import pandas as pd
import streamlit as st

from eduai_charts import group_chart_data
from eduai_exports import export_tables, table_csv
from eduai_i18n import metric_help, tr
from eduai_report import _report_number, _report_percent
from eduai_report_locale import _metric_tooltips, present_report


TABLE_LABELS = {"summary": "Results for both models", "differences": "Observed differences: B minus A",
                "overlap": "Selection overlap", "group_differences": "Group results for both models"}
CATEGORY_LABELS = {"all": "All decision records", "both": "Selected by both models", "only_A": "Selected only by A",
                   "only_B": "Selected only by B", "neither": "Selected by neither model"}
DIFFERENCE_NOTE = "B minus A describes observed differences on the same cohort. Individual model intervals do not test these differences; paired comparison intervals are not calculated."


def display_comparison_tables(result, language):
    t = lambda text: tr(text, language)
    summary = result["summary"]
    rates = {"precision_pct": "Precision", "recall_pct": "Recall", "false_positive_rate_pct": "False-Positive Rate (FPR)"}
    counts = {"selected_records": "Selected records", "found_positives": "Found cases", "missed_positives": "Missed cases", "false_alarms": "False alarms"}
    overall = pd.DataFrame({t("Model"): summary.model.map(lambda m: t("Model " + m)),
                            t("Score column"): summary.score_column,
                            t("Review shares (%)"): summary.review_share_pct.map(_report_percent)})
    for field, label in counts.items():
        overall[t(label)] = summary[field].map(_report_number)
    for field, label in rates.items():
        overall[label] = summary[field].map(_report_percent)
    diffs = result["differences"]
    differences = pd.DataFrame({t("Review shares (%)"): diffs.review_share_pct.map(_report_percent)})
    for field, label in {**counts, **rates}.items():
        suffix = " (pp)" if field in rates else ""
        differences[(label if field in rates else t(label)) + " B − A" + suffix] = diffs[field + "_B_minus_A"].map(lambda n: f"{n:+.1f}" if field in rates else f"{n:+.0f}")
    overlap = result["overlap"]
    overlaps = pd.DataFrame({t("Review shares (%)"): overlap.review_share_pct.map(_report_percent)})
    for category in CATEGORY_LABELS:
        if category != "all":
            overlaps[t(CATEGORY_LABELS[category])] = overlap[category].map(_report_number)
    groups = result["group_differences"]
    group_table = pd.DataFrame()
    if not groups.empty:
        group_table = pd.DataFrame({t("Review shares (%)"): groups.review_share_pct.map(_report_percent),
                                   t("Group column"): groups.group_column, t("Group"): groups.group_value,
                                   t("Records"): groups.records.map(_report_number)})
        for model in ("A", "B"):
            for field, label in {"selected_records": "Selected records", "found_positives": "Found cases", "false_alarms": "False alarms"}.items():
                group_table[t(label) + " " + model] = groups[field + "_" + model].map(_report_number)
            for field, label in {"recall_pct": "Recall", "false_positive_rate_pct": "False-Positive Rate (FPR)"}.items():
                group_table[label + " " + model] = groups[field + "_" + model].map(_report_percent)
        for field, label in {"recall_pct": "Recall", "false_positive_rate_pct": "False-Positive Rate (FPR)"}.items():
            group_table[label + " B − A (pp)"] = groups[field + "_B_minus_A"].map(lambda n: tr("Metric unavailable", language) if pd.isna(n) else f"{n:+.1f}")
    return {"summary": overall, "differences": differences, "overlap": overlaps, "group_differences": group_table}


def comparison_group_chart(result, feature, metric, language):
    focus = result["config"]["focus_share"]
    parts = []
    for model in ("A", "B"):
        data = group_chart_data(result["comparisons"][model]["reports"][focus], feature, language)
        data = data.loc[data.metric.eq(metric)].copy()
        data["model"] = tr("Model " + model, language)
        parts.append(data)
    data = pd.concat(parts, ignore_index=True)
    label = "Recall" if metric == "recall_pct" else "False-Positive Rate (FPR)"
    groups = list(dict.fromkeys(data.group_value.tolist()))
    base = alt.Chart(data).encode(
        y=alt.Y("group_value:N", title=None, scale=alt.Scale(domain=groups)), yOffset="model:N",
        color=alt.Color("model:N", title=None, scale=alt.Scale(domain=[tr("Model A", language), tr("Model B", language)], range=["#2251A4", "#8C56A2"]), legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("model:N", title=tr("Model", language)), alt.Tooltip("group_value:N", title=tr("Group", language)),
                 alt.Tooltip("estimate_pct:Q", title=label + " (%)", format=".1f"),
                 alt.Tooltip("ci_lower_pct:Q", title=tr("Interval lower bound (%)", language), format=".1f"),
                 alt.Tooltip("ci_upper_pct:Q", title=tr("Interval upper bound (%)", language), format=".1f"),
                 alt.Tooltip("interval_status:N", title=tr("Interval status", language)),
                 alt.Tooltip("denominator_records:Q", title=tr("Relevant outcomes", language)),
                 alt.Tooltip("denominator_units:Q", title=tr("Contributing students", language)),
                 alt.Tooltip("support:N", title=tr("Support note", language))])
    rules = base.mark_rule(strokeWidth=2).encode(x=alt.X("ci_lower_pct:Q", title=label + " (%)", scale=alt.Scale(domain=[0, 100])), x2="ci_upper_pct:Q")
    points = base.mark_point(filled=True, size=70).encode(x=alt.X("estimate_pct:Q", title=label + " (%)", scale=alt.Scale(domain=[0, 100])))
    missing = base.transform_filter("!isValid(datum.estimate_pct)").mark_text(align="left").encode(x=alt.value(5), text=alt.value(tr("Metric unavailable", language)))
    confidence = 100 * result["comparisons"]["A"]["reports"][focus]["uncertainty_configuration"]["confidence_level"]
    return (rules + points + missing).properties(title=f"{label} · {confidence:g}% CI", height=max(320, 160 + 50 * len(groups)))


def comparison_html(result, language):
    t = lambda text: tr(text, language)
    tables = display_comparison_tables(result, language)
    title = t("Prediction comparison") + ": " + result["config"]["dataset_name"]
    parts = [f'<!doctype html><html lang="{language}"><head><meta charset="utf-8"><title>{escape(title)}</title>',
             '<style>body{font-family:Arial,sans-serif;max-width:1400px;margin:auto;padding:24px;line-height:1.5;color:#13233B}table{border-collapse:collapse;font-size:.9em}td,th{padding:6px;border:1px solid #ccd5e3;text-align:left}.audit-table{overflow-x:auto}svg{width:100%;height:auto}details{margin:20px 0}li{margin:8px 0}</style></head><body>',
             '<h1>' + escape(title) + '</h1>', '<p>' + escape(t(DIFFERENCE_NOTE)) + '</p>',
             '<p>' + escape(t("The models share outcomes, exclusions, decision keys, groups, prediction timing and outcome horizon. Equal scores use the original input row order.")) + '</p>']
    for name, table in tables.items():
        if not table.empty:
            parts += ['<h2>' + escape(t(TABLE_LABELS[name])) + '</h2>', '<div class="audit-table">' + table.to_html(index=False, escape=True, border=0) + '</div>']
    for model in ("A", "B"):
        report = present_report(result["reports"][model], result["comparisons"][model], language)
        body = re.search(r"<body[^>]*>(.*?)</body>", report["html"], re.S).group(1)
        parts.append('<details><summary>' + escape(t("Full audit for model " + model)) + '</summary>' + body + '</details>')
    return _metric_tooltips(''.join(parts) + '</body></html>', language)


def comparison_zip(result):
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name in TABLE_LABELS:
            archive.writestr(name + ".csv", table_csv(result[name]))
        for model in ("A", "B"):
            for name, table in export_tables(result["comparisons"][model], result["reports"][model]).items():
                archive.writestr("model_" + model + "/" + name + ".csv", table_csv(table))
        archive.writestr("manifest.json", json.dumps({"application": "EduAI-Audit", "version": 1,
            "configuration": result["config"], "score_column_b": result["score_column_b"],
            "encoding": "UTF-8 with BOM", "notes": DIFFERENCE_NOTE,
            "selection_records_included": False}, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def render_model_comparison(result, language, select, show_table, key):
    t = lambda text, **values: tr(text, language, **values)
    focus = result["config"]["focus_share"]
    st.header(t("4. Prediction comparison"))
    st.caption(t("Model A: {column_a}. Model B: {column_b}.", column_a=result["config"]["score_column"], column_b=result["score_column_b"]))
    overlap = result["overlap"].loc[lambda frame: frame.review_share_pct.eq(100 * focus)].iloc[0]
    st.write(t("At {share}%, each model selects {selected} of {records} audited decision records.", share=f"{100 * focus:g}", selected=int(overlap.selected_per_model), records=int(overlap.audited_records)))
    for area, name in zip(st.columns(4), ["both", "only_A", "only_B", "neither"]):
        area.metric(t(CATEGORY_LABELS[name]), f"{int(overlap[name]):,}")
    for area, name in zip(st.columns(3), ["Recall", "Precision", "False-Positive Rate"]):
        area.markdown("**" + name + "**", help=metric_help(name, language))
    tables = display_comparison_tables(result, language)
    focus_masks = {name: result[name].review_share_pct.eq(100 * focus) if not result[name].empty else [] for name in TABLE_LABELS}
    for name in ("summary", "differences"):
        st.subheader(t(TABLE_LABELS[name]))
        show_table(tables[name].loc[focus_masks[name]], language)
    st.caption(t(DIFFERENCE_NOTE))
    with st.expander(t("Results at all review shares")):
        for name in ("summary", "differences", "overlap"):
            st.write(t(TABLE_LABELS[name]))
            show_table(tables[name], language)
    if result["config"]["decision_unit"] != "student":
        st.caption(t("Overlap counts decision records, not distinct students; one student may have several records."))
    if not tables["group_differences"].empty:
        st.subheader(t("Group results for both models"))
        feature = select(t("Compare groups by"), result["config"]["group_columns"], key("comparison_feature"), result["config"]["group_columns"][0])
        for area, metric in zip(st.columns(2), ["recall_pct", "false_positive_rate_pct"]):
            area.altair_chart(comparison_group_chart(result, feature, metric, language), width="stretch")
        show_table(tables["group_differences"].loc[focus_masks["group_differences"]], language)
    with st.expander(t("Which decision records were selected?")):
        category = select(t("Selection category"), list(CATEGORY_LABELS), key("selection_category"), "only_A",
                          format_func=lambda value: t(CATEGORY_LABELS[value]))
        records = result["selection_records"]
        if category != "all":
            records = records.loc[records.selection_category.eq(category)]
        st.caption(t("Source record numbers refer to data rows before exclusions. Key columns identify the submitted decisions; technical row keys do not verify real student identity."))
        displayed = records.copy()
        displayed["selection_category"] = displayed.selection_category.map(lambda value: t(CATEGORY_LABELS[value]))
        labels = {"source_record": t("Source record"), "observed_outcome": t("Observed outcome"),
                  "score_A": t("Probability A"), "score_B": t("Probability B"), "selected_A": t("Selected A"),
                  "selected_B": t("Selected B"), "selection_category": t("Selection category")}
        labels.update({c: t("Key") + " · " + c[4:] for c in records.columns if c.startswith("key:")})
        labels.update({c: t("Group") + " · " + c[6:] for c in records.columns if c.startswith("group:")})
        st.dataframe(displayed.rename(columns=labels), hide_index=True, width="stretch")
        st.download_button(t("Download these decision records CSV"), table_csv(records), "comparison-" + category + ".csv", "text/csv", key="selection_csv", on_click="ignore")
    st.download_button(t("Download comparison HTML report"), comparison_html(result, language).encode("utf-8"),
                       "eduai-model-comparison-" + language + ".html", "text/html", key="comparison_html", on_click="ignore")
    file_area, zip_area = st.columns(2)
    name = select(t("Comparison table to download"), list(TABLE_LABELS), key("comparison_export"), "summary", format_func=lambda value: t(TABLE_LABELS[value]))
    file_area.download_button(t("Download comparison table CSV"), table_csv(result[name]), "comparison-" + name + ".csv", "text/csv", key="comparison_csv", on_click="ignore")
    zip_area.download_button(t("Download comparison tables ZIP"), comparison_zip(result), "eduai-model-comparison.zip", "application/zip", key="comparison_zip", on_click="ignore")
