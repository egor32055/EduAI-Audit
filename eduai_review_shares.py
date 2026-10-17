"""Compare review capacities using one scored cohort and explicit input rules."""

from numbers import Real

import numpy as np
import pandas as pd

from eduai_prediction_audit import _review_count
from eduai_validated_audit import audit_validated_predictions, validate_audit_input


def audit_review_shares(
    dataset, *, target_column, positive_value, negative_values,
    score_column, decision_unit, decision_id_columns,
    review_shares=(0.15, 0.20, 0.30), group_columns=None,
    entity_id_column=None, excluded_values=(), confidence_level=0.95,
    n_resamples=2000, random_state=42, group_references=None,
):
    """Run the same validated prediction audit for several review shares.

    Shares are sorted and must be unique. One stable score ranking is used;
    equal scores are resolved by original input row order. Capacity is rounded
    up on the outcome-filtered cohort. Marginal changes are exact observed
    counts, not inference about differences between policies. Each confidence
    interval remains conditional on its own selection, with no simultaneous
    coverage across shares and no automatic choice of an optimal policy.
    """
    if not isinstance(review_shares, (list, tuple)) or not review_shares:
        raise ValueError("review_shares must be a non-empty list or tuple")
    shares = []
    for share in review_shares:
        if isinstance(share, (bool, np.bool_)) or not isinstance(share, Real) or not np.isfinite(share) or not 0 < share <= 1:
            raise ValueError("Each review share must be a finite number greater than 0 and at most 1")
        shares.append(float(share))
    if len(shares) != len(set(shares)):
        raise ValueError("review_shares contains duplicate values")
    shares.sort()
    common = dict(
        target_column=target_column, positive_value=positive_value,
        negative_values=negative_values, score_column=score_column,
        decision_unit=decision_unit, decision_id_columns=decision_id_columns,
        group_columns=group_columns, entity_id_column=entity_id_column,
        excluded_values=excluded_values,
    )
    prepared, validation = validate_audit_input(dataset, review_share=shares[0], **common)
    ranked_scores = np.sort(prepared[score_column].to_numpy(dtype=float))[::-1]
    reports, summary_rows, group_tables, comparison_tables = {}, [], [], []
    previous_review = None
    marginal_rows = []
    for share in shares:
        report = audit_validated_predictions(
            dataset, review_share=share, confidence_level=confidence_level,
            n_resamples=n_resamples, random_state=random_state,
            group_references=group_references, **common,
        )
        reports[share] = report
        review = report["review"]
        total_positives = review["found_positives"] + review["missed_positives"]
        total_negatives = review["records"] - total_positives
        selected_count = _review_count(share, len(prepared))
        cutoff = ranked_scores[selected_count - 1]
        above_cutoff = int((ranked_scores > cutoff).sum())
        overall = report["review_uncertainty"].set_index("metric")
        summary = {
            **review,
            "actual_review_share_pct": 100 * selected_count / len(prepared),
            "total_positives": total_positives, "total_negatives": total_negatives,
            "false_positive_rate_pct": 100 * review["false_alarms"] / total_negatives,
            "cutoff_score": cutoff,
            "cutoff_tie_records": int((ranked_scores == cutoff).sum()),
            "selected_at_cutoff": selected_count - above_cutoff,
        }
        for metric, prefix in [("recall_pct", "recall"), ("false_positive_rate_pct", "false_positive_rate")]:
            interval = overall.loc[metric]
            for source, suffix in [("ci_lower_pct", "ci_lower_pct"), ("ci_upper_pct", "ci_upper_pct"),
                                   ("ci_status", "ci_status"), ("support_note", "support_note")]:
                summary[f"{prefix}_{suffix}"] = interval[source]
        summary_rows.append(summary)
        groups = report["group_audit"].copy()
        if not groups.empty:
            for metric, prefix in [("recall_pct", "recall"), ("false_positive_rate_pct", "false_positive_rate")]:
                intervals = report["group_uncertainty"]
                fields = ["group_column", "group_value", "ci_lower_pct", "ci_upper_pct", "ci_status", "support_note", "denominator_units"]
                part = intervals.loc[intervals.metric == metric, fields].copy()
                part = part.rename(columns={c: f"{prefix}_{c}" for c in fields[2:]})
                groups = groups.merge(part, on=["group_column", "group_value"], validate="one_to_one")
        groups.insert(0, "review_share_pct", 100 * share)
        group_tables.append(groups)
        comparisons = report["group_comparisons"].copy()
        comparisons.insert(0, "review_share_pct", 100 * share)
        comparison_tables.append(comparisons)
        if previous_review is not None:
            previous_share, previous = previous_review
            added = review["selected_records"] - previous["selected_records"]
            found = review["found_positives"] - previous["found_positives"]
            false_alarms = review["false_alarms"] - previous["false_alarms"]
            marginal_rows.append({
                "from_review_share_pct": 100 * previous_share,
                "to_review_share_pct": 100 * share,
                "additional_records": added, "additional_found_positives": found,
                "additional_false_alarms": false_alarms,
                "marginal_precision_pct": 100 * found / added if added else np.nan,
            })
        previous_review = share, review
    marginal_columns = ["from_review_share_pct", "to_review_share_pct", "additional_records", "additional_found_positives", "additional_false_alarms", "marginal_precision_pct"]
    return {
        "configuration": {
            "review_shares": shares, "selection_unit": decision_unit,
            "selection_population": validation["selection_population"],
            "rounding_rule": "Ceiling of declared decimal share times audited records",
            "tie_rule": "Stable original input row order",
            "same_scores_and_population": True, "model_refitted": False,
            "confidence_level": confidence_level, "simultaneous_intervals": False,
            "marginal_changes_are_observed_counts": True,
        },
        "input_validation": validation,
        "summary": pd.DataFrame(summary_rows),
        "group_audit": pd.concat(group_tables, ignore_index=True),
        "group_comparisons": pd.concat(comparison_tables, ignore_index=True),
        "marginal_changes": pd.DataFrame(marginal_rows, columns=marginal_columns),
        "reports": reports,
    }
