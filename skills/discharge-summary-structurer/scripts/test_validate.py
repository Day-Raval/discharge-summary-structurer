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
    # line breaks and case differences in a quote are fine
    assert errors_for(lambda d: d["principal_diagnosis"].update(
        evidence="principal diagnosis:\n community-acquired   pneumonia")) == []


def test_consistency_errors():
    expect(lambda d: d["discharge_date"].update(value="2026-03-01", evidence="03/01"), "is before admission_date")
    expect(lambda d: d["admission_date"].update(value="2026-02-30"), "is not a real calendar date")
    expect(lambda d: d["allergies"].update(status="nkda"), "allergies.status: is nkda but allergies are listed")
    expect(lambda d: d["principal_diagnosis"].update(value=None), "principal_diagnosis.evidence: must be null")


def test_cli():
    import contextlib, io, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        note, ext = Path(tmp, "note.txt"), Path(tmp, "out.json")
        note.write_text(NOTE, encoding="utf-8")
        ext.write_text(json.dumps(GOOD), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = validate.main([str(note), str(ext)])
        assert code == 0 and json.loads(out.getvalue())["valid"] is True
        ext.write_text("{not json", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = validate.main([str(note), str(ext)])
        assert code == 1 and "not valid JSON" in out.getvalue()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
