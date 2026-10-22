#!/usr/bin/env python3
"""Check validate.py catches each kind of extraction mistake. Run: python3 scripts/test_validate.py"""
import copy, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate  # noqa: E402

SCHEMA = json.loads((HERE.parent / "references" / "schema.json").read_text(encoding="utf-8"))

NOTE = """DISCHARGE SUMMARY (synthetic test note)
Admission Date: 03/02/2026    Discharge Date: 03/05/2026
Principal Diagnosis: Community-acquired pneumonia, right lower lobe.
Secondary Diagnoses: Type 2 diabetes mellitus; hypertension.
Allergies: Penicillin (hives).
Procedures: Chest X-ray on 03/02/2026.
Discharge Medications:
- Levofloxacin 750 mg PO daily x 5 days (NEW)
- Metformin 500 mg PO twice daily (continue home dose)
- Lisinopril was STOPPED due to low blood pressure.
Follow-up: PCP Dr. Rivera in 1 week.
Pending: Blood cultures from 03/02 pending at discharge.
Disposition: Discharged home in stable condition.
"""

GOOD = {
    "admission_date": {"value": "2026-03-02", "evidence": "Admission Date: 03/02/2026"},
    "discharge_date": {"value": "2026-03-05", "evidence": "Discharge Date: 03/05/2026"},
    "principal_diagnosis": {"value": "Community-acquired pneumonia, right lower lobe",
                            "evidence": "Principal Diagnosis: Community-acquired pneumonia, right lower lobe."},
    "secondary_diagnoses": [
        {"value": "Type 2 diabetes mellitus", "evidence": "Type 2 diabetes mellitus"},
        {"value": "Hypertension", "evidence": "hypertension"},
    ],
    "procedures": [{"value": "Chest X-ray", "date": "2026-03-02", "evidence": "Chest X-ray on 03/02/2026."}],
    "allergies": {"status": "documented", "evidence": "Allergies: Penicillin (hives).",
                  "items": [{"value": "Penicillin", "reaction": "hives", "evidence": "Penicillin (hives)"}]},
    "discharge_medications": [
        {"name": "Levofloxacin", "dose": "750 mg", "route": "PO", "frequency": "daily x 5 days", "status": "new",
         "evidence": "Levofloxacin 750 mg PO daily x 5 days (NEW)"},
        {"name": "Metformin", "dose": "500 mg", "route": "PO", "frequency": "twice daily", "status": "continued",
         "evidence": "Metformin 500 mg PO twice daily (continue home dose)"},
        {"name": "Lisinopril", "dose": None, "route": None, "frequency": None, "status": "stopped",
         "evidence": "Lisinopril was STOPPED due to low blood pressure."},
    ],
    "follow_up": [{"with": "PCP Dr. Rivera", "timeframe": "1 week", "evidence": "PCP Dr. Rivera in 1 week."}],
    "pending_results": [{"value": "Blood cultures", "evidence": "Blood cultures from 03/02 pending at discharge."}],
    "discharge_disposition": {"value": "home", "evidence": "Discharged home in stable condition."},
    "needs_review": [],
}


def errors_for(mutate):
    data = copy.deepcopy(GOOD)
    mutate(data)
    return [e["path"] + ": " + e["message"] for e in validate.validate(NOTE, data, SCHEMA)]


def expect(mutate, *fragments):
    errs = errors_for(mutate)
    joined = " | ".join(errs)
    for frag in fragments:
        assert frag in joined, f"expected {frag!r} in: {joined or 'no errors'}"


def test_good_passes():
    assert errors_for(lambda d: None) == []


def test_schema_errors():
    expect(lambda d: d.pop("follow_up"), "follow_up: is required")
    expect(lambda d: d["admission_date"].update(value="03/02/2026"), "admission_date.value: must match")
    expect(lambda d: d["discharge_medications"][0].update(status="started"), "status: must be one of")
    expect(lambda d: d.update(patient_name="X"), "patient_name: is not an allowed field")
    expect(lambda d: d["discharge_medications"][0].pop("route"), "discharge_medications[0].route: is required")


