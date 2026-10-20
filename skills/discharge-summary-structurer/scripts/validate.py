#!/usr/bin/env python3
"""Validate a structured discharge summary against the schema and the source note. Standard library only.

Usage: python3 validate.py NOTE.txt EXTRACTION.json [--schema references/schema.json]

Prints JSON {"valid": bool, "error_count": int, "errors": [{"path", "message"}]} and exits 0 if valid, 1 if not.
Checks, in order:
  1. schema: types, required fields, enums, date format, no extra fields
  2. grounding: every evidence string appears in the note (case and whitespace insensitive)
  3. support: each value is backed by its own evidence (key words of the value appear in the quote)
  4. consistency: null values have null evidence; admission <= discharge; allergy status matches items
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path

STOP = {"and", "or", "the", "of", "with", "to", "for", "in", "on", "a", "an", "at", "by", "per", "as", "needed"}


def squash(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def node_ref_parts(ref):
    return ref.lstrip("#/").split("/")


def deref(schema, root):
    while isinstance(schema, dict) and "$ref" in schema:
        target = root
        for part in node_ref_parts(schema["$ref"]):
            target = target[part]
        schema = target
    return schema


TYPES = {"string": str, "array": list, "object": dict, "null": type(None), "boolean": bool}


def check_schema(value, schema, root, path, errors):
    schema = deref(schema, root)
    if "enum" in schema and value not in schema["enum"]:
        errors.append((path, f"must be one of {schema['enum']}, got {value!r}"))
        return
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(isinstance(value, TYPES[t]) and not (t != "boolean" and isinstance(value, bool)) for t in allowed):
            errors.append((path, f"must be {' or '.join(allowed)}, got {type(value).__name__}"))
            return
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append((path, f"must be at least {schema['minLength']} characters"))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append((path, f"must match {schema['pattern']} (dates are YYYY-MM-DD)"))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append((f"{path}.{key}".lstrip("."), "is required (use null or [] if the note doesn't say)"))
        for key, sub in value.items():
            if key not in props:
                if schema.get("additionalProperties") is False:
                    errors.append((f"{path}.{key}".lstrip("."), "is not an allowed field"))
                continue
            check_schema(sub, props[key], root, f"{path}.{key}".lstrip("."), errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            check_schema(item, schema["items"], root, f"{path}[{i}]", errors)


def facts(data):
    """Yield (path, value_text, evidence) for every fact that carries evidence."""
    for key in ("admission_date", "discharge_date", "principal_diagnosis", "discharge_disposition"):
        f = data.get(key) or {}
        yield key, f.get("value"), f.get("evidence")
    for key, field in (("secondary_diagnoses", "value"), ("pending_results", "value"), ("procedures", "value"),
                       ("discharge_medications", "name"), ("follow_up", "with")):
        for i, item in enumerate(data.get(key) or []):
            yield f"{key}[{i}]", item.get(field), item.get("evidence")
    allergies = data.get("allergies") or {}
    yield "allergies", allergies.get("status"), allergies.get("evidence")
    for i, item in enumerate(allergies.get("items") or []):
        yield f"allergies.items[{i}]", item.get("value"), item.get("evidence")


def key_words(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP]


def check_note(data, note, errors):
    note_s = squash(note)
    for path, value, evidence in facts(data):
        if isinstance(evidence, str) and squash(evidence) not in note_s:
            errors.append((f"{path}.evidence", "is not a verbatim quote from the note; copy the exact words"))
        if value is None and evidence not in (None, ""):
            errors.append((f"{path}.evidence", "must be null when value is null"))
        # dates and enums are normalized forms, so only free-text values are checked against their quote
        free_text = path.split(".")[0].split("[")[0] in (
            "principal_diagnosis", "secondary_diagnoses", "pending_results", "procedures", "discharge_medications",
            "follow_up") or path.startswith("allergies.items")
        if free_text and isinstance(value, str) and isinstance(evidence, str):
            words = key_words(value)
            if words and not any(w in squash(evidence) for w in words):
                errors.append((path, f"value {value!r} is not supported by its evidence quote"))
    for i, med in enumerate(data.get("discharge_medications") or []):
        dose, ev = med.get("dose"), med.get("evidence")
        if isinstance(dose, str) and isinstance(ev, str):
            quoted = set(re.findall(r"\d+(?:\.\d+)?", ev))  # whole numbers, so "4" doesn't match inside "40"
            for num in re.findall(r"\d+(?:\.\d+)?", dose):
                if num not in quoted:
                    errors.append((f"discharge_medications[{i}].dose", f"dose number {num} is not in its evidence quote"))


def check_consistency(data, errors):
    def as_date(key):
        v = (data.get(key) or {}).get("value")
        try:
            return date.fromisoformat(v) if isinstance(v, str) else None
        except ValueError:
            errors.append((f"{key}.value", f"{v!r} is not a real calendar date"))
            return None
    adm, dis = as_date("admission_date"), as_date("discharge_date")
    if adm and dis and adm > dis:
        errors.append(("discharge_date.value", "is before admission_date"))
    allergies = data.get("allergies") or {}
    status, items = allergies.get("status"), allergies.get("items") or []
    if status == "documented" and not items:
        errors.append(("allergies.items", "status is documented but no allergies are listed"))
    if status in ("nkda", "not_documented") and items:
        errors.append(("allergies.status", f"is {status} but allergies are listed"))
    if status == "not_documented" and allergies.get("evidence"):
        errors.append(("allergies.evidence", "must be null when status is not_documented"))


def validate(note, data, schema):
    errors = []
    check_schema(data, schema, schema, "", errors)
    if not errors:  # grounding checks assume the shape is right
        check_note(data, note, errors)
        check_consistency(data, errors)
    return [{"path": p, "message": m} for p, m in errors]


def main(argv=None):
    here = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("note")
    p.add_argument("extraction")
    p.add_argument("--schema", default=str(here / "references" / "schema.json"))
    args = p.parse_args(argv)

    note = Path(args.note).read_text(encoding="utf-8")
    try:
        data = json.loads(Path(args.extraction).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors = [{"path": "", "message": f"not valid JSON: {e}"}]
    else:
        errors = validate(note, data, json.loads(Path(args.schema).read_text(encoding="utf-8")))
    json.dump({"valid": not errors, "error_count": len(errors), "errors": errors}, sys.stdout, indent=2)
    print()
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
