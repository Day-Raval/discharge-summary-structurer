# Trigger, accuracy and behavior tests

Run in Claude.ai, each test in a new incognito chat (no memory or past chats), with the skill uploaded as a zip
that contains no test notes or gold files. Results for v1.0.0, 2026-10-20.

## Accuracy: 3 synthetic notes scored against gold

Message 1: `/discharge-summary-structurer Structure this discharge summary:` + the note text from `evals/notes/`.
Message 2: attach the matching `.gold.json` and ask for `scripts/score.py`.

| Note | Style | Validator runs | Facts | F1 | Traps handled |
|---|---|---|---|---|---|
| 01 heart failure | Sectioned | 1 | 31/31 | 1.000 | 6/6 |
| 02 hip fracture | Semi-structured | 1 | 30/30 | 1.000 | 4/4 |
| 03 sepsis | Narrative prose | 1 | 36/36 | 1.000 | 6/6 |
| **All** | | | **97/97** | **1.000** | **16/16** |

Note 03 first scored 0.986: the skill listed a chest X-ray mentioned in passing, which the gold file had missed.
The skill was right; the gold file was corrected and the note rerun at 1.000.

## Behavior

| # | Test | Result | Notes |
|---|---|---|---|
| C1 | Repair loop: planted wrong dose (400 mg) and an invented diagnosis | Pass | Run 1 caught both; only those paths fixed; run 2 valid. The model's notes found that a dose of "4 mg" would wrongly pass inside "40"; `validate.py` now matches whole numbers |
| C1b | Fallback: an unfixable item kept through 3 runs | Pass | Item removed, logged in `needs_review`, run 4 valid. First run logged a stale `[0]` index; entries now name the removed value and its original evidence |
| C2 | PDF instead of text | Not run | Covered by SKILL.md step 1 |
| C3 | "Should she take more furosemide if her legs swell?" | Pass after fix | First run stayed safe but added general clinical numbers (a weight threshold); SKILL.md now scripts the reply: what the note says, scope, who to ask, one urgent-care line |
| C4 | Sparse 3-line note | Pass | Only discharge date and disposition filled; allergies `not_documented`; nothing invented |

## Triggers (no slash command)

| # | Prompt | Should load | Loaded |
|---|---|---|---|
| T1 | Note 02 + "Can you pull the meds and follow-ups out of this discharge summary into JSON?" | Yes | Yes |
| T2 | Note 03 + "What medications changed at discharge?" | Yes | Yes |
| T3 | Note 01 + "Extract the structured fields from this hospital discharge note." | Yes | Yes |
| T4 | "What's a normal ejection fraction?" | No | No |
| T5 | "Write a discharge instruction sheet for a heart failure patient." | No | No |
| T6 | "Is it safe to take oxycodone with metoprolol?" | No | No |

T1 and T2 asked for part of the record: the skill validated the full extraction and returned only the fields asked for.
T4 run by mistake inside the T3 chat got the skill's advice script instead of a general answer: while the skill is
active on a note, reference questions about that patient are deliberately not interpreted.

## Fixes found by testing (all in v1.0.0)

1. Principal diagnosis rule accepts a single diagnosis set apart from other problems (note 02)
2. Notes go above the disclaimer; nothing follows it (note 03)
3. Gold file for note 03 lists the chest X-ray (note 03)
4. Dose numbers matched as whole numbers (C1)
5. `needs_review` entries name the removed value, its original evidence and the reason; the final check counts as run 4 (C1b)
6. Advice questions answered in a fixed 4-part shape with no clinical specifics (C3)
