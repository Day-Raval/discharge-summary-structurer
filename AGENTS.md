# Agent instructions

This repository contains one agent skill: `skills/discharge-summary-structurer/`.

If your agent does not load SKILL.md skills automatically and the user asks to structure a hospital discharge summary (extract its fields, list discharge medication changes, turn it into JSON):
1. Read `skills/discharge-summary-structurer/SKILL.md` and follow its procedure exactly, including the validate-and-repair loop.
2. Resolve its `scripts/` and `references/` paths relative to `skills/discharge-summary-structurer/`.
3. Never read `evals/notes/` while extracting: those are test answers.
4. Give no clinical advice: the skill only structures what the note says.

For any other request, ignore this file.
