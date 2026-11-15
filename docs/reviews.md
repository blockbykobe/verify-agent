# Independent reviews and what was done about them (November 2026)

After publication the project was reviewed by eight AI reviewers. Four were run by the author in other chats
(Gemini; Claude Sonnet 5.5, Claude Haiku 5.5 and Claude Fable 5.2 in claude.ai), four were run as separate agents
inside the project session (Claude Opus 5.5, Sonnet 5.5, Fable 5.2, Haiku 5.5), each read-only, with a narrow brief.
One more reviewer (a third-party tool) returned a generic review without opening the repository.

**Rule:** no finding was accepted on the reviewer's word. Each was checked against the data or the code first;
the "Check" column says how. All Claude reviewers are the same model family as the agent that built the project,
so this is independence of context, not of model family. Gemini is the only reviewer from another vendor.

| # | Finding | Reviewer(s) | Check | Status |
|---|---|---|---|---|
| 1 | Per-attempt Fisher p (2·10⁻⁶) treats 10 runs of the same task as independent (pseudoreplication) | Gemini, Fable (chat), Sonnet (chat), Haiku (chat) | `audit/task_level.py`: per-task sign-flip test | **Fixed.** Task-level analysis is now primary |
| 2 | D's gain comes mostly from refusing whole hard tasks | Fable (chat), Sonnet (chat), Haiku (chat) | per-task table; per-task random-refusal placebo | **Confirmed.** Within tasks D ≈ random refusal (placebo 6.2 vs D 5 errors: about the same) |
| 3 | README said the oracle in E shows an expected-vs-actual diff; the code shows only FAIL + own stdout | Fable (chat) | `experiment.py` `FEEDBACK_EXT` | **Fixed** (README error) |
| 4 | Hidden check of task 004 did not test "system group/user, no home directory" | Sonnet (agent) | read `check.sh` vs `task.md`; re-ran all stored scripts | **Fixed** (`audit/rescore_checks_v2.py`): 17 qwen verdicts PASS→FAIL, all on 004; Haiku unchanged. Checks of 003 (owners) and 006 (mode as octal) also tightened; no verdict changed |
| 5 | Verifier accuracy unknown | Fable (chat) | `audit/verifier_accuracy.py`: hidden check on every C/D attempt | **Done.** D accepted 39/58 good, 5/47 bad; C accepted 25/26 good, 9/20 bad |
| 6 | Unequal attempts (A: 1, C/D/E: ≤3); qwen retried after FAIL in only 6/84 cases | Gemini, Opus (agent) | recount from `history` | **Accepted**, wording changed ("did not retry", not "cannot learn") |
| 7 | Haiku results rest on one task (nginx); 3 of 16 "fixes" changed only the self-test | Fable (chat), Opus (agent) | recount | **Confirmed**, wording changed |
| 8 | Haiku's self-tests "never wrong" ignores 3 false rejections | Opus (agent) | recount | **Fixed** |
| 9 | Percentile bootstrap over 10 tasks is too narrow | Opus (agent) | t-interval over tasks | **Fixed** (t-interval reported) |
| 10 | Confession: journal shifts the threshold to agree with any accusation, not "truthfulness"; 23% vs 0% uses different denominators; pressure split 3/20, 3/20, 8/20 | Sonnet (chat), Haiku (chat), Opus (agent) | recount | **Accepted**, rewritten as hit / false-alarm rates; experiment 2 marked preliminary |
| 11 | Confession classifier misses partial confessions | Haiku (chat) | `confession.classify` on example sentences | **Confirmed.** Human blind relabelling planned |
| 12 | Evidence flag in confession replies is lexical (27/60 is an upper bound; strict 19/60) | Sonnet (agent) | — | **Accepted** as limitation |
| 13 | Injection: isolation prompt effect n.s. (p ≈ 0.6); gate's 16/16 only on an unobfuscated payload; 2 of 3 injections never appeared | Sonnet (chat), Haiku (chat), Opus (agent) | recount | **Accepted**, wording changed; marked preliminary |
| 14 | Experiment 4: one obvious lure, 5 agents per cell, model not verified; 0/20 means upper bound ≈ 16% | Sonnet (chat), Haiku (chat) | Wilson interval | **Accepted**, marked preliminary |
| 15 | Runs from two harness versions (pre/post seeded hardened check) are pooled | Sonnet (agent) | `hidden_log` prefix | **Accepted** as limitation |
| 16 | E's "honest refusal" cell is A's behaviour (no check.sh on abstain tasks) | Sonnet (agent) | `experiment.py` | **Accepted**, footnoted |
| 17 | Experiment 6 (RAG pilot): Haiku answers lost by a JSON parser bug; retry does not retrieve new evidence; quote verifier both too lax and too strict; J not paired with D; D_src uses gold metadata | Fable (agent) | reproduced on stored rows | **Confirmed.** Experiment 6 stopped; reported as a pilot; v2 needs a redesign |
| 18 | README/README_ru mismatches (missing sections, wrong "mostly hedged", p written two ways, a broken path) | Haiku (agent) | diff | **Fixed** |
| 19 | Generic review asking for sections that already exist | third-party tool | — | **Rejected** (did not read the repository) |
| 20 | "20/27 vs 20/30" discrepancy | Haiku (chat) | two different experiments, labelled in the file | **Rejected** |
| 21 | Second pass on the revised README (Opus agent, ~170 numbers recomputed): per-task "within a task" range was 0.44–0.62, not 0.50–0.62; the task-level sign-flip test was presented as pre-registered; ground truth changed (v2 checks) after the plan was committed; reviewer count; "p = 0.062 instead of 2·10⁻⁶" mixed check versions; 4/84 vs 6/84; "no better than random" too strong | Opus (agent) | recomputed | **Fixed**; deviations from the plan are now stated in the README |
| 22 | Only two verifiers in Experiment 1c; they differ in vendor, size and serving | Haiku (chat), Opus (agent) | Experiment 1d, pre-registered: four more local verifiers | **Done.** No local model (7B–14B, three vendors) came close to Haiku; fits capability, but vendor and API-vs-local remain confounded. A 14B-over-7B gain (H3a) was formally met but within run-to-run noise and dependent on 27 regenerated outputs |
| 23 | Confession labels made by an AI only | Sonnet (chat), Haiku (chat), Opus (agent) | blind human relabelling of 60 replies by the owner | **Done.** κ = 0.44 (0.31 on the AI-relabelled half); 13/14 false confessions confirmed; 4 missed confessions among 30 unread rule denials |
| 24 | Third pass on 1d and the human labels (Opus agent, ~100 numbers): vendor claim too strong; H3a depends on regenerated outputs and is within noise; 29 not 27 garbage answers; H3b read too broadly; κ is not all against AI labels; 13–15/60 was a sample statement | Opus (agent) | recomputed | **Fixed** |
| 25 | DeepSeek (chat): headline claims stated as general laws; Haiku result from a single run; Haiku may only be conservative; no related-work section; multiple comparisons in secondary analyses | DeepSeek | recomputed; arXiv lookups | **Headlines narrowed** to "in this data"; **single-run concern tested** (pre-registered H5: second Haiku run BA 0.92, 82% valid — replicated); **"only conservative" rejected** (Haiku's tests accept more good solutions, 0.79 vs 0.48, and reject more bad ones); **Related work added** (17 papers, each checked on arXiv); multiple comparisons noted |

What changed in the headline: qwen without checking was confidently wrong 36/100 times (27/100 before the 004
fix); with the independent verifier 5/100. Counted per task the difference is suggestive, not conclusive
(exact sign-flip p = 0.062), and inside a task the weak verifier did not separate good from bad solutions better
than random refusal. Whether a *stronger* verifier does is tested in the pre-registered cross-verifier analysis
([`prereg_cross_verifier.md`](prereg_cross_verifier.md), results in [`../results/cross_verifier.md`](../results/cross_verifier.md)).
