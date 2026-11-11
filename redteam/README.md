# Independent red-team scripts

Written by a separate agent with a fresh context (see `docs/audit.md` → "Independent red team").
Each file is a candidate *solution* script, run only inside the sandbox through `sandbox.evaluate()`.
attack1/5/6 (hard-coded answers) PASS the hidden check → finding F21; attack3 (binary tamper) and attack4
(hidden-check extraction) are blocked; attack2 turned out to be a valid solution, not a bypass.
