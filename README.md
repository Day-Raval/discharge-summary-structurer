# Discharge Summary Structurer

An agent skill that turns a hospital discharge summary into structured JSON, **where every fact carries a verbatim quote from the note and a script checks each quote before anything is returned**.

An LLM asked for JSON usually returns JSON, but it fails quietly: a dose that sounds right but isn't in the note, a stopped medication listed as continued, a ruled-out diagnosis listed as present. This skill makes those failures visible. The model extracts, a bundled Python script (standard library only) checks the result against a schema and against the note itself, and the model may fix only what the script flags, up to 3 tries. Anything still failing is set to null and listed for human review.

## What you get

- Admission and discharge dates, principal and secondary diagnoses, procedures
- Allergies, with `nkda` and `not_documented` kept apart
- Discharge medications with dose, route, frequency and status: `new`, `changed`, `continued` or `stopped`
- Follow-up appointments, results still pending at discharge, and discharge disposition
- A verbatim `evidence` quote on every fact, checked against the note
- A `needs_review` list naming any field the model couldn't ground after 3 tries
- A readable summary and medication table, built only from the validated JSON

Example, from the synthetic note in `evals/notes/note-01.txt`:

| Medication | Dose | Route | Frequency | Change |
|---|---|---|---|---|
| Furosemide | 40 mg | PO | daily | changed |
| Sacubitril-valsartan | 24-26 mg | PO | twice daily | new |
| Carvedilol | 6.25 mg | PO | twice daily | continued |
| Amlodipine | - | - | - | stopped |

```json
{"name": "Furosemide", "dose": "40 mg", "route": "PO", "frequency": "daily", "status": "changed",
 "evidence": "Furosemide 40 mg PO daily (increased from home dose of 20 mg daily)"}
```

## How it works

```
note.txt ──► model extracts JSON ──► validate.py ──► valid? ──yes──► summary + JSON
                    ▲                                  │ no
                    └── fix only the flagged paths ────┤ (max 3 validator runs)
                                                       └── still failing → null + needs_review
```

`validate.py` runs four checks and prints each failure as a path plus a message the model can act on:

| Check | Catches | Example message |
|---|---|---|
| Schema | Missing fields, wrong types, bad enums, non-ISO dates, extra fields | `admission_date.value: must match ^\d{4}-\d{2}-\d{2}$ (dates are YYYY-MM-DD)` |
| Grounding | A quote that isn't in the note | `secondary_diagnoses[2].evidence: is not a verbatim quote from the note; copy the exact words` |
| Support | A value its own quote doesn't back, or a dose number not in the quote | `discharge_medications[0].dose: dose number 500 is not in its evidence quote` |
| Consistency | Discharge before admission, impossible dates, allergy status vs items | `allergies.status: is nkda but allergies are listed` |

Quotes are matched ignoring case and line breaks. The hard cases (stopped versus historical medications, ruled-out diagnoses, NKDA versus no allergy line) are decided by `references/extraction-rules.md`.

## Requirements

- Python 3.9 or newer (`python3 --version`). No packages to install.
- The discharge summary as plain text. For a PDF or scan, copy the text out first.

## Install

Works in Claude Code, Claude.ai, OpenAI Codex, Gemini CLI, Cursor and GitHub Copilot. The skill uses the open SKILL.md format, so any compatible agent can load it.

**Any agent (manual install)**:

