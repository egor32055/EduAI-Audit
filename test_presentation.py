"""Preset boundaries, translation integrity, and data displayed by plots."""

from copy import deepcopy
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from eduai_app_service import build_uploaded_audit, load_prediction_csv
from eduai_charts import capacity_chart, capacity_chart_data, charts_html
from eduai_i18n import error_text
from eduai_presets import preset_defaults
from eduai_report_locale import present_report


ROOT = Path(__file__).parent
SAMPLE = (ROOT / "examples" / "sample_predictions.csv").read_bytes()


def sample_audit(**changes):
    frame = load_prediction_csv(SAMPLE)
    config = preset_defaults("example", frame)
    config.update(dataset_name="Example", review_shares=[0.15, 0.20, 0.30], focus_share=0.20)
    config.update(changes)
    return build_uploaded_audit(frame, **config)


class PresentationTests(unittest.TestCase):
    def test_upv_preset_uses_student_key_and_only_declared_reference(self):
        frame = pd.DataFrame({"dni_hash": ["001", "002"], "abandono_hash": ["A", "B"],
                              "Predicted Dropout Risk": [".8", ".2"], "dedicacion": ["TC", "TP"],
                              "estudios_m_hash": ["E", "F"], "desplazado_hash": ["A", "B"]})
        config = preset_defaults("upv_2022", frame)
        self.assertEqual(config["decision_unit"], "student")
        self.assertEqual(config["decision_id_columns"], ["dni_hash"])
        self.assertEqual(config["entity_id_column"], "dni_hash")
        self.assertEqual(config["group_references"], {"dedicacion": "TC"})
        self.assertEqual(config["score_column"], "Predicted Dropout Risk")
        self.assertIsNone(preset_defaults("upv_2022", frame.drop(columns="Predicted Dropout Risk"))["score_column"])

    def test_oulad_requires_complete_composite_key_and_uci_keeps_identity_limit(self):
        frame = pd.DataFrame(columns=["final_result", "id_student", "code_module", "code_presentation", "imd_band", "score"])
        config = preset_defaults("oulad", frame)
        self.assertEqual(config["decision_unit"], "course_enrollment")
        self.assertEqual(len(config["decision_id_columns"]), 3)
        self.assertEqual(preset_defaults("oulad", frame.drop(columns="code_presentation"))["decision_id_columns"], [])
        uci = pd.DataFrame({"Target": ["Dropout", "Graduate", "Enrolled"], "Source Row ID": ["1", "2", "3"],
                            "Predicted Dropout Risk": [".8", ".2", ".6"]})
        config = preset_defaults("uci", uci)
        self.assertEqual(config["excluded_values"], ["Enrolled"])
        self.assertIsNone(config["entity_id_column"])
        self.assertFalse(config["use_source_row_number"])

    def test_russian_report_keeps_counts_codes_evidence_and_original_results(self):
        comparison, report = sample_audit(group_references={"study_mode": "Full-time"})
        original = deepcopy(comparison)
        original_report = deepcopy(report)
        russian = present_report(report, comparison, "ru")
        self.assertEqual([f["evidence"] for f in russian["findings"]], [f["evidence"] for f in report["findings"]])
        self.assertEqual(russian["tables"]["capacity_results"]["Выбрано строк"].tolist(), report["tables"]["capacity_results"]["Selected Records"].tolist())
        self.assertEqual(russian["tables"]["group_counts"]["Группа"].tolist(), report["tables"]["group_counts"]["Group"].tolist())
        self.assertIn('lang="ru"', russian["html"])
        self.assertIn("Ложные тревоги", russian["html"])
        self.assertNotIn("Key Findings", russian["html"])
        self.assertNotIn("Limited Outcome Support", russian["html"])
        self.assertEqual(russian["html"].count("<svg "), 2)
        self.assertNotIn("<script", russian["html"])
        pd.testing.assert_frame_equal(comparison["summary"], original["summary"])
        pd.testing.assert_frame_equal(report["tables"]["scope"], original_report["tables"]["scope"])
        self.assertEqual(report["html"], original_report["html"])

    def test_locale_covers_no_groups_missing_identity_and_escaped_user_text(self):
        comparison, report = sample_audit(dataset_name='<script>alert(1)</script>', group_columns=[], group_references={}, entity_id_column=None)
        russian = present_report(report, comparison, "ru")
        self.assertIn("&lt;script&gt;", russian["html"])
        self.assertNotIn("<script>", russian["html"])
        self.assertTrue(any("ID студента не указан" in text for text in russian["limitations"]))
        self.assertTrue(any("только общие" in row["text"] for row in russian["findings"]))
        english = present_report(report, comparison, "en")
        self.assertEqual(english["findings"], report["findings"])

    def test_locale_handles_cluster_support_missing_groups_and_cutoff_ties(self):
        frame = pd.DataFrame({"row": range(8), "student": [1, 1, 2, 2, 3, 3, 4, 4],
                              "outcome": ["A", "B", "A", "B", "A", "B", "A", "X"],
                              "score": [.8] * 8, "group": ["TC", "TC", "TP", "TP", None, "TC", "TP", "TC"]})
        comparison, report = build_uploaded_audit(frame, dataset_name="Repeated", target_column="outcome", positive_value="A",
            negative_values=["B"], excluded_values=["X"], score_column="score", decision_unit="course_enrollment",
            decision_id_columns=["row"], entity_id_column="student", group_columns=["group"], group_references={"group": "TC"},
            review_shares=[.2, .5], focus_share=.2)
        translated = present_report(report, comparison, "ru")
        rules = {f["rule"] for f in translated["findings"]}
        self.assertTrue({"record_and_student_units", "cutoff_ties", "missing_group_values"}.issubset(rules))
        self.assertNotIn("Component Interval Unavailable", translated["html"])

    def test_chart_values_are_existing_audit_results_and_single_share_is_supported(self):
        comparison, _ = sample_audit()
        data = capacity_chart_data(comparison["summary"], "counts", "ru")
        self.assertEqual(data.loc[data.metric.eq("Найдено случаев"), "value"].tolist(), comparison["summary"].found_positives.tolist())
        rates = capacity_chart_data(comparison["summary"], "rates")
        self.assertTrue(rates.value.between(0, 100).all())
        capacity_chart(comparison["summary"], "rates", "ru").to_dict(validate=True)
        single = charts_html(comparison["summary"].iloc[:1], "ru")
        self.assertNotIn("nan", single)
        self.assertNotIn("<script", single)

    def test_input_errors_are_readable_in_russian(self):
        self.assertIn("от 0 до 1", error_text(ValueError("Score column must contain numeric probabilities"), "ru"))
        self.assertIn("dni_hash", error_text(ValueError("ID column contains missing or blank values: dni_hash"), "ru"))


class AppFlowTests(unittest.TestCase):
    def test_preset_run_language_switch_and_changed_inputs(self):
        uploaded = BytesIO(SAMPLE)
        uploaded.name = "sample_predictions.csv"
        with patch("streamlit.file_uploader", return_value=uploaded):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
            app.selectbox(key="preset_id").set_value("example").run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            app.button(key="run_audit").click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual([m.value for m in app.metric], ["16", "4", "2", "5", "2"])
            saved = app.session_state["audit_result_v2"]
            with patch("eduai_app_service.audit_review_shares", side_effect=AssertionError("Language switch reran audit")):
                app.selectbox(key="language").set_value("ru").run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual([m.value for m in app.metric], ["16", "4", "2", "5", "2"])
            self.assertEqual(app.metric[0].label, "Проверено строк")
            reference = next(widget for widget in app.selectbox if widget.label.startswith("Базовая группа для"))
            self.assertEqual(reference.proto.placeholder, "Без базовой группы")
            self.assertEqual(app.session_state["audit_result_v2"]["signature"], saved["signature"])
            name_input = next(text for text in app.text_input if text.label == "Название выборки")
            name_input.set_value("Changed cohort").run(timeout=30)
            self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
