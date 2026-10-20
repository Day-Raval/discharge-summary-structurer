# Planted traps in the synthetic notes

Each note in `evals/notes/` has a hand-made gold extraction (`note-0N.gold.json`).
The notes and gold files live outside the skill folder on purpose: the model must never see the answers while it extracts.
These are the traps the gold files answer. `validate.py` catches ungrounded values; most traps below are grounded
but wrong, so only `score.py` (gold comparison) catches them.

| Note | Trap | Wrong answer | Right answer (gold) |
|---|---|---|---|
| 01 | Negated diagnosis: "Acute myocardial infarction was ruled out" | MI listed as a secondary diagnosis | Not listed |
| 01 | Dose changed: furosemide 20 mg to 40 mg | `continued`, or dose 20 mg | `changed`, dose 40 mg |
| 01 | Home med stopped: amlodipine | `continued`, or left out | `stopped`, dose null |
| 01 | NKDA | `not_documented`, or an empty status | `nkda` with its quote |
| 01 | Inpatient-only drug: IV furosemide in the hospital course | Listed as a discharge med | Only the discharge list counts |
| 01 | Pending lab: TSH | Left out | One pending result |
| 02 | No allergy line at all | `nkda` | `not_documented`, evidence null |
| 02 | Historical med: warfarin stopped in 2024 | Listed as `stopped` | Not listed: not a change at this discharge |
| 02 | Follow-up with no timeframe | A guessed timeframe | `timeframe: null` |
| 02 | Nothing pending | An invented pending result | Empty list |
| 03 | Narrative prose, dates written out ("June 3, 2026") | Dates left null or wrong format | ISO dates with the written-out quote |
| 03 | Negated diagnosis: pneumonia "excluded" | Pneumonia listed | Not listed |
| 03 | Inpatient-only drug: IV ceftriaxone | Listed as a discharge med | Not listed |
| 03 | Dose changed in prose: insulin glargine 20 to 24 units | Dose 20 units | `changed`, dose 24 units |
| 03 | Two allergies with reactions in one sentence | One allergy, or reactions dropped | Two items, each with its reaction |
