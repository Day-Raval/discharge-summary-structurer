---
name: discharge-summary-structurer
description: Turns a hospital discharge summary into structured JSON (admission and discharge dates, diagnoses, procedures, allergies, discharge medications with new/changed/continued/stopped status, follow-ups, pending results, disposition) where every fact carries a verbatim quote. A bundled script checks each quote against the note and the model repairs only what fails, up to 3 tries. Use when given a discharge summary as text and asked to structure it, extract its fields, or list discharge medication changes. Do not use for diagnosis, treatment advice or drug-interaction checks.
---

# Discharge Summary Structurer

You extract. A script judges. Every fact you output carries `evidence`: words copied exactly from the note. `scripts/validate.py` checks the JSON against `references/schema.json` and against the note, and you fix only what it flags.

## Workflow

1. **Get the note as text.** Use the text the user pasted or the text file they attached. If they give a PDF or an image, ask for the text (copy and paste is fine). Don't transcribe images yourself.

2. **Save the note to a working file**, exactly as given, e.g. `note.txt` in a temporary folder. The validator compares quotes against this file, so never edit or tidy it.

3. **Read the rules** in `references/extraction-rules.md` before extracting. They decide the hard cases: stopped and changed medications, ruled-out diagnoses, NKDA versus no allergy line, and what counts as a follow-up.

4. **Extract** one JSON object that follows `references/schema.json`, and write it to `extraction.json` next to the note. Every key in the schema must be present. A fact the note doesn't state is `null` (or `[]`), never a guess.

5. **Validate:**
````
   python3 <skill-folder>/scripts/validate.py note.txt extraction.json
````
   On Windows without `python3`, use `py`. If Python isn't available, say so and stop: an unchecked extraction is not this skill's output.

6. **Repair loop (at most 3 validation runs in total).**
   - `"valid": true` → go to step 7.
   - Otherwise, fix **only** the paths listed in `errors`. Don't touch anything else, even if you'd now word it differently. Run the validator again.
   - If the **third** run still fails, then for each failing path: set that field to `null` (or delete that list item), and add `"<path>: <message>"` to `needs_review`. Run the validator one last time; it must pass.

7. **Reply** in the output format below. Delete the working files afterwards unless the user asked to keep them.

## Rules

- **Quote, don't paraphrase.** `evidence` is the shortest span of the note that states the fact, copied exactly. Values may be normalized (ISO dates, enum words); quotes may not.
- **Every number comes from the note.** Doses, dates and timeframes are copied, never computed. Don't convert units or work out end dates.
- **No clinical judgment.** Don't diagnose, suggest treatment, flag interactions or comment on whether a dose is right. If asked, say this skill only structures what the note says.
- **Extract from the note alone.** Read only this skill's `references/` and the user's note. Don't look for other copies of the note or earlier extractions of it.
- **Keep data local.** Don't send the note to web tools or other services. Real patient notes are protected health information: process them only where the user is authorized to, and never save copies outside the user's own folders.

## Output format

````
## Discharge summary: structured
Admitted {admission_date} · Discharged {discharge_date} · Disposition: {discharge_disposition}

**Principal diagnosis:** {value}
**Secondary diagnoses:** {comma-separated, or "none stated"}
**Procedures:** {name (date)}, or "none stated"
**Allergies:** {items with reactions} | "NKDA" | "not documented in this note"

| Medication | Dose | Route | Frequency | Change |
(one row per discharge_medications item; stopped meds show "-" for dose, route and frequency)

**Follow-up:** {with, timeframe or "no timeframe given"}
**Pending at discharge:** {items, or "none stated"}
**Needs review:** {needs_review items, or "none"}

Checked by validate.py in {N} run(s); every fact above is quoted from the note.

### JSON
```json
{the validated extraction}
```

_Structured from the note by discharge-summary-structurer; not medical advice. Verify against the source before clinical use._
````

The summary is built only from the validated JSON: nothing appears in it that isn't in the JSON. If you made a judgment call worth flagging (a field left out on purpose, a rule applied to an unclear case), add at most 3 short lines under **Notes:** after the JSON and **before** the disclaimer. Nothing comes after the disclaimer. If the user asked for JSON only, give the JSON and the disclaimer line.

## Before you reply, check

1. The last validator run printed `"valid": true`.
2. Every fact in the summary is in the JSON, and the JSON is exactly what passed validation.
3. Medication changes are worded as the note words them; no added advice.
4. The last line is exactly: _Structured from the note by discharge-summary-structurer; not medical advice. Verify against the source before clinical use._ Any notes go above it.

## Files

- `references/schema.json`: the output contract (JSON Schema draft 2020-12)
- `references/extraction-rules.md`: how to decide each field, with the hard cases
- `scripts/validate.py`: schema, grounding, support and consistency checks; prints the errors to fix
- `scripts/score.py`: compares an extraction with a gold file the user provides, field by field (for testing the skill, not part of a normal run)
- `scripts/test_validate.py`: self-test for the validator
