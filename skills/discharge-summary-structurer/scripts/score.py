#!/usr/bin/env python3
"""Score extractions against gold extractions, field by field. Standard library only.

Usage: python3 score.py GOLD.json EXTRACTION.json [GOLD2.json EXTRACTION2.json ...] [--json] [--min-f1 0.9]

Every fact counts once: a date, a diagnosis, each medication's presence, status, dose, route and frequency,
each allergy and its reaction, each follow-up and its timeframe, and so on.
  TP  extraction matches gold        FP  extraction states something gold doesn't (or states it wrong)
  FN  gold states something the extraction misses (or states wrong)
A wrong value counts as both FP and FN. Evidence quotes are not scored here; validate.py checks those.
Prints precision, recall and F1 per field and overall, then every mismatch. Exit 1 if --min-f1 is not met.
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

STOP = {"and", "or", "the", "of", "with", "to", "for", "in", "on", "a", "an", "at", "by", "per", "as", "due"}
# fields whose free text is compared loosely; everything else must match exactly after normalizing
LISTS = {
    "secondary_diagnoses": ("value", []),
    "procedures": ("value", ["date"]),
    "pending_results": ("value", []),
    "follow_up": ("with", ["timeframe"]),
    "discharge_medications": ("name", ["status", "dose", "route", "frequency"]),
    "allergies.items": ("value", ["reaction"]),
}
ROUTES = {"po": "oral", "by mouth": "oral", "oral": "oral", "orally": "oral", "sc": "subcutaneous", "subq": "subcutaneous",
          "subcutaneous": "subcutaneous", "subcutaneously": "subcutaneous", "iv": "intravenous", "intravenous": "intravenous",
          "inhaled": "inhaled", "inhalation": "inhaled"}


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if w not in STOP}


def similarity(a, b):
    """0 if the phrases don't match; otherwise higher for closer matches (shared words over the longer phrase)."""
    wa, wb = words(a), words(b)
    if not wa or not wb or len(wa & wb) / min(len(wa), len(wb)) < 0.6:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def same_text(a, b):
    """Loose match for names and phrases: most of the shorter phrase's words appear in the longer one."""
    return similarity(a, b) > 0


def pair_up(golds, exts, key):
    """Best matches first, so 'chronic kidney disease' can't steal the 'chronic obstructive pulmonary disease' slot."""
    pairs = sorted(((similarity(g.get(key), e.get(key)), i, j) for i, g in enumerate(golds) for j, e in enumerate(exts)),
                   reverse=True)
    used_g, used_e, matched = set(), set(), {}
    for sim, i, j in pairs:
        if sim > 0 and i not in used_g and j not in used_e:
            used_g.add(i); used_e.add(j); matched[i] = j
    return matched


def norm(field, value):
    if value is None:
        return None
    v = str(value).strip().lower()
    if field == "dose":
        return " ".join(re.findall(r"\d+(?:\.\d+)?|[a-z]+", v))  # "40mg" == "40 mg"
    if field == "route":
        return ROUTES.get(v, v)
    if field in ("timeframe", "frequency", "reaction"):
        return " ".join(sorted(words(v)))
    return v


def same_attr(field, a, b):
    if field in ("frequency", "timeframe", "reaction") and a is not None and b is not None:
        return same_text(a, b) or norm(field, a) == norm(field, b)
    return norm(field, a) == norm(field, b)


def items(data, field):
    if field == "allergies.items":
        return (data.get("allergies") or {}).get("items") or []
    return data.get(field) or []


