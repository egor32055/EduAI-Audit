"""Reference calculations and independence checks for audit intervals."""

import unittest

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from eduai_uncertainty import _wilson_interval
from eduai_validated_audit import audit_validated_predictions


class UncertaintyTests(unittest.TestCase):
    def frame(self, copies=1, crossing_groups=False):
        records = []
        for student in range(40):
            for repeat in range(copies):
                records.append({
                    "student": student, "row": student * copies + repeat,
                    "outcome": int(student % 2 == 0),
                    "score": 0.9 if student % 4 < 2 else 0.1,
                    "group": ("A" if repeat % 2 == 0 else "B") if crossing_groups else ("A" if student < 20 else "B"),
                })
        return pd.DataFrame(records)

    def audit(self, frame=None, **changes):
        config = dict(target_column="outcome", positive_value=1, negative_values=[0],
                      score_column="score", decision_unit="course_enrollment",
                      decision_id_columns=["row"], entity_id_column="student",
                      group_columns=["group"], review_share=0.5,
                      n_resamples=1000, random_state=7, group_references={"group": "A"})
        config.update(changes)
        return audit_validated_predictions(self.frame() if frame is None else frame, **config)

    def test_wilson_matches_scipy_including_boundaries(self):
        for successes, trials in [(3, 5), (300, 500), (0, 5), (5, 5), (17, 21)]:
            for confidence in [0.90, 0.95, 0.99]:
                with self.subTest(k=successes, n=trials, confidence=confidence):
                    expected = binomtest(successes, trials).proportion_ci(confidence, method="wilson")
                    np.testing.assert_allclose(_wilson_interval(successes, trials, confidence), [expected.low, expected.high], atol=1e-14)
        small = _wilson_interval(3, 5, .95)
        large = _wilson_interval(300, 500, .95)
        self.assertGreater(small[1] - small[0], large[1] - large[0])

    def test_estimates_match_existing_metrics(self):
        report = self.audit()
        for _, row in report["group_uncertainty"].iterrows():
            old = report["group_audit"].query("group_value == @row.group_value").iloc[0]
            self.assertEqual(row["estimate_pct"], old[row["metric"]])
        self.assertEqual(report["review_uncertainty"].iloc[0]["estimate_pct"], report["review"]["recall_pct"])

    def test_replicating_rows_within_students_does_not_narrow_cluster_intervals(self):
        two = self.audit(self.frame(copies=2))
        twenty = self.audit(self.frame(copies=20))
        self.assertEqual(two["uncertainty_configuration"]["method"], "Student Cluster Bootstrap")
        self.assertEqual(twenty["uncertainty_configuration"]["independent_units"], 40)
        for key in ["review_uncertainty", "group_uncertainty"]:
            np.testing.assert_allclose(two[key][["ci_lower_pct", "ci_upper_pct"]],
                                       twenty[key][["ci_lower_pct", "ci_upper_pct"]], atol=1e-12)

    def test_shared_students_across_groups_are_resampled_together(self):
        report = self.audit(self.frame(copies=2, crossing_groups=True))
        comparisons = report["group_comparisons"]
        self.assertTrue((comparisons["difference_pp"] == 0).all())
        self.assertTrue((comparisons["ci_status"] == "Degenerate Bootstrap").all())
        self.assertTrue(comparisons["ci_lower_pp"].isna().all())

    def test_seed_is_reproducible_and_points_do_not_change(self):
        first = self.audit(self.frame(copies=2))
        second = self.audit(self.frame(copies=2))
        pd.testing.assert_frame_equal(first["group_uncertainty"], second["group_uncertainty"])
        changed = self.audit(self.frame(copies=2), random_state=9)
        pd.testing.assert_frame_equal(first["group_audit"], changed["group_audit"])

    def test_no_denominator_and_independent_boundary(self):
        frame = self.frame()
        frame["group"] = np.where(frame.outcome == 1, "A", "B")
        report = self.audit(frame, review_share=1)
        rows = report["group_uncertainty"]
        absent = rows[rows.denominator_records == 0]
        self.assertTrue((absent.ci_status == "No Relevant Outcomes").all())
        self.assertTrue(absent.ci_lower_pct.isna().all())
        available = rows[rows.denominator_records > 0]
        self.assertTrue((available.ci_upper_pct == 100).all())
        self.assertTrue((available.ci_lower_pct < 100).all())

    def test_cluster_boundaries_and_too_few_units_not_certified(self):
        report = self.audit(self.frame(copies=2), review_share=1)
        self.assertTrue((report["review_uncertainty"].ci_status == "Boundary Estimate: Bootstrap Unavailable").all())
        tiny = self.frame(copies=2).iloc[:16]
        report = self.audit(tiny, group_references=None)
        self.assertTrue((report["review_uncertainty"].ci_status == "Too Few Independent Units").all())

    def test_missing_entity_id_does_not_assume_independent_enrollments(self):
        report = self.audit(entity_id_column=None)
        self.assertTrue((report["group_uncertainty"].ci_status == "Missing Entity ID").all())
        self.assertTrue(report["group_uncertainty"].ci_lower_pct.isna().all())

    def test_sparse_cluster_events_withhold_bootstrap_interval(self):
        report = self.audit(self.frame(copies=2), review_share=0.05)
        self.assertTrue((report["review_uncertainty"].ci_status == "Too Few Outcome Event Units").all())
        self.assertTrue(report["review_uncertainty"].ci_lower_pct.isna().all())
        self.assertTrue((report["review_uncertainty"].support_note == "Limited Outcome Support").all())

    def test_source_row_student_assumption_is_explicit(self):
        report = self.audit(entity_id_column=None, decision_unit="student")
        self.assertEqual(report["uncertainty_configuration"]["method"], "Wilson")
        self.assertIsNone(report["uncertainty_configuration"]["entity_id_column"])

    def test_comparison_direction_and_reference_validation(self):
        frame = self.frame()
        frame.loc[frame.group == "B", "score"] = 0.99
        report = self.audit(frame)
        self.assertTrue((report["group_comparisons"].difference_pp == 100).all())
        self.assertTrue((report["group_comparisons"].ci_lower_pp > 0).all())
        for reference in [{"absent": "A"}, {"group": "absent"}, []]:
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                self.audit(group_references=reference)

    def test_interval_configuration_is_validated(self):
        for key, values in {"confidence_level": [0, 1, np.nan, True],
                            "n_resamples": [100, 500.5, True],
                            "random_state": [-1, 1.5, True]}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.audit(**{key: value})


if __name__ == "__main__":
    unittest.main()