1. On the [repository page](https://github.com/Day-Raval/discharge-summary-structurer), choose **Code > Download ZIP** and extract it.
2. Copy the entire `skills/discharge-summary-structurer/` folder into your agent's skills folder below. Keep its name and contents together.
3. Start a new chat in the agent.

On Windows, `~` means your Windows user folder (for example, `C:\Users\<you>`).

| Agent | Skills folder |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Cursor | `~/.cursor/skills/` |
| GitHub Copilot | `~/.copilot/skills/` |

**Claude Code plugin** (gets updates with `claude plugin update`):
```
claude plugin marketplace add Day-Raval/discharge-summary-structurer
claude plugin install discharge-summary-structurer@discharge-summary-structurer
```

**Claude.ai**: zip the `skills/discharge-summary-structurer/` folder and upload it under Settings > Capabilities > Skills. Code execution must be on, because the skill runs a Python script.

**Agents without skill support**: open this repo in the agent. `AGENTS.md` tells it to follow `skills/discharge-summary-structurer/SKILL.md`.

## Use

```
Structure this discharge summary:
<paste the note>
```
Or attach the note as a `.txt` file and ask "What medications changed at discharge?" or "Pull the meds and follow-ups out of this into JSON."

To check an extraction without an agent:
```
python3 skills/discharge-summary-structurer/scripts/validate.py note.txt extraction.json
```

## Try it with sample data

`evals/notes/` holds three synthetic discharge summaries, each with a hand-made gold extraction. They are written in three styles (sectioned, semi-structured and narrative prose) and plant 16 traps, listed in `evals/traps.md`: a negated diagnosis, a stopped home medication, a changed dose, an inpatient-only IV drug, a historical medication, NKDA versus no allergy line, a follow-up with no timeframe and more.

Paste a note into your agent, then score the result against its gold file:
```
python3 skills/discharge-summary-structurer/scripts/score.py evals/notes/note-01.gold.json extraction.json
```
`score.py` reports precision, recall and F1 per field and overall, and lists every mismatch, e.g. `discharge_medications.status (Furosemide): expected 'changed', got 'continued'`.

The test notes live outside the skill folder on purpose: an agent running the skill never has the answer key in reach.

## Results

Tested in Claude.ai (v1.0.0), each run in a fresh chat, with the skill uploaded without any test notes or gold files:

| Test | Result |
|---|---|
| Accuracy on 3 synthetic notes (sectioned, semi-structured, prose) | **97/97 facts, F1 1.000**, all 16 planted traps handled, each valid on the first validator run |
| Repair loop and fallback | Planted errors caught and fixed in one repair; an unfixable item removed and logged in `needs_review` after 3 runs |
| Advice question ("should she take more furosemide?") | Answers from the note, says it can't advise, names the care team from the note |
| Sparse note (date and disposition only) | Everything else left null; nothing invented |
| Triggers | 6/6: loads for 3 discharge-summary requests, stays out of 3 general medical questions |

Testing found and fixed 6 issues before release, 3 of them first flagged by the skill's own Notes (a dose-matching gap in the validator, an unreadable `needs_review` entry, a gold file that had missed a procedure). Full record: `evals/trigger-tests.md`.

## Privacy and safety

- **Synthetic data only in this repo.** Every note here is fictional. `.gitignore` excludes `*.txt` outside `evals/`, and CI fails if a note appears anywhere else. Never commit a real patient note.
- **Local by design.** The scripts make no network calls and write no files except where you tell them. The skill has no MCP servers and tells the agent not to send the note to web tools.
- **Real notes are protected health information.** Process them only in an environment you are authorized to use. The agent you run sees the note the same way it sees anything you paste.
- **Not a clinical tool.** The skill structures what the note says. It does not diagnose, recommend treatment, check interactions or judge doses, and every output ends with a disclaimer saying so.

## Limits

- One English discharge summary per run, as plain text. No PDFs, scans or multi-note records.
- No coding to ICD-10, SNOMED or RxNorm; medication names stay as written.
- `validate.py` proves a fact is quoted, not that it was read correctly. A ruled-out diagnosis quoted word for word passes validation. That's what the gold files and `score.py` are for.
- Dates written month-first (`03/04/2026`) are read as US dates.
- While the skill is working on a note, it won't interpret results or give reference ranges about that patient, even well-known ones; it points to the care team instead. Ask general medical questions in a separate chat.

## Troubleshooting

| Problem | Fix |
|---|---|
| `is not a verbatim quote from the note` keeps repeating | The note was edited after saving (smart quotes, trimmed spaces). Paste it again exactly as it is, or attach the original `.txt` |
| Fields land in `needs_review` | The model couldn't ground them in 3 tries. Check those fields against the note by hand |
| `python3: command not found` | Install Python 3.9+ (on Windows, use `py` in place of `python3`) |
| Claude.ai can't run the script | Turn on code execution under Settings > Capabilities |
| Skill doesn't load | Start a new chat, mention "discharge summary" with the note, or call it directly with `/discharge-summary-structurer` |
| Other issues | Open an issue: https://github.com/Day-Raval/discharge-summary-structurer/issues |

## Testing

```
python3 skills/discharge-summary-structurer/scripts/test_validate.py
python3 evals/test_score.py
```
The first checks that the validator catches every error class; the second checks the scorer's counting, including a trap-falling extraction worth exactly 5 false positives and 6 false negatives. CI runs both on Python 3.9 and 3.12. Agent-level trigger and behavior tests are in `evals/trigger-tests.md`.

## Repository layout

```
skills/discharge-summary-structurer/   the skill (this is what gets installed or zipped)
├── SKILL.md
├── references/schema.json, extraction-rules.md
└── scripts/validate.py, score.py, test_validate.py
evals/                                 test data and tests (never installed)
├── notes/note-01..03.txt, note-01..03.gold.json
├── traps.md, test_score.py, trigger-tests.md
```

## Security

See [SECURITY.md](SECURITY.md) to report a vulnerability.

## License

MIT
