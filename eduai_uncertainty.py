"""Conditional intervals for existing, fixed audit selections.

Wilson intervals: https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
Newcombe differences: statsmodels.stats.proportion.confint_proportions_2indep
Cluster resampling: Cameron and Miller (2015), A Practitioner's Guide to
Cluster-Robust Inference, https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015.pdf
"""

from numbers import Integral, Real
from statistics import NormalDist

import numpy as np
import pandas as pd

from eduai_prediction_audit import _review_count


def _wilson_interval(successes, trials, confidence_level):
    if trials == 0:
        return np.nan, np.nan
    z = NormalDist().inv_cdf((1 + confidence_level) / 2)
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    radius = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def _newcombe_interval(row, reference, confidence_level):
    p = row["numerator"] / row["denominator_records"]
    q = reference["numerator"] / reference["denominator_records"]
    lp, up = _wilson_interval(row["numerator"], row["denominator_records"], confidence_level)
    lq, uq = _wilson_interval(reference["numerator"], reference["denominator_records"], confidence_level)
    return p - q - np.hypot(p - lp, uq - q), p - q + np.hypot(q - lq, up - p)


def _percentile_interval(draws, confidence_level):
    finite = draws[np.isfinite(draws)]
    if len(finite) < 0.95 * len(draws):
        return np.nan, np.nan, "Too Many Undefined Resamples"
    if np.ptp(finite) < 1e-12:
        return np.nan, np.nan, "Degenerate Bootstrap"
    tail = (1 - confidence_level) / 2
    low, high = np.quantile(finite, [tail, 1 - tail])
    return float(low), float(high), "Available"


