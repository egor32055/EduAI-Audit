"""Editable mappings for scored exports from the research prototype."""

PRESETS = {
    "custom": dict(name="Custom CSV", unit="student", target=None, positive=None,
                   negative=[], excluded=[], keys=[], entity=None, groups=[], references={}),
    "upv_2022": dict(name="UPV 2022", unit="student", target="abandono_hash", positive="A",
                     negative=["B"], excluded=[], keys=["dni_hash"], entity="dni_hash",
                     groups=["dedicacion", "desplazado_hash", "estudios_m_hash"],
                     references={"dedicacion": "TC"}),
    "oulad": dict(name="OULAD", unit="course_enrollment", target="final_result", positive="Withdrawn",
                  negative=["Pass", "Fail", "Distinction"], excluded=[],
                  keys=["id_student", "code_module", "code_presentation"], entity="id_student",
                  groups=["imd_band"], references={}),
    "uci": dict(name="UCI", unit="student", target="Target", positive="Dropout",
                negative=["Graduate"], excluded=["Enrolled"], keys=["Source Row ID"], entity=None,
                groups=["Daytime/evening attendance"], references={"Daytime/evening attendance": "Daytime"}),
    "example": dict(name="Synthetic example", unit="student", target="outcome", positive="Dropout",
                    negative=["Graduate"], excluded=["Enrolled"], keys=["student_id"], entity="student_id",
                    groups=["study_mode"], references={}),
}

SCORE_NAMES = ("Predicted Dropout Risk", "dropout_probability", "predicted_probability", "probability", "score")


def preset_defaults(preset_id, frame):
    """Use only supplied columns and labels; never infer scores from features."""
    preset = PRESETS[preset_id]
    target = preset["target"] if preset["target"] in frame.columns else None
    values = frame[target].dropna().tolist() if target else []
    keys = preset["keys"] if all(c in frame.columns for c in preset["keys"]) else []
    groups = [c for c in preset["groups"] if c in frame.columns]
    references = {}
    for column, value in preset["references"].items():
        if column in groups and value in frame[column].dropna().astype(str).tolist():
            references[column] = value
    return dict(
        target_column=target,
        score_column=next((c for c in SCORE_NAMES if c in frame.columns and c != target), None),
        positive_value=preset["positive"] if preset["positive"] in values else None,
        negative_values=[v for v in preset["negative"] if v in values],
        excluded_values=[v for v in preset["excluded"] if v in values],
        decision_unit=preset["unit"], decision_id_columns=list(keys),
        entity_id_column=preset["entity"] if preset["entity"] in frame.columns else None,
        group_columns=groups, group_references=references,
        use_source_row_number=False,
    )
