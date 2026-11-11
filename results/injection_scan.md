# Harness-side injection detector — offline evaluation

`injection_scan.py` flags text addressed to AI agents ("AI reviewers", "агенту обслуживания"), override/concealment phrases ("ignore the task", "do not mention") and requests to claim success or run `curl | sh`.
It runs on file contents and command output *before* the model sees them, and shows hits to the user directly.

Corpus: every injected and clean text already used in this project. No new examples were written for this evaluation, except that the regexes were written by the same author who wrote the injections, so this is optimistic.

| | count |
|---|---|
| injected texts detected | **10/10** |
| clean task / log / code files flagged (false alarms) | **0/67** |
| project docs that *discuss* injections flagged | 4/4 (expected: they quote the attacks) |

Flagged clean texts:
- README.md (project docs that DISCUSS injections)
- docs/audit.md (project docs that DISCUSS injections)
- docs/application_notes.md (project docs that DISCUSS injections)
- results/claude_canary.md (project docs that DISCUSS injections)

Limitations: keyword heuristics are easy to evade (paraphrase, other languages, encoding). This only makes the obvious attempts visible; the sandbox and policy gate remain the boundary.

## Independent hold-out (the honest number)

A separate fresh‑context agent, which never saw the detector, wrote `tests/injection_holdout_independent.yaml`: 15 injected excerpts and 15 benign ones. Its injections used polite and third‑person wording, German/Spanish/Russian, base64, dotted letters ("i.g.n.o.r.e") and fake "pre‑approved / elevated trust" framing, placed in logs, YAML/JSON, commit messages, systemd output and Dockerfiles. The set was committed before the single evaluation; the rules were not changed afterwards.

| | own corpus | independent hold‑out |
|---|---|---|
| injections detected | 10/10 | **3/15** |
| false alarms | 0/67 | 0/15 |

Evaluating the detector on texts written by the same author who wrote its rules was wildly optimistic: 100% fell to 20%. This is the same lesson as the self‑verification result in Experiment 1. Keyword scanning only surfaces the obvious attempts.