def calculate_audit_uncertainty(
    prepared, *, target_column, positive_value, score_column, decision_unit,
    entity_id_column=None, group_columns=None, review_share=0.20,
    confidence_level=0.95, n_resamples=2000, random_state=42,
    group_references=None,
):
    """Consume already validated, outcome-filtered rows.

    Scores and selected/not-selected flags stay fixed. Intervals quantify
    evaluation-sample uncertainty under independent students, allowing dependence
    within each student. They do not include refitting, re-ranking, temporal
    drift, confounding, or simultaneous coverage across multiple comparisons.
    """
    if isinstance(confidence_level, (bool, np.bool_)) or not isinstance(confidence_level, Real) or not np.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be a finite number between 0 and 1")
    if isinstance(n_resamples, (bool, np.bool_)) or not isinstance(n_resamples, Integral) or n_resamples < 200:
        raise ValueError("n_resamples must be an integer of at least 200")
    if isinstance(random_state, (bool, np.bool_)) or not isinstance(random_state, Integral) or random_state < 0:
        raise ValueError("random_state must be a non-negative integer")
    groups = [group_columns] if isinstance(group_columns, str) else list(group_columns or [])
    references = {} if group_references is None else group_references
    if not isinstance(references, dict) or any(column not in groups for column in references):
        raise ValueError("group_references must map audited group columns to reference values")
    actual = prepared[target_column].eq(positive_value).to_numpy()
    scores = prepared[score_column].to_numpy(dtype=float)
    selected = np.zeros(len(prepared), dtype=bool)
    selected[np.argsort(-scores, kind="stable")[:_review_count(review_share, len(prepared))]] = True
    codes = pd.factorize(prepared[entity_id_column], sort=False)[0] if entity_id_column else np.arange(len(prepared))
    unit_count = int(codes.max()) + 1
    repeated = unit_count < len(prepared)
    missing_cluster_id = entity_id_column is None and decision_unit != "student"
    method = "Unavailable" if missing_cluster_id else "Student Cluster Bootstrap" if repeated else "Wilson"
    masks = [(None, "All", np.ones(len(prepared), dtype=bool))]
    for column in groups:
        values = prepared[column].astype("object").fillna("Unknown").astype(str).to_numpy()
        if column in references and str(references[column]) not in values:
            raise ValueError(f"Reference group not found in audited rows: {column}")
        masks.extend((column, value, values == value) for value in np.unique(values))
    rows, denominators, numerators = [], [], []
    for column, value, mask in masks:
        for metric, outcomes in [("recall_pct", actual), ("false_positive_rate_pct", ~actual)]:
            denominator = mask & outcomes
            numerator = denominator & selected
            n, k = int(denominator.sum()), int(numerator.sum())
            n_units = len(np.unique(codes[denominator]))
            selected_units = len(np.unique(codes[numerator]))
            unselected_units = len(np.unique(codes[denominator & ~selected]))
            support = "Limited Outcome Support" if n_units < 30 else (
                "Sparse Selected or Unselected Outcomes"
                if min(selected_units, unselected_units) < 10 else ""
            )
            rows.append({
                "group_column": column, "group_value": value, "metric": metric,
                "records": int(mask.sum()), "independent_units": len(np.unique(codes[mask])),
                "numerator": k, "denominator_records": n, "denominator_units": n_units,
                "selected_outcome_units": selected_units, "unselected_outcome_units": unselected_units,
                "estimate_pct": 100 * k / n if n else np.nan,
                "ci_lower_pct": np.nan, "ci_upper_pct": np.nan,
                "ci_width_pp": np.nan, "method": method,
                "ci_status": "No Relevant Outcomes" if n == 0 else "Available",
                "support_note": support,
            })
            denominators.append(denominator)
            numerators.append(numerator)
    bootstrap = None
    if repeated and not missing_cluster_id:
        # Each draw gives one multiplicity to a whole student, across all groups.
        counts = np.zeros((unit_count, 2 * len(rows)), dtype=float)
        for j, (numerator, denominator) in enumerate(zip(numerators, denominators)):
            counts[:, 2 * j] = np.bincount(codes, weights=numerator, minlength=unit_count)
            counts[:, 2 * j + 1] = np.bincount(codes, weights=denominator, minlength=unit_count)
        rng = np.random.default_rng(random_state)
        bootstrap = np.full((n_resamples, len(rows)), np.nan)
        probabilities = np.full(unit_count, 1 / unit_count)
        for start in range(0, n_resamples, 100):
            stop = min(start + 100, n_resamples)
            weights = rng.multinomial(unit_count, probabilities, size=stop - start)
            totals = weights.astype(float) @ counts
            np.divide(totals[:, ::2], totals[:, 1::2],
                      out=bootstrap[start:stop], where=totals[:, 1::2] > 0)
    for j, row in enumerate(rows):
        n, k = row["denominator_records"], row["numerator"]
        if n == 0:
            continue
        if missing_cluster_id:
            row["ci_status"] = "Missing Entity ID"
            continue
        if not repeated:
            low, high = _wilson_interval(k, n, confidence_level)
        elif row["denominator_units"] < 10:
            row["ci_status"] = "Too Few Independent Units"
            continue
        elif k in (0, n):
            row["ci_status"] = "Boundary Estimate: Bootstrap Unavailable"
            continue
        elif min(row["selected_outcome_units"], row["unselected_outcome_units"]) < 5:
            row["ci_status"] = "Too Few Outcome Event Units"
            continue
        else:
            low, high, row["ci_status"] = _percentile_interval(bootstrap[:, j], confidence_level)
        row["ci_lower_pct"], row["ci_upper_pct"] = 100 * low, 100 * high
        row["ci_width_pp"] = 100 * (high - low)
    comparisons = []
    lookup = {(r["group_column"], r["group_value"], r["metric"]): j for j, r in enumerate(rows)}
    for column, reference_value in references.items():
        for j, row in enumerate(rows):
            if row["group_column"] != column or row["group_value"] == str(reference_value):
                continue
            ref_index = lookup[column, str(reference_value), row["metric"]]
            reference = rows[ref_index]
            low = high = np.nan
            status = "Available"
            if row["ci_status"] != "Available" or reference["ci_status"] != "Available":
                status = "Component Interval Unavailable"
            elif repeated:
                low, high, status = _percentile_interval(bootstrap[:, j] - bootstrap[:, ref_index], confidence_level)
            else:
                low, high = _newcombe_interval(row, reference, confidence_level)
            comparisons.append({
                "group_column": column, "group_value": row["group_value"],
                "reference_group": str(reference_value), "metric": row["metric"],
                "difference_pp": row["estimate_pct"] - reference["estimate_pct"],
                "ci_lower_pp": 100 * low, "ci_upper_pp": 100 * high,
                "method": method if repeated or missing_cluster_id else "Newcombe",
                "ci_status": status,
                "contains_zero": bool(low <= 0 <= high) if np.isfinite(low) else None,
                "support_note": "; ".join(dict.fromkeys(note for note in [row["support_note"], reference["support_note"]] if note)),
            })
    table = pd.DataFrame(rows)
    comparison_columns = ["group_column", "group_value", "reference_group", "metric", "difference_pp", "ci_lower_pp", "ci_upper_pp", "method", "ci_status", "contains_zero", "support_note"]
    return {
        "review_uncertainty": table.loc[table["group_column"].isna()].reset_index(drop=True),
        "group_uncertainty": table.loc[table["group_column"].notna()].reset_index(drop=True),
        "group_comparisons": pd.DataFrame(comparisons, columns=comparison_columns),
        "uncertainty_configuration": {
            "confidence_level": confidence_level, "method": method,
            "n_resamples": n_resamples if repeated and not missing_cluster_id else 0,
            "random_state": random_state, "entity_id_column": entity_id_column,
            "independent_units": unit_count if not missing_cluster_id else None,
            "group_references": dict(references),
            "selection_is_fixed": True, "model_is_fixed": True,
            "simultaneous_intervals": False,
            "support_warning_below_units": 30,
            "minimum_bootstrap_denominator_units": 10,
            "minimum_bootstrap_event_units_per_side": 5,
            "sparse_events_warning_below_units_per_side": 10,
            "minimum_valid_resample_share": 0.95,
            "identity_assumption": "Independent students; dependence allowed within supplied entity IDs",
        },
    }
