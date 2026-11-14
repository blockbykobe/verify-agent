# Pre-registration: cross-verifier analysis (written and committed before running)

Date: 2026-11-15. Motivated by the independent reviews (see README, "Independent reviews"): the gain of the
independent verifier (condition D) came largely from refusing whole hard tasks, and its tests rejected many good
solutions. Open question: **is it the verifier's independence or its strength that lets it catch errors?**

## Data (no new model calls)

* Solutions: every bash solution already recorded in Experiment 1 (qwen2.5-coder:7b; `results/{A,C,D,E}.jsonl`)
  and Experiment 1b (Claude Haiku 5.5; `results/claude/claude-haiku-5-5-low/{A,C,D,E}.jsonl`): final scripts in A,
  and every attempt in C, D, E. Deduplicated by (task, exact script text). Solvable tasks 001–010 only.
* Verifier tests: the independent verifier tests already written in condition D — qwen: 10 per task
  (`results/D.jsonl`), Haiku: 5 per task (`results/claude/claude-haiku-5-5-low/D.jsonl`). Both were written from
  `task.md` only, before any solution existed.
* Ground truth: the hardened hidden check (`sandbox.evaluate`) re-run on every unique solution.

## Procedure

1. For each unique solution, draw 3 qwen tests and 3 Haiku tests for the same task (random seed 2026, without
   replacement). Run `setup.sh` → solution → test in a fresh sandbox, exactly as `experiment.run_external` does,
   and record PASS (exit 0) / FAIL.
2. Test validity: run every verifier test against the task's reference `solution.sh` and against a no-op solution
   (`true`). A valid test passes the reference and fails the no-op.

## Metrics (decided now)

For each verifier family V ∈ {qwen, Haiku} and solver S ∈ {qwen, Haiku}, over (solution, test) pairs:
* sensitivity = P(test PASS | hidden PASS); specificity = P(test FAIL | hidden FAIL);
  **balanced accuracy (BA)** = mean of the two; precision = P(hidden PASS | test PASS).

**Primary comparison:** BA of Haiku-written tests vs qwen-written tests, pooled over both solvers, with a 95%
bootstrap interval that resamples **tasks** (the unit is the task, not the attempt), 10 000 resamples.

Secondary:
* the same per solver (2 × 2 table: solver × verifier);
* **within-task discrimination:** BA computed only on tasks that have both good and bad solutions for that solver;
  a verifier that only detects hard tasks would score ≈ 0.5 here;
* placebo: a verifier that says PASS at random with the same pass rate has BA = 0.5 by construction;
* test validity: share of tests that pass the reference solution and share that fail the no-op.

## Hypotheses and how they will be read

* H1: Haiku-written tests have higher BA than qwen-written tests. Supported only if the task-bootstrap 95% interval
  for the difference excludes 0.
* H2 (from the Fable 5.2 review): qwen-written tests are mostly a difficulty detector — their within-task BA is close
  to 0.5 — while Haiku-written tests discriminate within tasks (BA clearly above 0.5).
* All numbers will be reported whatever they show, including null results.

## Known limitations (stated in advance)

* Same 10 public tasks; solutions are not independent samples (retries of the same model on the same task).
* Haiku tests come from one earlier run (5 per task), qwen tests from 10 runs.
* Self-tests (condition C) are excluded: each self-test was written for its own solution only.
* This is a post-hoc analysis of existing data, motivated by reviews; the plan above is fixed before running it.
