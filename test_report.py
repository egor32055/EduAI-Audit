"""Factual reporting, conditional conclusions, provenance, and safe rendering."""

from copy import deepcopy
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from eduai_report import build_audit_report
from eduai_review_shares import audit_review_shares


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = pd.DataFrame({
            "id": range(10), "outcome": [1, 0, 1, 0, 0, 1, 0, 0, 2, 2],
            "score": [.9, .8, .7, .6, .5, .4, .3, .2, .99, .98],
            "group": ["A"] * 4 + ["B"] * 6,
        })
        cls.config = dict(target_column="outcome", positive_value=1, negative_values=[0],
                          excluded_values=[2], score_column="score", decision_unit="student",
                          decision_id_columns=["id"], entity_id_column="id", group_columns=["group"],
                          group_references={"group": "A"}, n_resamples=200,
                          review_shares=[.25, .5, .75])
        cls.comparison = audit_review_shares(cls.frame, **cls.config)

    def build(self, comparison=None, **changes):
        return build_audit_report(self.comparison if comparison is None else comparison,
                                  **(dict(dataset_name="Example Institution", focus_share=.5) | changes))

    def test_focus_outcome_counts_match_hand_calculated_example(self):
        report = self.build()
        focus = next(f for f in report["findings"] if f["rule"] == "focus_outcomes")
        self.assertIn("selection contains 4 students", focus["text"])
        self.assertIn("finds 2 of 3 positive cases", focus["text"])
        self.assertIn("misses 1", focus["text"])
        self.assertIn("2 false alarms", focus["text"])
        self.assertEqual(focus["evidence"], "reports[0.5].review")
        scope = report["tables"]["scope"].set_index("Field").Value
        self.assertEqual(scope["Input Records"], "10")
        self.assertEqual(scope["Excluded Records"], "2")
        self.assertEqual(scope["Audited Records"], "8")

    def test_marginal_findings_are_exact_observed_changes(self):
        report = self.build()
        changes = [f for f in report["findings"] if f["rule"] == "capacity_change"]
        self.assertEqual(len(changes), 2)
        self.assertTrue(all("adds 2 students" in f["text"] and "1 additional positive case" in f["text"] for f in changes))
        self.assertEqual(report["tables"]["marginal_changes"]["Marginal Precision"].tolist(), ["50.0%", "50.0%"])

    def test_report_does_not_recompute_audit_or_mutate_input(self):
        before = deepcopy(self.comparison)
        with patch("eduai_review_shares.audit_validated_predictions", side_effect=AssertionError("Unexpected audit calculation")):
            report = self.build()
        pd.testing.assert_frame_equal(before["summary"], self.comparison["summary"])
        for share, original in before["reports"].items():
            self.assertEqual(original["review"], self.comparison["reports"][share]["review"])
            pd.testing.assert_frame_equal(original["group_uncertainty"], self.comparison["reports"][share]["group_uncertainty"])
        self.assertEqual(report["html"], self.build()["html"])

    def test_group_interval_conclusions_do_not_claim_equality(self):
        report = self.build(focus_share=.75)
        differences = [f for f in report["findings"] if f["rule"] == "group_difference"]
        self.assertTrue(differences)
        self.assertTrue(all("includes zero; the direction is unresolved" in f["text"] for f in differences))
        self.assertTrue(any("does not establish equality" in note for note in report["limitations"]))

    def test_positive_negative_and_unavailable_intervals_are_described(self):
        for low, high, phrase in [(10., 40., "above zero"), (-40., -10., "below zero")]:
            changed = deepcopy(self.comparison)
            table = changed["reports"][.5]["group_comparisons"]
            table.loc[:, "ci_lower_pp"] = low
            table.loc[:, "ci_upper_pp"] = high
            report = self.build(changed)
            differences = [f for f in report["findings"] if f["rule"] == "group_difference"]
            self.assertTrue(all(phrase in f["text"] for f in differences))
        changed["reports"][.5]["group_comparisons"].loc[:, "ci_status"] = "Component Interval Unavailable"
        report = self.build(changed)
        self.assertTrue(all("direction is not assessed" in f["text"] for f in report["findings"] if f["rule"] == "group_difference"))

    def test_missing_groups_or_reference_are_explicit(self):
        no_groups = audit_review_shares(self.frame, **(self.config | dict(group_columns=None, group_references=None)))
        report = self.build(no_groups)
        self.assertTrue(any(f["rule"] == "no_groups" for f in report["findings"]))
        no_reference = audit_review_shares(self.frame, **(self.config | dict(group_references=None)))
        report = self.build(no_reference)
        self.assertTrue(any(f["rule"] == "no_group_reference" for f in report["findings"]))

    def test_labels_and_untrusted_text_are_html_escaped(self):
        report = self.build(dataset_name="<script>alert(1)</script>",
                            column_labels={"group": "Study Mode"},
                            group_labels={"group": {"A": "<img src=x onerror=alert(1)>"}})
        self.assertNotIn("<script>", report["html"])
        self.assertNotIn("<img src=x", report["html"])
        self.assertIn("&lt;script&gt;", report["html"])
        self.assertIn("&lt;img", report["html"])
        self.assertIn("Study Mode", report["html"])

    def test_context_is_not_marked_as_verified(self):
        report = self.build()
        scope = report["tables"]["scope"].set_index("Field").Value
        self.assertEqual(scope["Prediction Timing"], "Not supplied")
        self.assertTrue(any("were not supplied" in note for note in report["limitations"]))
        report = self.build(context={"Prediction Timing": "At admission", "Outcome Horizon": "One academic year"})
        self.assertTrue(any("supplied descriptions" in note for note in report["limitations"]))
        self.assertTrue(any("does not verify their provenance" in note for note in report["limitations"]))

    def test_no_real_student_id_is_not_presented_as_verified(self):
        comparison = audit_review_shares(self.frame, **(self.config | dict(entity_id_column=None)))
        self.assertTrue(any("No student ID was supplied" in note for note in self.build(comparison)["limitations"]))

    def test_record_vs_student_units_and_cutoff_ties(self):
        frame = self.frame.loc[self.frame.index.repeat(2)].reset_index(drop=True)
        frame["row"] = np.arange(len(frame))
        comparison = audit_review_shares(frame, **(self.config | dict(decision_unit="course_enrollment", decision_id_columns=["row"])))
        report = self.build(comparison)
        text = " ".join(f["text"] for f in report["findings"])
        self.assertIn("8 course enrollments", text)
        self.assertIn("4 distinct supplied student IDs", text)
        frame["score"] = .5
        comparison = audit_review_shares(frame, **(self.config | dict(decision_unit="course_enrollment", decision_id_columns=["row"])))
        self.assertTrue(any(f["rule"] == "cutoff_ties" for f in self.build(comparison)["findings"]))

    def test_confidence_level_is_not_hardcoded_to_95(self):
        comparison = audit_review_shares(self.frame, **(self.config | dict(confidence_level=.90)))
        report = self.build(comparison)
        self.assertIn("Recall 90% CI", report["tables"]["capacity_results"].columns)
        self.assertNotIn("Recall 95% CI", report["html"])

    def test_invalid_focus_or_report_inputs_rejected(self):
        for changes in [dict(focus_share=.2), dict(focus_share=np.nan), dict(focus_share=True),
                        dict(dataset_name=""), dict(context=[]), dict(group_labels={"group": []}),
                        dict(context={"Prediction Timing": 5})]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.build(**changes)
        with self.assertRaises(ValueError):
            self.build({})
        changed = deepcopy(self.comparison)
        changed["summary"].loc[changed["summary"].review_share_pct == 50, "selected_records"] = 99
        with self.assertRaisesRegex(ValueError, "disagree"):
            self.build(changed)

    def test_single_capacity_has_no_invented_changes_and_no_color_rules(self):
        comparison = audit_review_shares(self.frame, **(self.config | dict(review_shares=[.5])))
        report = self.build(comparison)
        self.assertTrue(report["tables"]["marginal_changes"].empty)
        self.assertFalse(any(f["rule"] == "capacity_change" for f in report["findings"]))
        self.assertNotIn("background:", report["html"])
        self.assertNotIn("color:", report["html"])


if __name__ == "__main__":
    unittest.main()
