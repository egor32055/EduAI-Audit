"""Paired-record descriptive comparisons, without inventing inference for model differences."""

from copy import deepcopy
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from eduai_app_service import build_uploaded_audit, load_prediction_csv
from eduai_comparison_view import comparison_group_chart, comparison_html, comparison_zip
from eduai_model_comparison import compare_uploaded_predictions, preview_model_comparison
from eduai_presets import preset_defaults
from eduai_settings import read_settings, widget_settings, write_settings
from test_presentation import ROOT


TWO_SAMPLE = (ROOT / "examples" / "sample_two_predictions.csv").read_bytes()


def fixture():
    frame = pd.DataFrame({"id": [f"{n:03}" for n in range(1, 11)],
        "outcome": ["A", "B", "A", "B", "A", "B", "B", "B", "X", "X"],
        "score_a": [.9, .8, .7, .6, .5, .4, .3, .2, 1, 1],
        "score_b": [.9, .5, .95, .6, .7, .4, .3, .2, 1, 1],
        "group": ["TC"] * 4 + ["TP"] * 4 + [None, "TP"]})
    config = dict(dataset_name="Pair", target_column="outcome", score_column="score_a", positive_value="A", negative_values=["B"],
                  excluded_values=["X"], decision_unit="student", decision_id_columns=["id"], entity_id_column="id",
                  group_columns=["group"], group_references={"group": "TC"}, review_shares=[.25, .5, 1], focus_share=.25,
                  use_source_row_number=False, prediction_timing="", outcome_horizon="")
    return frame, config


class ModelComparisonTests(unittest.TestCase):
    def test_exact_same_capacity_overlap_and_outcome_differences(self):
        frame, config = fixture()
        before = frame.copy(deep=True)
        result = compare_uploaded_predictions(frame, config, "score_b")
        row = result["overlap"].iloc[0]
        self.assertEqual([row[name] for name in ("audited_records", "selected_per_model", "both", "only_A", "only_B", "neither")], [8, 2, 1, 1, 1, 5])
        self.assertEqual([row[name] for name in ("positives_both", "positives_only_A", "positives_only_B", "positives_neither")], [1, 0, 1, 1])
        self.assertEqual(result["differences"].iloc[0].found_positives_B_minus_A, 1)
        self.assertEqual(result["differences"].iloc[0].false_alarms_B_minus_A, -1)
        records = result["selection_records"]
        self.assertEqual(records.loc[records.selection_category.eq("only_A"), "key:id"].tolist(), ["002"])
        self.assertEqual(records.loc[records.selection_category.eq("only_B"), "key:id"].tolist(), ["003"])
        self.assertEqual(records.source_record.tolist(), list(range(1, 9)))
        self.assertFalse(any("ci_" in column for column in result["differences"].columns))
        self.assertEqual(result["overlap"].iloc[-1][["both", "only_A", "only_B", "neither"]].tolist(), [8, 0, 0, 0])
        pd.testing.assert_frame_equal(frame, before)
        for model, score in [("A", "score_a"), ("B", "score_b")]:
            comparison, _ = build_uploaded_audit(frame, **{**config, "score_column": score})
            pd.testing.assert_frame_equal(result["comparisons"][model]["summary"], comparison["summary"])

    def test_identical_and_tied_predictions_keep_original_order_and_exclusions(self):
        frame, config = fixture()
        frame["score_a"] = .5
        frame["score_b"] = .5
        frame.index = [5] * len(frame)
        config.update(review_shares=[.3], focus_share=.3)
        result = compare_uploaded_predictions(frame, config, "score_b")
        self.assertEqual(result["selection_records"].loc[lambda f: f.selected_A, "key:id"].tolist(), ["001", "002", "003"])
        self.assertEqual(result["overlap"].iloc[0][["selected_per_model", "both", "only_A", "only_B"]].tolist(), [3, 3, 0, 0])
        self.assertTrue(result["differences"].filter(like="_B_minus_A").eq(0).all().all())

    def test_secondary_invalid_scores_even_in_excluded_rows_stop_both_audits(self):
        frame, config = fixture()
        for value in [np.nan, np.inf, -1, 1.1, "bad", True]:
            bad = frame.copy().astype({"score_b": object})
            bad.loc[9, "score_b"] = value
            with self.subTest(value=value), patch("eduai_model_comparison.build_uploaded_audit", side_effect=AssertionError("Ran before both inputs were valid")):
                with self.assertRaises(ValueError):
                    compare_uploaded_predictions(bad, config, "score_b")
        for column in [None, "score_a", "id", "group", "outcome", "missing"]:
            with self.subTest(column=column), self.assertRaises(ValueError):
                preview_model_comparison(frame, config, column)

    def test_record_overlap_does_not_collapse_repeated_students(self):
        frame, config = fixture()
        frame["student"] = ["S1", "S1", "S2", "S2", "S3", "S3", "S4", "S4", "S5", "S5"]
        config.update(decision_unit="course_enrollment", entity_id_column="student", group_columns=[], group_references={})
        result = compare_uploaded_predictions(frame, config, "score_b")
        self.assertEqual(len(result["selection_records"]), 8)
        self.assertEqual(result["overlap"].iloc[0].only_A, 1)
        self.assertEqual(result["comparisons"]["A"]["reports"][.25]["uncertainty_configuration"]["method"], "Student Cluster Bootstrap")
        self.assertEqual(result["selection_records"].loc[lambda f: f.selected_A, "key:student"].nunique(), 1)

    def test_groups_missing_outcomes_and_exports_preserve_individual_intervals(self):
        frame, config = fixture()
        frame.loc[4, "outcome"] = "B"
        result = compare_uploaded_predictions(frame, config, "score_b")
        for metric in ("recall_pct", "false_positive_rate_pct"):
            comparison_group_chart(result, "group", metric, "ru").to_dict(validate=True)
        group = result["group_differences"].loc[lambda f: f.review_share_pct.eq(25)]
        self.assertEqual(group.found_positives_B.sum() - group.found_positives_A.sum(), 1)
        self.assertTrue(pd.isna(group.loc[group.group_value.eq("TP"), "recall_pct_B_minus_A"].iloc[0]))
        result["config"]["dataset_name"] = '<script>alert(1)</script>'
        for language in ("en", "ru"):
            html = comparison_html(result, language)
            self.assertIn('&lt;script&gt;', html)
            self.assertNotIn('<script>', html)
            self.assertIn('lang="' + language + '"', html)
        with ZipFile(BytesIO(comparison_zip(result))) as archive:
            self.assertIn("model_A/group_uncertainty.csv", archive.namelist())
            self.assertIn("model_B/group_uncertainty.csv", archive.namelist())
            self.assertNotIn("selection_records.csv", archive.namelist())
            manifest = json.loads(archive.read("manifest.json"))
            self.assertFalse(manifest["selection_records_included"])
            parsed = pd.read_csv(archive.open("overlap.csv"))
            self.assertEqual(parsed.iloc[0].both, 1)

    def test_settings_v1_and_v2_retain_comparison_mode(self):
        _, config = fixture()
        data = write_settings(config, preset_id="custom", delimiter=",", encoding="utf-8-sig", comparison_score_column="score_b")
        settings = read_settings(data)
        self.assertEqual(settings["comparison_score_column"], "score_b")
        values = widget_settings(settings, "f" * 64)
        self.assertTrue(values["ffffffffffffffff:custom:compare_models"])
        self.assertEqual(values["ffffffffffffffff:custom:score_b"], "score_b")
        legacy = deepcopy(settings)
        legacy["version"] = 1
        del legacy["comparison_score_column"]
        migrated = read_settings(json.dumps(legacy).encode())
        self.assertIsNone(migrated["comparison_score_column"])
        self.assertFalse(widget_settings(migrated, "f" * 64)["ffffffffffffffff:custom:compare_models"])


