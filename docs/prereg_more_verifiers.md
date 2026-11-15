# Pre-registration: Experiment 1d — more verifiers (written and committed before any test is generated)

Date: 2026-11-15. Follows Experiment 1c ([`prereg_cross_verifier.md`](prereg_cross_verifier.md),
[`../results/cross_verifier.md`](../results/cross_verifier.md)), where tests written by Claude Haiku separated good from
bad solutions far better than tests written by qwen2.5-coder:7b. Open objection: two verifiers differ in vendor, size,
serving stack and API, so "strength" is only one explanation.

## New verifiers (all local, Ollama 0.40.15 on the owner's second PC, RTX 5060 8 GB)

* `qwen2.5-coder:7b` regenerated on the GPU — control: same model as Experiment 1, different hardware;
* `llama3.1:8b` (Meta) and `gemma2:9b` (Google) — similar size, different vendors;
* `qwen2.5-coder:14b` — same family as the 7B, about twice the size.

## Procedure (unchanged from condition D of Experiment 1)

* Prompt: `prompts.SYSTEM_VERIFIER` + `task.md` only, temperature 0.7, up to 2 tries to get a bash block that passes
  the policy gate (exactly `experiment.write_verifier_test`). 10 tests per solvable task (001–010) per model.
* Each test is scored on the same 262 unique solutions as Experiment 1c: for each solution, 3 tests of the model drawn
  at random (seed 2026), run `setup.sh` → solution → test in a fresh sandbox. Ground truth: the corrected (v2) hidden check.
* Validity: every test against the reference `solution.sh` (must pass) and a no-op solution (must fail).

## Metrics and how they will be read

For each verifier model: balanced accuracy (BA) pooled over both solvers; BA inside each task on qwen's solutions
(tasks 003, 004, 006, 009); share of valid tests. The two existing verifiers (qwen 7B on CPU, Haiku) are reported
alongside for comparison.

* **H3a (size within a family):** qwen2.5-coder:14b tests have higher BA than qwen2.5-coder:7b tests. Read as supported
  only if the 14B is better on every task with both good and bad solutions in an exact sign-flip test (p < 0.05 needs
  at least 5 such tasks, all in the same direction).
* **H3b (hardware control):** the share of valid tests from qwen 7B on GPU is within ±10 points of the CPU run (9/100).
  If not, hardware/serving differences confound the comparison and will be reported as such.
* **Vendor:** if llama3.1:8b and gemma2:9b score like qwen 7B (BA and validity well below Haiku), the gap in 1c is
  more plausibly about capability than about vendor; if either scores near Haiku, "strength" is not the whole story.
  This is descriptive; no significance claim.
* All numbers will be reported whatever they show.

## Known limitations (stated in advance)

* "Strength" has no independent measure here; parameter count and family are rough proxies.
* Same 10 public tasks; the solutions are retries, not independent samples; models may have seen similar tasks in training.
* One generation run per model (10 tests per task).

## Addendum (2026-11-15, written before the 32B run): a strong non-Anthropic verifier

Motivation: Experiment 1d could not separate vendor from capability, because Claude Haiku was the only strong verifier.
Added verifier: `qwen2.5-coder:32b` (local, Ollama, partly offloaded to CPU on the 8 GB GPU machine). Because it is slow,
**5 tests per task** instead of 10 (same prompt, temperature 0.7, same 2-try rule); scoring exactly as above.
Garbage outputs (non-text token salad, as seen once with the 14B) will be set aside and regenerated, and reported.

* **H4 (vendor vs capability):** if the 32B's balanced accuracy is within 0.10 of Claude Haiku's (0.90) and its share
  of valid tests is above 50%, a strong non-Anthropic verifier behaves like Haiku → evidence for "capability".
  If its balanced accuracy stays within the range of the small local models (0.52–0.67) → "capability" (as measured by
  size) is not enough, and the gap is not explained by model size alone. Anything in between is reported as inconclusive.
