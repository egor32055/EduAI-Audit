"""Build a readable, deterministic report from an existing capacity audit."""

from html import escape
from numbers import Real

import numpy as np
import pandas as pd


def _report_number(value):
    return "Unavailable" if pd.isna(value) else f"{value:,.0f}".replace(",", " ")


def _report_percent(value):
    return "Unavailable" if pd.isna(value) else f"{value:.1f}%"


def _report_quantity(value, singular):
    return f"{_report_number(value)} {singular if value == 1 else singular + 's'}"


def _report_interval(row, prefix=None, difference=False):
    status = row[f"{prefix}_ci_status"] if prefix else row["ci_status"]
    if status != "Available":
        return "Unavailable"
    suffix = "pp" if difference else "pct"
    low = row[f"{prefix}_ci_lower_pct"] if prefix else row[f"ci_lower_{suffix}"]
    high = row[f"{prefix}_ci_upper_pct"] if prefix else row[f"ci_upper_{suffix}"]
    if not np.isfinite([low, high]).all():
        return "Unavailable"
    return f"{low:+.1f} to {high:+.1f} pp" if difference else f"{low:.1f}% to {high:.1f}%"


def build_audit_report(comparison, *, dataset_name, focus_share,
                       column_labels=None, group_labels=None, context=None):
    """Format existing results and describe them using explicit factual rules.

    No model, probability, metric, interval, or optimal policy is calculated here.
    focus_share must be supplied and must already exist in the capacity audit.
    Optional context is provider-supplied descriptive text, not verified evidence.
    Tables retain original source codes unless display labels are supplied.
    """
    if not isinstance(dataset_name, str) or not dataset_name.strip():
        raise ValueError("dataset_name must be a non-empty string")
    if isinstance(focus_share, (bool, np.bool_)) or not isinstance(focus_share, Real) or not np.isfinite(focus_share):
        raise ValueError("focus_share must be a finite numeric share present in the audit")
    required = ["configuration", "input_validation", "summary", "reports", "marginal_changes"]
    if not isinstance(comparison, dict) or any(key not in comparison for key in required):
        raise ValueError("comparison must be an audit_review_shares result")
    if not isinstance(comparison["reports"], dict) or focus_share not in comparison["reports"]:
        raise ValueError("focus_share is not present in the capacity audit")
    if not isinstance(comparison["summary"], pd.DataFrame) or comparison["summary"].empty:
        raise ValueError("The capacity summary must be a non-empty DataFrame")
    for name, mapping in [("column_labels", column_labels), ("group_labels", group_labels), ("context", context)]:
        if mapping is not None and not isinstance(mapping, dict):
            raise ValueError(f"{name} must be a dictionary")
    columns = column_labels or {}
    labels = group_labels or {}
    context = context or {}
    if any(not isinstance(mapping, dict) for mapping in labels.values()):
        raise ValueError("group_labels must map column names to dictionaries of value labels")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in context.items()):
        raise ValueError("context must contain text keys and text values")
    focus = comparison["reports"][focus_share]
    config, validation = focus["configuration"], comparison["input_validation"]
    uncertainty = focus["uncertainty_configuration"]
    review = focus["review"]
    summary = comparison["summary"].copy()
    selected_summary = summary.loc[np.isclose(summary.review_share_pct, 100 * focus_share, rtol=0, atol=1e-10)]
    if len(selected_summary) != 1:
        raise ValueError("The focus share must have exactly one summary row")
    focus_row = selected_summary.iloc[0]
    if focus_row.selected_records != review["selected_records"] or focus_row.records != validation["audited_records"]:
        raise ValueError("Focus summary, individual audit, and audited population disagree")
    unit = config["selection_unit"]
    unit_noun = {"student": "student", "course_enrollment": "course enrollment",
                 "student_period": "student-period record", "record": "record"}.get(unit, "record")
    confidence_label = f"{100 * uncertainty['confidence_level']:g}% CI"
    metric_labels = {"recall_pct": "Recall", "false_positive_rate_pct": "False-Positive Rate"}

    def feature_label(column):
        return str(columns.get(column, column))

    def value_label(column, value):
        return str(labels.get(column, {}).get(value, value))

    def joined(values):
        return ", ".join(map(str, values)) or "None"

    scope_rows = [
        ("Dataset", dataset_name), ("Input Records", _report_number(validation["input_records"])),
        ("Excluded Records", _report_number(validation["excluded_records"])),
        ("Audited Records", _report_number(validation["audited_records"])),
        ("Decision Unit", unit.replace("_", " ").title()),
        ("Outcome Column", config["target_column"]), ("Positive Outcome", str(config["positive_value"])),
        ("Negative Outcomes", joined(config["negative_values"])),
        ("Excluded Outcomes", joined(config["excluded_values"])),
        ("Decision Key", joined(config["decision_id_columns"])),
        ("Student ID Column", config["entity_id_column"] or "Not supplied"),
        ("Group Features", ", ".join(feature_label(c) for c in config["group_columns"]) or "None"),
        ("Score Column", config["score_column"]), ("Focus Review Share", _report_percent(100 * focus_share)),
        ("Actual Selected Share", _report_percent(focus_row.actual_review_share_pct)),
        ("Compared Review Shares", ", ".join(_report_percent(100 * s) for s in comparison["configuration"]["review_shares"])),
        ("Confidence Level", _report_percent(100 * uncertainty["confidence_level"])),
        ("Interval Method", uncertainty["method"]),
        ("Bootstrap Resamples", _report_number(uncertainty["n_resamples"]) if uncertainty["n_resamples"] else "Not used"),
        ("Resampling Seed", str(uncertainty["random_state"]) if uncertainty["n_resamples"] else "Not used"),
        ("Reference Groups", ", ".join(f"{feature_label(c)}: {value_label(c, v)}" for c, v in uncertainty["group_references"].items()) or "None"),
        ("Capacity Rounding", comparison["configuration"]["rounding_rule"]),
        ("Equal-Score Rule", comparison["configuration"]["tie_rule"]),
        ("Prediction Timing", context.get("Prediction Timing") or "Not supplied"),
        ("Outcome Horizon", context.get("Outcome Horizon") or "Not supplied"),
    ]
    scope_rows.extend((key, value) for key, value in context.items() if key not in {"Prediction Timing", "Outcome Horizon"})
    capacity_rows = []
    for _, row in summary.iterrows():
        capacity_rows.append({
            "Review Share": _report_percent(row.review_share_pct),
            "Selected Records": _report_number(row.selected_records),
            "Found Cases": _report_number(row.found_positives),
            "Missed Cases": _report_number(row.missed_positives),
            "False Alarms": _report_number(row.false_alarms),
            "Precision": _report_percent(row.precision_pct), "Recall": _report_percent(row.recall_pct),
            f"Recall {confidence_label}": _report_interval(row, "recall"),
            "False-Positive Rate": _report_percent(row.false_positive_rate_pct),
            f"False-Positive Rate {confidence_label}": _report_interval(row, "false_positive_rate"),
        })
    group_count_rows = []
    for _, row in focus["group_audit"].iterrows():
        group_count_rows.append({
            "Group Feature": feature_label(row.group_column), "Group": value_label(row.group_column, row.group_value),
            "Records": _report_number(row.records), "Positive Outcomes": _report_number(row.total_positives),
            "Selected Records": _report_number(row.selected_records),
            "Found Cases": _report_number(row.found_positives),
            "Missed Cases": _report_number(row.total_positives - row.found_positives),
            "False Alarms": _report_number(row.false_alarms),
        })
    group_interval_rows = []
    for _, row in focus["group_uncertainty"].iterrows():
        group_interval_rows.append({
            "Group Feature": feature_label(row.group_column), "Group": value_label(row.group_column, row.group_value),
            "Metric": metric_labels[row.metric], "Estimate": _report_percent(row.estimate_pct),
            confidence_label: _report_interval(row), "Relevant Outcomes": _report_number(row.denominator_records),
            "Contributing Students": _report_number(row.denominator_units),
            "Interval Status": row.ci_status, "Support Note": row.support_note or "—",
        })
    group_comparison_rows = []
    for _, row in focus["group_comparisons"].iterrows():
        group_comparison_rows.append({
            "Group Feature": feature_label(row.group_column),
            "Comparison": f"{value_label(row.group_column, row.group_value)} minus {value_label(row.group_column, row.reference_group)}",
            "Metric": metric_labels[row.metric],
            "Difference (pp)": "Unavailable" if pd.isna(row.difference_pp) else f"{row.difference_pp:+.1f}",
            confidence_label: _report_interval(row, difference=True),
            "Interval Status": row.ci_status, "Support Note": row.support_note or "—",
        })
    marginal_rows = []
    for _, row in comparison["marginal_changes"].iterrows():
        marginal_rows.append({
            "From Review Share": _report_percent(row.from_review_share_pct),
            "To Review Share": _report_percent(row.to_review_share_pct),
            "Additional Records": _report_number(row.additional_records),
            "Additional Found Cases": _report_number(row.additional_found_positives),
            "Additional False Alarms": _report_number(row.additional_false_alarms),
            "Marginal Precision": _report_percent(row.marginal_precision_pct),
        })
    tables = {
        "scope": pd.DataFrame(scope_rows, columns=["Field", "Value"]),
        "capacity_results": pd.DataFrame(capacity_rows),
        "group_counts": pd.DataFrame(group_count_rows),
        "group_uncertainty": pd.DataFrame(group_interval_rows),
        "group_comparisons": pd.DataFrame(group_comparison_rows),
        "marginal_changes": pd.DataFrame(marginal_rows),
    }
    findings = []

    def add(rule, text, evidence):
        findings.append({"rule": rule, "text": text, "evidence": evidence})

    total_cases = review["found_positives"] + review["missed_positives"]
    add("focus_outcomes",
        f"At {_report_percent(100 * focus_share)} review capacity, the selection contains {_report_quantity(review['selected_records'], unit_noun)}. "
        f"It finds {_report_number(review['found_positives'])} of {_report_quantity(total_cases, 'positive case')}, "
        f"misses {_report_number(review['missed_positives'])}, and produces {_report_quantity(review['false_alarms'], 'false alarm')}.",
        f"reports[{focus_share}].review")
    if validation["excluded_records"]:
        excluded_counts = ", ".join(f"{label}: {_report_number(count)}" for label, count in validation["excluded_outcome_counts"].items())
        add("outcome_exclusions", f"The outcome rules exclude {_report_quantity(validation['excluded_records'], 'input record')} ({excluded_counts}). "
            f"Results apply to the remaining {_report_number(validation['audited_records'])} records.", "input_validation")
    if "unique_entities_to_review" in review and unit != "student":
        add("record_and_student_units", f"The selection of {_report_quantity(review['selected_records'], unit_noun)} contains "
            f"{_report_number(review['unique_entities_to_review'])} distinct supplied student IDs.", f"reports[{focus_share}].review")
    if focus_row.selected_at_cutoff < focus_row.cutoff_tie_records:
        add("cutoff_ties", f"The cutoff score is shared by {_report_number(focus_row.cutoff_tie_records)} records; "
            f"{_report_number(focus_row.selected_at_cutoff)} of those records are selected using original input row order.", "summary.cutoff_tie_records")
    for _, row in comparison["marginal_changes"].iterrows():
        add("capacity_change", f"Increasing capacity from {_report_percent(row.from_review_share_pct)} to {_report_percent(row.to_review_share_pct)} "
            f"adds {_report_quantity(row.additional_records, unit_noun)} to review, "
            f"finds {_report_quantity(row.additional_found_positives, 'additional positive case')}, "
            f"and adds {_report_quantity(row.additional_false_alarms, 'false alarm')}.", "marginal_changes")
    for _, row in focus["group_comparisons"].iterrows():
        label = f"{feature_label(row.group_column)}: {value_label(row.group_column, row.group_value)} minus {value_label(row.group_column, row.reference_group)}"
        interval = _report_interval(row, difference=True)
        direction = "The interval is unavailable; the direction is not assessed."
        if interval != "Unavailable":
            direction = "The interval includes zero; the direction is unresolved." if row.ci_lower_pp <= 0 <= row.ci_upper_pp else (
                "The interval lies above zero under the stated assumptions." if row.ci_lower_pp > 0 else "The interval lies below zero under the stated assumptions."
            )
        difference = "Unavailable" if pd.isna(row.difference_pp) else f"{row.difference_pp:+.1f} pp"
        note = f" Support note: {row.support_note}." if row.support_note else ""
        add("group_difference", f"At {_report_percent(100 * focus_share)}, {label}, {metric_labels[row.metric]} difference: "
            f"{difference}; individual {confidence_label}: {interval}. {direction}{note}", f"reports[{focus_share}].group_comparisons")
    if focus["group_comparisons"].empty and not focus["group_audit"].empty:
        add("no_group_reference", "Group metrics are available; no reference group was supplied for signed group comparisons.",
            f"reports[{focus_share}].uncertainty_configuration.group_references")
    if focus["group_audit"].empty:
        add("no_groups", "No group columns were supplied; this report contains overall results only.",
            f"reports[{focus_share}].configuration.group_columns")
    intervals = focus["group_uncertainty"]
    if not intervals.empty:
        unavailable = int((intervals.ci_status != "Available").sum())
        limited = int(intervals.support_note.ne("").sum())
        if unavailable or limited:
            add("group_interval_support", f"At the focus capacity: unavailable group-metric intervals, {_report_number(unavailable)}; "
                f"group metrics with support notes, {_report_number(limited)}. Inspect their relevant-outcome and contributing-student counts.",
                f"reports[{focus_share}].group_uncertainty")
    for column, count in validation["missing_group_records"].items():
        if count:
            add("missing_group_values", f"{feature_label(column)} is missing for {_report_number(count)} audited records; "
                "those records remain visible in the Unknown group.", "input_validation.missing_group_records")
    limitations = [
        "Counts describe the submitted, outcome-filtered cohort. Positive cases mean the declared positive outcome; course withdrawal and university dropout are different events.",
        "Intervals describe evaluation-sample uncertainty for fixed scores and selections, assuming independent students and allowing dependence within supplied student IDs. They do not cover model refitting, re-ranking, or future-cohort changes.",
        "Intervals are individual exploratory comparisons without simultaneous coverage across groups or review shares. An interval including zero does not establish equality; excluding zero does not establish causation or discrimination.",
        "Capacity changes are observed count differences. The report does not infer significance of policy changes or select an optimal capacity.",
        "Recall divides found positive cases by all positive cases. False-positive rate divides false alarms by negative cases. Precision is the positive-case share of selected records; marginal precision uses only additional selected records.",
        "Group labels follow the supplied display mapping; unmapped values remain source codes. Support flags and bootstrap guards are diagnostic rules, not guarantees of interval coverage.",
    ]
    if config["entity_id_column"] is None:
        limitations.append("No student ID was supplied. Student identity and duplicate students cannot be verified from technical row keys; student intervals rely on the one-row-per-student assumption.")
    if validation["excluded_records"]:
        limitations.append("Outcome exclusions change the evaluation population. Compare capacities within this filtered cohort; results do not describe the excluded outcomes.")
    if not context.get("Prediction Timing") or not context.get("Outcome Horizon"):
        limitations.append("Prediction timing and/or outcome horizon were not supplied. Verify them with the data provider before interpreting this as an operational evaluation.")
    else:
        limitations.append("Prediction timing and outcome horizon are supplied descriptions; this report does not verify their provenance or rule out outcome leakage.")
    confidence_title = f"Group results at {_report_percent(100 * focus_share)}"

    def table_html(key):
        table = tables[key]
        if table.empty:
            return "<p>No results for this section.</p>"
        return '<div class="audit-table">' + table.to_html(index=False, border=0, escape=True) + "</div>"

    parts = [
        "<!doctype html><html><head><meta charset=\"utf-8\">",
        f"<title>Audit Report: {escape(dataset_name)}</title>",
        "<style>.eduai-report{font-family:Arial,sans-serif;line-height:1.45;max-width:1200px;margin:auto;padding:16px}"
        ".eduai-report .audit-table{overflow-x:auto}.eduai-report table{border-collapse:collapse;font-size:0.9em}"
        ".eduai-report th,.eduai-report td{border:1px solid currentColor;padding:6px 8px;text-align:left;vertical-align:top}"
        ".eduai-report details{margin:12px 0}.eduai-report summary{cursor:pointer;font-weight:bold}"
        ".eduai-report li{margin:8px 0}</style></head><body><article class=\"eduai-report\">",
        f"<h2>Audit Report: {escape(dataset_name)}</h2>",
        f"<p>Focus review share: <strong>{_report_percent(100 * focus_share)}</strong>. "
        "This is the supplied report focus, not a recommended capacity.</p>",
        "<h3>Key Findings</h3><ul>" + "".join(f"<li>{escape(finding['text'])}</li>" for finding in findings) + "</ul>",
        "<h3>Data and Scope</h3>" + table_html("scope"),
        "<h3>Review Capacities</h3>" + table_html("capacity_results"),
        "<h3>Additional Workload</h3>" + table_html("marginal_changes"),
        f"<h3>{escape(confidence_title)}</h3>" + table_html("group_comparisons"),
        "<details><summary>Group Counts</summary>" + table_html("group_counts") + "</details>",
        "<details><summary>Group Metrics and Uncertainty</summary>" + table_html("group_uncertainty") + "</details>",
        "<h3>Reading Notes and Limits</h3><ul>" + "".join(f"<li>{escape(note)}</li>" for note in limitations) + "</ul>",
        "</article></body></html>",
    ]
    return {"dataset_name": dataset_name, "focus_share": float(focus_share),
            "tables": tables, "findings": findings, "limitations": limitations,
            "html": "".join(parts)}
