"""One-click examples run real audits and cannot leak into the user's upload."""

from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).parent


class ExampleFlowTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def test_single_example_is_ready_without_upload_and_resets_to_known_settings(self):
        app = self.app()
        app.selectbox(key="delimiter").set_value(";").run()
        with patch("eduai_app_service.audit_review_shares", side_effect=AssertionError("Example loading ran an audit")):
            app.button(key="try_example").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.button(key="run_audit").disabled)
        self.assertEqual(app.selectbox(key="delimiter").value, ",")
        self.assertEqual(app.selectbox(key="preset_id").value, "example")
        self.assertFalse(app.metric)
        self.assertTrue(any("artificial example data" in message.value for message in app.info))
        self.assertFalse(next(w for w in app.checkbox if w.label == "Compare two prediction columns").value)
        app.button(key="run_audit").click().run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["16", "4", "2", "5", "2"])
        self.assertIn("settings_download", [d.key for d in app.get("download_button")])
        self.assertIn("report_download", [d.key for d in app.get("download_button")])
        next(w for w in app.selectbox if w.label == "Report focus share").set_value(.3).run()
        app.button(key="try_example").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(w for w in app.selectbox if w.label == "Report focus share").value, .2)
        self.assertFalse(app.metric)

    def test_switch_to_comparison_clears_old_results_and_language_keeps_new_results(self):
        app = self.app()
        app.button(key="try_example").click().run()
        app.button(key="run_audit").click().run()
        app.button(key="try_comparison_example").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.metric)
        self.assertFalse(app.button(key="run_audit").disabled)
        self.assertTrue(next(w for w in app.checkbox if w.label == "Compare two prediction columns").value)
        self.assertEqual(next(w for w in app.selectbox if w.label == "Model B probability column").value, "dropout_probability_b")
        app.button(key="run_audit").click().run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["2", "2", "2", "10"])
        result = app.session_state["audit_result_v2"]["model_comparison"]
        for model, expected in [("A", (4, 2, 5, 2)), ("B", (4, 4, 3, 0))]:
            review = result["comparisons"][model]["reports"][.2]["review"]
            self.assertEqual(tuple(review[k] for k in ("selected_records", "found_positives", "missed_positives", "false_alarms")), expected)
        with patch("eduai_model_comparison.build_uploaded_audit", side_effect=AssertionError("Language reran audit")):
            app.selectbox(key="language").set_value("ru").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.button(key="try_example").label, "Попробовать пример")
        self.assertEqual([m.value for m in app.metric], ["2", "2", "2", "10"])
        self.assertIn("comparison_html", [d.key for d in app.get("download_button")])
        app.button(key="use_my_csv").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.metric)
        self.assertNotIn("example_mode", app.session_state)
        self.assertNotIn("audit_result_v2", app.session_state)
        self.assertNotIn("run_audit", [button.key for button in app.button])

    def test_return_to_existing_upload_does_not_reuse_example_mappings(self):
        contents = (ROOT / "examples" / "sample_predictions.csv").read_bytes()
        upload = BytesIO(contents)
        upload.name = "my_students.csv"
        with patch("streamlit.file_uploader", side_effect=lambda label, **kw: upload if kw["key"] == "upload_file" else None):
            app = self.app()
            self.assertTrue(app.button(key="run_audit").disabled)
            app.button(key="try_example").click().run()
            self.assertFalse(app.button(key="run_audit").disabled)
            example_key = next(w for w in app.selectbox if w.label == "Observed outcome column").key
            app.button(key="run_audit").click().run()
            app.button(key="use_my_csv").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="preset_id").value, "custom")
            target = next(w for w in app.selectbox if w.label == "Observed outcome column")
            self.assertNotEqual(target.key, example_key)
            self.assertIsNone(target.value)
            self.assertTrue(app.button(key="run_audit").disabled)
            self.assertFalse(app.metric)
            self.assertEqual(upload.getvalue(), contents)

    def test_return_restores_csv_format_and_prior_configuration_after_switching_examples(self):
        upload = BytesIO((ROOT / "examples" / "sample_predictions.csv").read_bytes().replace(b",", b";"))
        upload.name = "semicolon.csv"
        with patch("streamlit.file_uploader", side_effect=lambda label, **kw: upload if kw["key"] == "upload_file" else None):
            app = self.app()
            app.selectbox(key="delimiter").set_value(";").run()
            app.selectbox(key="encoding").set_value("cp1251").run()
            app.selectbox(key="preset_id").set_value("example").run()
            next(w for w in app.selectbox if w.label == "Report focus share").set_value(.3).run()
            app.button(key="try_example").click().run()
            app.button(key="try_comparison_example").click().run()
            app.button(key="use_my_csv").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="delimiter").value, ";")
            self.assertEqual(app.selectbox(key="encoding").value, "cp1251")
            self.assertEqual(app.selectbox(key="preset_id").value, "example")
            self.assertEqual(next(w for w in app.selectbox if w.label == "Report focus share").value, .3)
            self.assertFalse(app.button(key="run_audit").disabled)
            app.button(key="run_audit").click().run()
            self.assertEqual([m.value for m in app.metric], ["16", "5", "3", "4", "2"])


if __name__ == "__main__":
    unittest.main()
