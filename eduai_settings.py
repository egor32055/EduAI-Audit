"""Portable, versioned audit settings. Never contains uploaded records."""

from copy import deepcopy
import json
import math

from eduai_presets import PRESETS


TIMINGS = ["", "At enrollment", "At the end of the first semester", "At the end of an academic year"]
HORIZONS = ["", "By the end of the first semester", "By the end of the first year",
            "By the end of an academic year", "By the end of the programme"]
AUDIT_FIELDS = {
    "dataset_name", "target_column", "score_column", "positive_value", "negative_values", "excluded_values",
    "decision_unit", "decision_id_columns", "entity_id_column", "group_columns", "group_references",
    "review_shares", "focus_share", "prediction_timing", "outcome_horizon", "use_source_row_number",
}


def _reject():
    raise ValueError("The settings file has an invalid structure or unsupported values.")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) != {"application", "version", "csv", "preset_id", "audit"}:
        _reject()
    if settings["application"] != "EduAI-Audit" or type(settings["version"]) is not int or settings["version"] != 1:
        raise ValueError("This settings file is not a supported EduAI-Audit version.")
    csv = settings["csv"]
    if not isinstance(csv, dict) or set(csv) != {"delimiter", "encoding"}:
        _reject()
    if csv["delimiter"] not in (",", ";", "\t", "|") or csv["encoding"] not in ("utf-8-sig", "cp1251"):
        _reject()
    if not isinstance(settings["preset_id"], str) or settings["preset_id"] not in PRESETS:
        _reject()
    config = settings["audit"]
    if not isinstance(config, dict) or set(config) != AUDIT_FIELDS:
        _reject()
    for name in ("dataset_name", "target_column", "score_column", "positive_value"):
        if not isinstance(config[name], str) or not config[name].strip():
            _reject()
    if config["decision_unit"] not in ("student", "course_enrollment", "student_period", "record"):
        _reject()
    if config["entity_id_column"] is not None and (not isinstance(config["entity_id_column"], str) or not config["entity_id_column"].strip()):
        _reject()
    for name in ("negative_values", "excluded_values", "decision_id_columns", "group_columns"):
        values = config[name]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            _reject()
        if len(values) != len(set(values)):
            _reject()
    if not config["negative_values"] or type(config["use_source_row_number"]) is not bool:
        _reject()
    if config["use_source_row_number"] and config["decision_id_columns"]:
        _reject()
    if not config["use_source_row_number"] and not config["decision_id_columns"]:
        _reject()
    labels = [config["positive_value"], *config["negative_values"], *config["excluded_values"]]
    if len(labels) != len(set(labels)):
        _reject()
    refs = config["group_references"]
    if not isinstance(refs, dict) or any(c not in config["group_columns"] or not isinstance(v, str) for c, v in refs.items()):
        _reject()
    if set(config["group_columns"]).intersection([*config["decision_id_columns"], config["entity_id_column"], config["target_column"], config["score_column"]]):
        _reject()
    shares = config["review_shares"]
    if not isinstance(shares, list) or not shares or any(
        type(v) not in (float, int) or not 0 < v <= 1 or not math.isfinite(v) or
        not math.isclose(v * 100, round(v * 100), abs_tol=1e-9) for v in shares
    ):
        _reject()
    if len(set(shares)) != len(shares) or type(config["focus_share"]) not in (int, float) or config["focus_share"] not in shares:
        _reject()
    if config["prediction_timing"] not in TIMINGS or config["outcome_horizon"] not in HORIZONS:
        _reject()
    return deepcopy(settings)


def read_settings(contents):
    if not contents or len(contents) > 262144:
        raise ValueError("Choose a settings JSON file smaller than 256 KB.")
    try:
        data = json.loads(contents.decode("utf-8-sig"), object_pairs_hook=_object,
                          parse_constant=lambda _: _reject())
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("The settings file is not valid UTF-8 JSON.") from exc
    return validate_settings(data)


def write_settings(config, *, preset_id, delimiter, encoding):
    data = validate_settings(dict(application="EduAI-Audit", version=1, preset_id=preset_id,
                                  csv=dict(delimiter=delimiter, encoding=encoding), audit=config))
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def widget_settings(settings, digest):
    """Map a validated profile to canonical widget values before widgets render."""
    prefix = digest[:16] + ":" + settings["preset_id"] + ":"
    config = settings["audit"]
    fields = {"name": "dataset_name", "target": "target_column", "score": "score_column",
              "positive": "positive_value", "negative": "negative_values", "excluded": "excluded_values",
              "unit": "decision_unit", "keys": "decision_id_columns", "entity": "entity_id_column",
              "groups": "group_columns", "row_key": "use_source_row_number", "focus": "focus_share",
              "timing_choice": "prediction_timing", "horizon_choice": "outcome_horizon"}
    values = {prefix + key: deepcopy(config[field]) for key, field in fields.items()}
    values.update({prefix + "reference:" + column: config["group_references"].get(column) for column in config["group_columns"]})
    values[prefix + "share_choices"] = sorted(round(100 * share) for share in config["review_shares"])
    return {**values, **settings["csv"], "preset_id": settings["preset_id"]}