class ComparisonFlowTests(unittest.TestCase):
    def test_comparison_settings_import_validates_both_columns_before_applying(self):
        uploaded = BytesIO(TWO_SAMPLE)
        uploaded.name = "two.csv"
        config = preset_defaults("example", load_prediction_csv(TWO_SAMPLE))
        config.update(dataset_name="Two scores", review_shares=[.15, .2, .3], focus_share=.2,
                      prediction_timing="", outcome_horizon="")
        profile = BytesIO(write_settings(config, preset_id="example", delimiter=",", encoding="utf-8-sig", comparison_score_column="dropout_probability_b"))
        profile.name = "comparison.json"
        def upload(label, **kwargs):
            return uploaded if kwargs["key"] == "upload_file" else profile
        with patch("streamlit.file_uploader", side_effect=upload):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
            with patch("eduai_app_service.audit_review_shares", side_effect=AssertionError("Import reran audit")):
                app.button(key="apply_settings").click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(next(w for w in app.checkbox if w.label == "Compare two prediction columns").value)
            self.assertEqual(next(w for w in app.selectbox if w.label == "Model B probability column").value, "dropout_probability_b")
            profile = BytesIO(write_settings(config, preset_id="example", delimiter=",", encoding="utf-8-sig", comparison_score_column="missing_b"))
            profile.name = "missing.json"
            app.button(key="apply_settings").click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("Missing columns" in e.value for e in app.error))
            self.assertEqual(next(w for w in app.selectbox if w.label == "Model B probability column").value, "dropout_probability_b")

    def test_bilingual_comparison_and_individual_model_details_do_not_rerun_audits(self):
        uploaded = BytesIO(TWO_SAMPLE)
        uploaded.name = "two.csv"
        with patch("streamlit.file_uploader", return_value=uploaded):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
            app.selectbox(key="preset_id").set_value("example").run(timeout=30)
            next(w for w in app.checkbox if w.label == "Compare two prediction columns").check().run(timeout=30)
            self.assertTrue(app.button(key="run_audit").disabled)
            next(w for w in app.selectbox if w.label == "Model B probability column").set_value("dropout_probability_b").run(timeout=30)
            app.button(key="run_audit").click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual([m.value for m in app.metric], ["2", "2", "2", "10"])
            with patch("eduai_app_service.audit_review_shares", side_effect=AssertionError("Display change reran audit")):
                app.selectbox(key="language").set_value("ru").run(timeout=30)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual([m.value for m in app.metric], ["2", "2", "2", "10"])
                next(w for w in app.selectbox if w.label == "Подробный аудит модели (необязательно)").set_value("B").run(timeout=30)
                self.assertEqual([m.value for m in app.metric][-5:], ["16", "4", "4", "3", "0"])
            next(w for w in app.selectbox if w.label == "Модель B: столбец вероятности").set_value("study_mode").run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.button(key="run_audit").disabled)
            self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