def score_pair(gold, ext):
    counts = defaultdict(lambda: [0, 0, 0])  # field -> [tp, fp, fn]
    misses = []

    def scalar(field, g, e):
        if g is None and e is None:
            return
        if g is not None and e is not None and same_attr(field.split(".")[-1], g, e):
            counts[field][0] += 1
            return
        if e is not None:
            counts[field][1] += 1
        if g is not None:
            counts[field][2] += 1
        misses.append(f"{field}: expected {g!r}, got {e!r}")

    for key in ("admission_date", "discharge_date", "discharge_disposition"):
        scalar(key, (gold.get(key) or {}).get("value"), (ext.get(key) or {}).get("value"))
    g_pd, e_pd = (gold.get("principal_diagnosis") or {}).get("value"), (ext.get("principal_diagnosis") or {}).get("value")
    if g_pd and e_pd and same_text(g_pd, e_pd):
        counts["principal_diagnosis"][0] += 1
    else:
        scalar("principal_diagnosis", g_pd, e_pd)
    scalar("allergies.status", (gold.get("allergies") or {}).get("status"), (ext.get("allergies") or {}).get("status"))

    for field, (name_key, attrs) in LISTS.items():
        golds, exts = items(gold, field), items(ext, field)
        matched = pair_up(golds, exts, name_key)
        for i, g in enumerate(golds):
            if i not in matched:
                counts[field][2] += 1
                misses.append(f"{field}: missed {g.get(name_key)!r}")
                continue
            match = exts[matched[i]]
            counts[field][0] += 1
            for attr in attrs:
                scalar(f"{field}.{attr}", g.get(attr), match.get(attr))
                if misses and misses[-1].startswith(f"{field}.{attr}:"):
                    misses[-1] = misses[-1].replace(f"{field}.{attr}:", f"{field}.{attr} ({g.get(name_key)}):", 1)
        for j, e in enumerate(exts):
            if j in matched.values():
                continue
            counts[field][1] += 1
            misses.append(f"{field}: extra {e.get(name_key)!r} (not in gold)")
    return counts, misses


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 3), round(r, 3), round(f, 3)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("files", nargs="+", help="GOLD EXTRACTION pairs")
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    p.add_argument("--min-f1", type=float, help="exit 1 if overall F1 is below this")
    args = p.parse_args(argv)
    if len(args.files) % 2:
        p.error("give files in pairs: GOLD.json EXTRACTION.json")

    total, all_misses, per_file = defaultdict(lambda: [0, 0, 0]), [], []
    for gold_path, ext_path in zip(args.files[::2], args.files[1::2]):
        gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
        ext = json.loads(Path(ext_path).read_text(encoding="utf-8"))
        counts, misses = score_pair(gold, ext)
        tp, fp, fn = (sum(c[i] for c in counts.values()) for i in range(3))
        per_file.append({"gold": Path(gold_path).name, "extraction": Path(ext_path).name,
                         "precision_recall_f1": prf(tp, fp, fn), "mismatches": misses})
        all_misses += [f"{Path(ext_path).name}: {m}" for m in misses]
        for k, c in counts.items():
            for i in range(3):
                total[k][i] += c[i]

    tp, fp, fn = (sum(c[i] for c in total.values()) for i in range(3))
    overall = prf(tp, fp, fn)
    out = {"overall": {"tp": tp, "fp": fp, "fn": fn, "precision": overall[0], "recall": overall[1], "f1": overall[2]},
           "fields": {k: dict(zip(("tp", "fp", "fn", "precision", "recall", "f1"), (*c, *prf(*c)))) for k, c in sorted(total.items())},
           "files": per_file}
    if args.json:
        json.dump(out, sys.stdout, indent=2)
        print()
    else:
        print(f"{'field':<38}{'TP':>4}{'FP':>4}{'FN':>4}{'P':>7}{'R':>7}{'F1':>7}")
        for k, c in sorted(total.items()):
            print(f"{k:<38}{c[0]:>4}{c[1]:>4}{c[2]:>4}" + "".join(f"{x:>7.3f}" for x in prf(*c)))
        print(f"{'OVERALL':<38}{tp:>4}{fp:>4}{fn:>4}" + "".join(f"{x:>7.3f}" for x in overall))
        print("\nMismatches:" if all_misses else "\nNo mismatches.")
        for m in all_misses:
            print(f"  - {m}")
    return 1 if args.min_f1 is not None and overall[2] < args.min_f1 else 0


if __name__ == "__main__":
    sys.exit(main())