def test_grounding_errors():
    # invented quote
    expect(lambda d: d["secondary_diagnoses"].append({"value": "Asthma", "evidence": "history of asthma"}),
           "secondary_diagnoses[2].evidence: is not a verbatim quote")
    # real quote, but the value isn't in it
    expect(lambda d: d["discharge_medications"][1].update(name="Glipizide"),
           "discharge_medications[1]: value 'Glipizide' is not supported")
    # dose changed from the note
    expect(lambda d: d["discharge_medications"][0].update(dose="500 mg"), "dose number 500 is not in its evidence")
    # a number hidden inside a bigger one doesn't count: "75" is not in "750", "5" is not in "500"
    expect(lambda d: d["discharge_medications"][0].update(dose="75 mg"), "dose number 75 is not in its evidence")
    expect(lambda d: d["discharge_medications"][1].update(dose="5 mg"), "dose number 5 is not in its evidence")
    # line breaks and case differences in a quote are fine
    assert errors_for(lambda d: d["principal_diagnosis"].update(
        evidence="principal diagnosis:\n community-acquired   pneumonia")) == []


def test_consistency_errors():
    expect(lambda d: d["discharge_date"].update(value="2026-03-01", evidence="03/01"), "is before admission_date")
    expect(lambda d: d["admission_date"].update(value="2026-02-30"), "is not a real calendar date")
    expect(lambda d: d["allergies"].update(status="nkda"), "allergies.status: is nkda but allergies are listed")
    expect(lambda d: d["principal_diagnosis"].update(value=None), "principal_diagnosis.evidence: must be null")


def test_required_evidence():
    for key in ("admission_date", "discharge_date", "principal_diagnosis", "discharge_disposition"):
        for evidence in (None, "   "):
            expect(lambda d: d[key].update(evidence=evidence), f"{key}.evidence: must contain a quote")
        assert errors_for(lambda d: d[key].update(value=None, evidence=None)) == []
    expect(lambda d: d["allergies"].update(evidence=None), "allergies.evidence: must contain a quote")
    expect(lambda d: d["allergies"].update(status="nkda", items=[], evidence=None),
           "allergies.evidence: must contain a quote")
    assert errors_for(lambda d: d["allergies"].update(status="not_documented", items=[], evidence=None)) == []
    expect(lambda d: d["pending_results"][0].update(evidence="   "),
           "pending_results[0].evidence: must contain a quote")


def test_dose_units_and_timeframe_numbers():
    for dose in ("750 g", "750 mcg", "750 mg/kg"):
        expect(lambda d: d["discharge_medications"][0].update(dose=dose),
               "discharge_medications[0].dose: dose unit")
    assert errors_for(lambda d: d["discharge_medications"][0].update(dose="750MG")) == []
    for timeframe in ("99 years", "11 weeks", "1.5 weeks"):
        expect(lambda d: d["follow_up"][0].update(timeframe=timeframe),
               "follow_up[0].timeframe: timeframe number")
    assert errors_for(lambda d: d["follow_up"][0].update(timeframe=None)) == []


def test_stopped_medication_attributes():
    for field, value in (("dose", "750 mg"), ("route", "PO"), ("frequency", "daily")):
        expect(lambda d: d["discharge_medications"][2].update({field: value}),
               f"discharge_medications[2].{field}: must be null when status is stopped")
    expect(lambda d: d["discharge_medications"][0].update(status="stopped"),
           "discharge_medications[0].dose: must be null when status is stopped",
           "discharge_medications[0].route: must be null when status is stopped",
           "discharge_medications[0].frequency: must be null when status is stopped")


def test_cli():
    import contextlib, io, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        note, ext = Path(tmp, "note.txt"), Path(tmp, "out.json")
        note.write_text(NOTE, encoding="utf-8")
        ext.write_text(json.dumps(GOOD), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = validate.main([str(note), str(ext)])
        assert code == 0 and json.loads(out.getvalue())["valid"] is True
        data = copy.deepcopy(GOOD)
        data["principal_diagnosis"].update(evidence=None)
        ext.write_text(json.dumps(data), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = validate.main([str(note), str(ext)])
        result = json.loads(out.getvalue())
        assert code == 1 and result["valid"] is False and result["error_count"] == 1
        assert set(result) == {"valid", "error_count", "errors"}
        assert result["errors"][0]["path"] == "principal_diagnosis.evidence"
        assert set(result["errors"][0]) == {"path", "message"}
        ext.write_text("{not json", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = validate.main([str(note), str(ext)])
        assert code == 1 and "not valid JSON" in out.getvalue()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
