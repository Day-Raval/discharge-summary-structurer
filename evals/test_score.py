#!/usr/bin/env python3
"""Check score.py counts matches and mistakes correctly. Run from the repo root: python3 evals/test_score.py"""
import contextlib, copy, io, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills" / "discharge-summary-structurer" / "scripts"))
import score  # noqa: E402

EX = HERE / "notes"
GOLD = {i: json.loads((EX / f"note-0{i}.gold.json").read_text(encoding="utf-8")) for i in (1, 2, 3)}


def totals(gold, ext):
    counts, misses = score.score_pair(gold, ext)
    return tuple(sum(c[i] for c in counts.values()) for i in range(3)), misses


def test_gold_scores_perfect():
    for i, g in GOLD.items():
        (tp, fp, fn), misses = totals(g, g)
        assert fp == fn == 0 and tp > 0 and misses == [], (i, misses)


def test_trap_falling_extraction():
    gold = GOLD[1]
    ext = copy.deepcopy(gold)
    ext["secondary_diagnoses"].append({"value": "Acute myocardial infarction", "evidence": "x"})  # negated dx kept: 1 FP
    furo = ext["discharge_medications"][0]
    furo.update(status="continued", dose="20 mg")                    # wrong status + old dose: 2 FP, 2 FN
    ext["discharge_medications"] = [m for m in ext["discharge_medications"] if m["name"] != "Amlodipine"]  # 1 FN
    ext["allergies"]["status"] = "not_documented"                    # NKDA missed: 1 FP, 1 FN
    ext["follow_up"][1]["timeframe"] = "within 1 week"               # guessed timeframe: 1 FP, 1 FN
    ext["pending_results"] = []                                      # TSH missed: 1 FN
    (tp, fp, fn), misses = totals(gold, ext)
    assert (fp, fn) == (5, 6), (fp, fn, misses)
    joined = "\n".join(misses)
    for frag in ("extra 'Acute myocardial infarction'", "status (Furosemide): expected 'changed', got 'continued'",
                 "missed 'Amlodipine'", "allergies.status: expected 'nkda'", "missed 'TSH'"):
        assert frag in joined, (frag, joined)


def test_equivalent_forms_match():
    gold = GOLD[1]
    ext = copy.deepcopy(gold)
    ext["discharge_medications"][0].update(dose="40mg", route="by mouth")   # spacing and route synonyms
    ext["follow_up"][1]["with"] = "Primary care physician"                   # extra word in a name
    ext["principal_diagnosis"]["value"] = "Acute on chronic systolic heart failure"
    (tp, fp, fn), misses = totals(gold, ext)
    assert fp == fn == 0, misses


def test_best_match_pairing():
    gold = {"secondary_diagnoses": [{"value": "Chronic obstructive pulmonary disease"}, {"value": "Chronic kidney disease"}]}
    ext = {"secondary_diagnoses": [{"value": "Chronic kidney disease"}, {"value": "Chronic obstructive pulmonary disease"}]}
    (tp, fp, fn), misses = totals(gold, ext)
    assert (tp, fp, fn) == (2, 0, 0), misses


def test_cli_min_f1():
    files = [str(EX / "note-01.gold.json")] * 2
    with contextlib.redirect_stdout(io.StringIO()) as out:
        assert score.main(files + ["--min-f1", "0.99"]) == 0
    assert "OVERALL" in out.getvalue()
    with contextlib.redirect_stdout(io.StringIO()) as out:
        score.main(files + ["--json"])
    assert json.loads(out.getvalue())["overall"]["f1"] == 1.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
