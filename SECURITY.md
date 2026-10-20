# Security policy

## Reporting a vulnerability

Email **dayesh.raval@gmail.com** with the subject `discharge-summary-structurer security`, or open a private security advisory at https://github.com/Day-Raval/discharge-summary-structurer/security/advisories/new.

Please include what you found, how to reproduce it, and which agent you used. You will get a reply within 7 days, and confirmed issues are fixed in a new release listed in CHANGELOG.md.

**Never include a real patient note in a report.** Reproduce the issue with a synthetic note like those in `evals/notes/`.

## Scope

The plugin contains markdown instructions, a local install script and Python scripts that use only the standard library. `validate.py` reads the note and extraction you point it at plus the bundled schema; `score.py` reads the gold and extraction files you point it at. Both print to the terminal, make no network calls and write no files. The skill has no MCP servers.

This is a documentation aid, not a medical device, and gives no clinical advice.
