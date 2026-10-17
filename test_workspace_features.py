"""Reusable settings, pre-audit population checks, interval plots, and aggregate exports."""

from copy import deepcopy
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from eduai_app_service import build_uploaded_audit, load_prediction_csv, preview_uploaded_audit
from eduai_charts import group_chart, group_chart_data, group_charts_html
from eduai_exports import export_tables, table_csv, tables_zip
from eduai_settings import read_settings, widget_settings, write_settings
from test_presentation import ROOT, SAMPLE, sample_audit
from eduai_presets import preset_defaults


def config_for(frame=None):
    config = preset_defaults("example", frame if frame is not None else load_prediction_csv(SAMPLE))
    config.update(dataset_name="Example", review_shares=[.15, .2, .3], focus_share=.2,
                  prediction_timing="At enrollment", outcome_horizon="By the end of the first year")
    return config


def settings_for(config=None, **csv):
    return write_settings(config or config_for(), preset_id="example", delimiter=csv.get("delimiter", ","), encoding=csv.get("encoding", "utf-8-sig"))


class SettingsTests(unittest.TestCase):
    def test_roundtrip_preserves_codes_choices_and_does_not_export_records(self):
        config = config_for()
        config["positive_value"] = "001"
        settings = read_settings(settings_for(config, delimiter=";", encoding="cp1251"))
        self.assertEqual(settings["audit"], config)
        self.assertEqual(settings["csv"], {"delimiter": ";", "encoding": "cp1251"})
        state = widget_settings(settings, "a" * 64)
        self.assertEqual(state["aaaaaaaaaaaaaaaa:example:share_choices"], [15, 20, 30])
        self.assertEqual(state["aaaaaaaaaaaaaaaa:example:positive"], "001")
        self.assertNotIn("records", settings)

    def test_invalid_profiles_fail_before_any_state_is_produced(self):
        base = read_settings(settings_for())
        for field, value in [("review_shares", [True]), ("review_shares", [.155]), ("focus_share", .9),
                             ("group_references", {"not_a_group": "X"}), ("negative_values", [base["audit"]["positive_value"]]),
                             ("prediction_timing", "invented"), ("use_source_row_number", "false")]:
            with self.subTest(field=field, value=value):
                bad = deepcopy(base)
                bad["audit"][field] = value
                with self.assertRaises(ValueError):
                    read_settings(json.dumps(bad).encode())
        for contents in [b'{"version":1,"version":2}', b'{"value":NaN}', b'not json', b'{}' * 150000]:
            with self.assertRaises(ValueError):
                read_settings(contents)

    def test_import_is_atomic_and_restores_configuration_without_running_audit(self):
        csv = BytesIO(SAMPLE)
        csv.name = "different_filename.csv"
        profile = BytesIO(settings_for())
        profile.name = "settings.json"
        def upload(label, **kwargs):
            return csv if kwargs["key"] == "upload_file" else profile
        with patch("streamlit.file_uploader", side_effect=upload):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
            with patch("eduai_app_service.audit_review_shares", side_effect=AssertionError("Import ran audit")):
                app.button(key="apply_settings").click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.selectbox(key="preset_id").value, "example")
            self.assertEqual(next(w for w in app.selectbox if w.label == "Dataset name").value, "Example")
            self.assertFalse(app.button(key="run_audit").disabled)
            self.assertEqual(len(app.metric), 0)
            app.button(key="run_audit").click().run(timeout=30)
            self.assertEqual([m.value for m in app.metric], ["16", "4", "2", "5", "2"])
            old_signature = app.session_state["audit_result_v2"]["signature"]
            bad_config = config_for()
            bad_config["score_column"] = "missing_probability"
            profile = BytesIO(settings_for(bad_config))
            profile.name = "bad.json"
            app.button(key="apply_settings").click().run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("Missing columns" in error.value for error in app.error))
            self.assertEqual(app.session_state["audit_result_v2"]["signature"], old_signature)


