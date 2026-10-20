# Changelog

## 1.0.1 (2026-10-20)
- Directory submission fixes: removed the blanket `* text=auto` rule from `.gitattributes`, added the plugin icon, privacy policy and documentation links.
- README privacy section now describes working files, where they are processed, and platform retention.

## 1.0.0 (2026-10-20)
- First public release.
- `references/schema.json` (JSON Schema draft 2020-12): 11 fields, every fact with a verbatim `evidence` quote.
- `scripts/validate.py` (Python 3.9+, standard library only): schema, grounding, support and consistency checks, with error messages written for the model to act on. Dose numbers are matched as whole numbers.
- SKILL.md: extract, validate, fix only the flagged paths, at most 3 runs, then null the field and log it in `needs_review` with the removed value, its evidence and the reason. Advice questions get a fixed 4-part reply with no clinical specifics.
- `references/extraction-rules.md`: stopped versus historical medications, ruled-out diagnoses, NKDA versus no allergy line, follow-ups, disposition.
- `scripts/score.py`: field-level precision, recall and F1 against gold, best-match pairing, readable mismatch list.
- `evals/`: 3 synthetic notes in 3 styles with gold extractions and 16 planted traps, kept outside the skill folder.
- Tested in Claude.ai: 97/97 facts (F1 1.000), behavior tests and 6/6 trigger tests, recorded in `evals/trigger-tests.md`.
- Works in Claude Code, Claude.ai, Codex, Gemini CLI, Cursor and GitHub Copilot via `install.sh`, plus an `AGENTS.md` fallback.
