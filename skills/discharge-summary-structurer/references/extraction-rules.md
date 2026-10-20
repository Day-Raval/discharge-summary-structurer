# Extraction rules

Read these before extracting. When a case isn't covered, prefer `null` over a guess.

## General

- **Evidence** is the shortest exact span that states the fact. It can cross a line break; the validator ignores case and whitespace. It can't skip words in the middle.
- **One quote per fact.** Don't reuse a long paragraph as evidence for several fields; quote the part that states each one.
- **Missing means null.** If the note doesn't state a field, the value is `null` (lists: `[]`) and its evidence is `null`. Never fill a gap from general knowledge.
- **Synthetic or real,** never add a patient name, record number or birth date: the schema has no field for them.

## Dates

- `admission_date`, `discharge_date` and procedure dates are `YYYY-MM-DD`, converted from however the note writes them ("June 3, 2026", "06/03/2026", "2026-06-03"). The quote keeps the note's own wording.
- Read `MM/DD/YYYY` as US month-first. If a date is genuinely ambiguous (e.g. "03/04" with no year), use `null`.

## Diagnoses

- `principal_diagnosis`: the one the note labels principal, primary or main. If none is labeled, use `null`; don't pick one.
- `secondary_diagnoses`: other active or chronic problems the note lists for this stay.
- **Leave out negated and excluded diagnoses**: "ruled out", "excluded", "no evidence of", "considered but". They are not diagnoses.
- Keep the note's wording for the value; trim lead-ins like "1." or "Principal diagnosis:".

## Procedures

- Tests and interventions done during this stay (imaging, operations, endoscopies). `date` is `null` if the note gives none.
- Lab draws and medications given are not procedures.

## Allergies

| Note says | `status` | `items` | `evidence` |
|---|---|---|---|
| Lists one or more allergies | `documented` | one item each, `reaction` if stated else `null` | the allergy line or sentence |
| "NKDA", "No known drug allergies", "No known allergies" | `nkda` | `[]` | that phrase |
| Nothing about allergies | `not_documented` | `[]` | `null` |

## Discharge medications

Only the medications the note gives **for after discharge**, including those it says to stop. Leave out:
- drugs given only in hospital (IV doses in the hospital course, one-time doses)
- historical medications already stopped before this admission ("previously on warfarin, stopped in 2024")

| Note says | `status` |
|---|---|
| New, started, "NEW", "begin" | `new` |
| Dose or frequency changed, "increased", "decreased", "changed from X to Y" | `changed` (dose = the **new** dose) |
| Continue, resume, home medication unchanged | `continued` |
| Stop, discontinue, "STOPPED" at this discharge | `stopped` (dose, route, frequency = `null`) |
| No word about change | `continued` only if the note calls it a home medication; otherwise `new`, and add the path to `needs_review` |

- `dose`: number and unit as written ("40 mg", "24-26 mg", "24 units"). `route`: as written ("PO", "by mouth", "subcutaneous"). `frequency`: as written, including duration or "as needed" ("once daily for 28 days").
- The validator checks that every number in `dose` appears in that medication's quote, so quote the line that holds the dose.

## Follow-up

- Appointments or visits **after discharge** with a person, clinic or specialty. `timeframe` as written ("1 week", "within 2 weeks"); `null` if none given. Don't guess one.
- Therapy or care delivered at the discharge destination is not a follow-up.

## Pending results

- Tests whose results were not back at discharge ("pending", "to follow", "awaiting"). Use the test's name as the value.

## Disposition

| Note says | `value` |
|---|---|
| Home, self-care | `home` |
| Home with home health, visiting nurse, services | `home_with_services` |
| Skilled nursing facility, SNF, nursing home for skilled care | `skilled_nursing` |
| Inpatient rehabilitation facility, acute rehab | `rehab` |
| Hospice | `hospice` |
| Left against medical advice | `left_ama` |
| Anything else stated | `other` |
| Not stated | `null` |