class PreviewTests(unittest.TestCase):
    def test_preview_matches_final_population_and_does_not_rank_or_run_bootstrap(self):
        frame = load_prediction_csv(SAMPLE)
        before = frame.copy(deep=True)
        config = config_for()
        with patch("eduai_app_service.audit_review_shares", side_effect=AssertionError("Preview ran audit")):
            preview = preview_uploaded_audit(frame, config)
        comparison, _ = build_uploaded_audit(frame, **config)
        self.assertEqual((preview["input_records"], preview["excluded_records"], preview["audited_records"],
                          preview["positive_records"], preview["negative_records"], preview["unique_students"]),
                         (18, 2, 16, 7, 9, 16))
        self.assertEqual(preview["missing_group_records"], comparison["input_validation"]["missing_group_records"])
        pd.testing.assert_frame_equal(before, frame)

    def test_invalid_excluded_scores_keys_and_absent_references_fail_preview(self):
        frame = load_prediction_csv(SAMPLE)
        config = config_for()
        bad = frame.copy()
        bad.loc[bad[config["target_column"]].isin(config["excluded_values"]), config["score_column"]] = "1.5"
        with self.assertRaisesRegex(ValueError, "finite probabilities"):
            preview_uploaded_audit(bad, config)
        with self.assertRaisesRegex(ValueError, "Duplicate decision keys"):
            preview_uploaded_audit(pd.concat([frame, frame.iloc[:1]], ignore_index=True), config)
        config["group_references"] = {"study_mode": "absent"}
        with self.assertRaisesRegex(ValueError, "Reference group not found"):
            preview_uploaded_audit(frame, config)


class ChartExportTests(unittest.TestCase):
    def test_group_plot_uses_original_estimates_and_never_fakes_missing_intervals(self):
        comparison, _ = sample_audit(group_references={"study_mode": "Full-time"})
        audit = deepcopy(comparison["reports"][.2])
        source = audit["group_uncertainty"].loc[lambda f: f.group_column.eq("study_mode")]
        data = group_chart_data(audit, "study_mode", "ru")
        np.testing.assert_array_equal(data.estimate_pct, source.estimate_pct)
        self.assertTrue(data.point_kind.eq("Базовая группа").any())
        row = source.index[0]
        audit["group_uncertainty"].loc[row, ["ci_status", "ci_lower_pct", "ci_upper_pct"]] = ["Missing Entity ID", 0, 100]
        data = group_chart_data(audit, "study_mode", "ru")
        self.assertTrue(pd.isna(data.loc[row, "ci_lower_pct"]))
        self.assertEqual(data.loc[row, "interval_status"], "Не указан ID студента")
        for metric in ["recall_pct", "false_positive_rate_pct"]:
            group_chart(audit, "study_mode", metric, "ru").to_dict(validate=True)
        html = group_charts_html(audit, "ru")
        self.assertEqual(html.count('<svg '), 2)
        self.assertNotIn('<script', html)
        self.assertNotIn('nan', html)
        self.assertIn('Не указан ID студента', html)

    def test_csv_zip_roundtrip_keeps_numeric_values_all_shares_and_no_student_rows(self):
        comparison, report = sample_audit()
        before = comparison["summary"].copy(deep=True)
        tables = export_tables(comparison, report)
        parsed = pd.read_csv(BytesIO(table_csv(tables["capacity_results"])))
        np.testing.assert_allclose(parsed.recall_pct, comparison["summary"].recall_pct)
        self.assertEqual(set(tables["group_counts"].review_share_pct), {15, 20, 30})
        self.assertNotIn("student_id", tables["group_counts"].columns)
        with ZipFile(BytesIO(tables_zip(tables, report))) as archive:
            self.assertEqual(set(archive.namelist()), {name + ".csv" for name in tables} | {"manifest.json"})
            self.assertIn("unavailable, not zero", json.loads(archive.read("manifest.json"))["notes"])
        pd.testing.assert_frame_equal(before, comparison["summary"])


if __name__ == "__main__":
    unittest.main()
