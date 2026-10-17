"""Hand-calculated capacity changes, rounding, ties, and existing-audit parity."""

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from eduai_prediction_audit import _review_count
from eduai_review_shares import audit_review_shares
from eduai_validated_audit import audit_validated_predictions


class ReviewShareTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "id": range(10), "outcome": [1, 0, 1, 0, 0, 1, 0, 0, 2, 2],
            "score": [.9, .8, .7, .6, .5, .4, .3, .2, .99, .98],
            "group": ["A"] * 4 + ["B"] * 6,
        })
        self.config = dict(target_column="outcome", positive_value=1, negative_values=[0],
                           excluded_values=[2], score_column="score", decision_unit="student",
                           decision_id_columns=["id"], entity_id_column="id",
                           group_columns=["group"], group_references={"group": "A"}, n_resamples=200)

    def run_grid(self, frame=None, **changes):
        return audit_review_shares(self.frame if frame is None else frame,
                                   **(self.config | changes))

    def test_known_counts_after_exclusion_and_marginal_changes(self):
        before = self.frame.copy(deep=True)
        result = self.run_grid(review_shares=[.75, .25, .50])
        summary = result["summary"]
        self.assertEqual(result["configuration"]["review_shares"], [.25, .5, .75])
        self.assertEqual(result["input_validation"]["excluded_records"], 2)
        self.assertEqual(summary.records.tolist(), [8, 8, 8])
        self.assertEqual(summary.selected_records.tolist(), [2, 4, 6])
        self.assertEqual(summary.found_positives.tolist(), [1, 2, 3])
        self.assertEqual(summary.false_alarms.tolist(), [1, 2, 3])
        self.assertEqual(summary.missed_positives.tolist(), [2, 1, 0])
        marginal = result["marginal_changes"]
        self.assertEqual(marginal.additional_records.tolist(), [2, 2])
        self.assertEqual(marginal.additional_found_positives.tolist(), [1, 1])
        self.assertEqual(marginal.additional_false_alarms.tolist(), [1, 1])
        self.assertEqual(marginal.marginal_precision_pct.tolist(), [50, 50])
        pd.testing.assert_frame_equal(self.frame, before)

    def test_each_report_matches_standalone_audit_including_intervals(self):
        result = self.run_grid(review_shares=[.25, .50, .75])
        for share, report in result["reports"].items():
            standalone = audit_validated_predictions(self.frame, review_share=share, **self.config)
            self.assertEqual(report["review"], standalone["review"])
            for key in ["group_audit", "group_uncertainty", "group_comparisons", "review_uncertainty"]:
                pd.testing.assert_frame_equal(report[key], standalone[key])
            groups = result["group_audit"].query("review_share_pct == @share * 100")
            self.assertIn("recall_ci_lower_pct", groups.columns)
            self.assertIn("false_positive_rate_ci_upper_pct", groups.columns)

    def test_decimal_rounding_without_float_artifacts(self):
        for share, expected in [(.07, 7), (.14, 14), (.28, 28), (.001, 1), (1, 100)]:
            self.assertEqual(_review_count(share, 100), expected)
        frame = pd.DataFrame({"id": range(100), "outcome": np.arange(100) % 2,
                              "score": np.linspace(1, 0, 100), "group": ["A"] * 100})
        result = self.run_grid(frame, review_shares=[.07, .14, .28])
        self.assertEqual(result["summary"].selected_records.tolist(), [7, 14, 28])
        for report in result["reports"].values():
            self.assertEqual(report["review_uncertainty"].numerator.sum(), report["review"]["selected_records"])

    def test_rounded_capacities_can_be_equal(self):
        result = self.run_grid(review_shares=[.01, .02])
        self.assertEqual(result["summary"].selected_records.tolist(), [1, 1])
        marginal = result["marginal_changes"].iloc[0]
        self.assertEqual(marginal.additional_records, 0)
        self.assertTrue(np.isnan(marginal.marginal_precision_pct))
        self.assertEqual(result["summary"].actual_review_share_pct.tolist(), [12.5, 12.5])

    def test_ties_follow_original_row_order(self):
        frame = self.frame.copy()
        frame["score"] = .5
        result = self.run_grid(frame, review_shares=[.25, .5, .75])
        self.assertEqual(result["summary"].found_positives.tolist(), [1, 2, 3])
        self.assertEqual(result["summary"].cutoff_tie_records.tolist(), [8, 8, 8])
        self.assertEqual(result["summary"].selected_at_cutoff.tolist(), [2, 4, 6])

    def test_one_share_and_no_groups(self):
        result = self.run_grid(review_shares=[1], group_columns=None, group_references=None,
                               entity_id_column=None)
        self.assertTrue(result["group_audit"].empty)
        self.assertTrue(result["group_comparisons"].empty)
        self.assertTrue(result["marginal_changes"].empty)
        self.assertEqual(result["summary"].iloc[0].recall_pct, 100)
        self.assertEqual(result["summary"].iloc[0].false_positive_rate_pct, 100)

    def test_repeated_entities_keep_record_capacity_and_unique_student_count(self):
        frame = self.frame.loc[self.frame.index.repeat(2)].reset_index(drop=True)
        frame["row"] = np.arange(len(frame))
        result = self.run_grid(frame, review_shares=[.25, .5], decision_unit="course_enrollment",
                               decision_id_columns=["row"])
        self.assertEqual(result["summary"].selected_records.tolist(), [4, 8])
        self.assertEqual(result["summary"].unique_entities_to_review.tolist(), [2, 4])
        self.assertEqual(result["reports"][.25]["uncertainty_configuration"]["method"], "Student Cluster Bootstrap")

    def test_invalid_share_grids_rejected(self):
        for shares in [[], (), .2, "20%", [0], [-.1], [1.1], [np.nan], [np.inf], [True],
                       [".2"], [.2, .2], [.2, .1 + .1]]:
            with self.subTest(shares=shares), self.assertRaises(ValueError):
                self.run_grid(review_shares=shares)

    def test_existing_input_validation_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "unmapped outcomes"):
            self.run_grid(excluded_values=[])
        duplicate = pd.concat([self.frame, self.frame.iloc[[0]]])
        with self.assertRaisesRegex(ValueError, "Duplicate decision keys"):
            self.run_grid(duplicate)

    def test_no_model_training_and_nested_counts(self):
        with patch("sklearn.linear_model.LogisticRegression.fit", side_effect=AssertionError("Unexpected model training")):
            result = self.run_grid(review_shares=[.15, .20, .30, 1])
        summary = result["summary"]
        for column in ["selected_records", "found_positives", "false_alarms", "recall_pct", "false_positive_rate_pct"]:
            self.assertTrue((summary[column].diff().dropna() >= 0).all(), column)
        self.assertTrue((summary.missed_positives.diff().dropna() <= 0).all())


if __name__ == "__main__":
    unittest.main()
