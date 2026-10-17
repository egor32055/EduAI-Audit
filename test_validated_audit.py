"""Input safety and hand-calculated checks for the validated audit entry."""

import unittest

import numpy as np
import pandas as pd

from eduai_validated_audit import audit_validated_predictions


class ValidatedAuditTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "student": [1, 2, 3, 4, 5],
            "outcome": ["Dropout", "Graduate", "Dropout", "Graduate", "Enrolled"],
            "score": [0.9, 0.8, 0.3, 0.1, 0.99],
            "group": ["A", "A", "B", None, "B"],
        })
        self.config = dict(
            target_column="outcome", positive_value="Dropout",
            negative_values=["Graduate"], excluded_values=["Enrolled"],
            score_column="score", decision_unit="student",
            decision_id_columns=["student"], entity_id_column="student",
            group_columns=["group"], review_share=0.5,
        )

    def audit(self, frame=None, **changes):
        return audit_validated_predictions(
            self.frame if frame is None else frame, **(self.config | changes)
        )

    def test_explicit_exclusion_and_hand_calculated_metrics(self):
        before = self.frame.copy(deep=True)
        report = self.audit()
        self.assertEqual(report["input_validation"]["excluded_outcome_counts"], {"Enrolled": 1})
        self.assertEqual(report["input_validation"]["missing_group_records"], {"group": 1})
        review = report["review"]
        # Among four resolved outcomes, top two are one dropout and one graduate.
        for key, expected in dict(records=4, selected_records=2, found_positives=1,
                                  false_alarms=1, missed_positives=1,
                                  recall_pct=50, precision_pct=50,
                                  unique_entities_to_review=2).items():
            self.assertEqual(review[key], expected, key)
        self.assertAlmostEqual(report["scores"]["roc_auc"], 0.75)
        self.assertEqual(report["configuration"]["selection_unit"], "student")
        pd.testing.assert_frame_equal(before, self.frame)

    def test_unknown_and_missing_outcomes_rejected(self):
        with self.assertRaisesRegex(ValueError, "unmapped outcomes"):
            self.audit(excluded_values=[])
        frame = self.frame.copy()
        frame.loc[4, "outcome"] = None
        with self.assertRaisesRegex(ValueError, "missing outcomes"):
            self.audit(frame)

    def test_duplicate_decisions_rejected_even_if_excluded(self):
        frame = pd.concat([self.frame, self.frame.iloc[[4]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate decision keys"):
            self.audit(frame)

    def test_repeated_student_cannot_hide_behind_row_key(self):
        frame = self.frame.copy()
        frame["row"] = np.arange(len(frame))
        frame.loc[1, "student"] = 1
        with self.assertRaisesRegex(ValueError, "repeated entity IDs"):
            self.audit(frame, decision_id_columns=["row"])

    def test_course_enrollment_allows_repeated_student_with_unique_key(self):
        frame = self.frame.copy()
        frame["course"] = ["A", "B", "A", "A", "A"]
        frame.loc[1, "student"] = 1
        report = self.audit(frame, decision_unit="course_enrollment",
                            decision_id_columns=["student", "course"])
        self.assertEqual(report["review"]["selected_records"], 2)
        self.assertEqual(report["review"]["unique_entities_to_review"], 1)

    def test_mapping_and_configuration_rejected(self):
        cases = [
            {"negative_values": ["Graduate", "Dropout"]},
            {"excluded_values": ["Graduate", "Enrolled"]},
            {"negative_values": "Graduate"},
            {"negative_values": []},
            {"negative_values": [None]},
            {"excluded_values": ["Enrolled", "Enrolled"]},
            {"decision_unit": ""},
            {"decision_unit": "Student"},
            {"decision_id_columns": []},
            {"decision_id_columns": ["student", "student"]},
            {"decision_id_columns": ["outcome"]},
            {"group_columns": ["outcome"]},
            {"score_column": "outcome"},
            {"score_column": "absent"},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.audit(**changes)

    def test_invalid_scores_rejected_including_excluded_rows(self):
        for bad in [np.nan, np.inf, -0.1, 1.1, "bad", True]:
            frame = self.frame.copy()
            frame["score"] = frame["score"].astype(object)
            frame.loc[4, "score"] = bad
            with self.subTest(score=bad), self.assertRaisesRegex(ValueError, "[Ss]core|probabilities"):
                self.audit(frame)

    def test_missing_ids_and_duplicate_column_names_rejected(self):
        for missing in [None, " "]:
            frame = self.frame.copy()
            frame["student"] = frame["student"].astype(object)
            frame.loc[4, "student"] = missing
            with self.subTest(id=missing), self.assertRaisesRegex(ValueError, "missing or blank"):
                self.audit(frame)
        frame = self.frame.copy()
        frame.columns = ["student", "outcome", "score", "score"]
        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            self.audit(frame)

    def test_invalid_review_shares(self):
        for value in [0, -1, 1.1, np.nan, np.inf, True, "0.2"]:
            with self.subTest(share=value), self.assertRaisesRegex(ValueError, "review_share"):
                self.audit(review_share=value)

    def test_all_excluded_or_single_class_rejected(self):
        for outcomes in [["Enrolled"] * 5, ["Dropout"] * 5, ["Graduate"] * 5]:
            frame = self.frame.copy()
            frame["outcome"] = outcomes
            with self.subTest(outcomes=outcomes), self.assertRaisesRegex(ValueError, "both outcome classes"):
                self.audit(frame)

    def test_no_groups_and_source_row_key_supported(self):
        report = self.audit(entity_id_column=None, group_columns=None)
        self.assertTrue(report["group_audit"].empty)
        self.assertEqual(report["review"]["records"], 4)


if __name__ == "__main__":
    unittest.main()
