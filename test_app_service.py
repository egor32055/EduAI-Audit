"""Checks for the CSV-to-report boundary used by the local app."""

import unittest

from eduai_app_service import (
    SOURCE_ROW_COLUMN, build_uploaded_audit, load_prediction_csv, parse_review_shares,
)


class AppServiceTests(unittest.TestCase):
    def test_csv_to_report_preserves_exclusions_and_capacity_counts(self):
        contents = (
            "student,outcome,score,group\n"
            "1,Dropout,0.9,A\n"
            "2,Graduate,0.8,A\n"
            "3,Dropout,0.7,B\n"
            "4,Graduate,0.6,B\n"
            "5,Enrolled,0.99,A\n"
            "6,Graduate,0.5,A\n"
            "7,Dropout,0.4,B\n"
            "8,Graduate,0.3,B\n"
            "9,Graduate,0.2,A\n"
        ).encode("utf-8")
        frame = load_prediction_csv(contents)
        comparison, report = build_uploaded_audit(
            frame,
            dataset_name="Example cohort",
            target_column="outcome",
            positive_value="Dropout",
            negative_values=["Graduate"],
            excluded_values=["Enrolled"],
            score_column="score",
            decision_unit="student",
            decision_id_columns=["student"],
            entity_id_column="student",
            group_columns=["group"],
            group_references={"group": "A"},
            review_shares=parse_review_shares("25, 50"),
            focus_share=0.5,
        )
        self.assertEqual(comparison["input_validation"]["input_records"], 9)
        self.assertEqual(comparison["input_validation"]["excluded_records"], 1)
        self.assertEqual(comparison["reports"][0.5]["review"]["selected_records"], 4)
        self.assertEqual(comparison["reports"][0.5]["review"]["found_positives"], 2)
        self.assertIn("Example cohort", report["html"])
        self.assertEqual(frame.columns.tolist(), ["student", "outcome", "score", "group"])

    def test_source_row_key_is_explicit_and_reported(self):
        frame = load_prediction_csv(b"outcome,score\n1,0.9\n0,0.1\n")
        comparison, report = build_uploaded_audit(
            frame, dataset_name="No ID", target_column="outcome", positive_value="1",
            negative_values=["0"], excluded_values=[], score_column="score",
            decision_unit="student", decision_id_columns=[], entity_id_column=None,
            group_columns=[], group_references={}, review_shares=[0.5],
            focus_share=0.5, use_source_row_number=True,
        )
        self.assertEqual(comparison["input_validation"]["decision_id_columns"], [SOURCE_ROW_COLUMN])
        self.assertIn("Technical source row number only", report["html"])
        self.assertNotIn(SOURCE_ROW_COLUMN, frame.columns)

    def test_duplicate_csv_headers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            load_prediction_csv(b"id,id,outcome,score\n1,2,1,0.9\n")

    def test_csv_keeps_leading_zero_ids_and_outcome_codes(self):
        frame = load_prediction_csv(b"id,outcome,score\n001,01,0.8\n1,NA,0.2\n")
        self.assertEqual(frame["id"].tolist(), ["001", "1"])
        self.assertEqual(frame["outcome"].tolist(), ["01", "NA"])

    def test_review_share_input_rejects_duplicates_and_out_of_range(self):
        for text in ("20, 20", "0", "101", "not a number"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_review_shares(text)


if __name__ == "__main__":
    unittest.main()
