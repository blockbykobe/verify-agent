# Pre-registration: human-written tasks (Experiment 7) — written and committed before any task exists

Date: 2026-11-15. Motivated by the Opus 5.5 review (see `docs/reviews.md`, row 26): the hidden checks and reference
solutions of tasks 001–010 were written with Claude's help, so Claude Haiku may share their assumptions
("kinship"). That could inflate Haiku's advantage as a verifier in Experiments 1c–1d. This plan is fixed **before the
project's author has written a single new task**, so neither the tasks nor the analysis can be tuned to the result.

## Tasks

* The project's author (a working system administrator) writes 5–10 tasks from his own practice, each as:
  (a) what to do, (b) the trap — where people usually go wrong, (c) how he would check that it was done right
  (concrete commands). He writes them without looking at tasks 001–015.
* Claude Code converts them into the usual format (`task.md`, `setup.sh`, `check.sh`, `solution.sh`, `meta.yaml`),
  numbered 101+. **The logic of `check.sh` must come from (c)**; Claude only wraps the author's commands into a
  script and may not add or remove conditions. Any change is listed in `meta.yaml` (`note:`) and approved by the author.
* The author reviews every task before any model sees it and confirms in writing that `check.sh` checks what he meant.
* Validity gate (as for 001–010): `check.sh` must pass the reference `solution.sh` and fail a no-op (`true`).
  A task that fails the gate is fixed or dropped **before** any model run; dropped tasks are listed.
* Known residual kinship: `setup.sh` and `solution.sh` may be written by Claude Code; the ground truth (`check.sh`) is not.

## Runs (no main-PC GPU needed)

* Solver qwen2.5-coder:7b (CPU, temperature 0.7, same prompts as Experiment 1): conditions A, C, D, 5 runs per task.
* Solver Claude Haiku 5.5 (effort low, same prompts as Experiment 1b): conditions A, C, D, 5 runs per task; budget cap $2.
* Verifier tests written from `task.md` only, before any solution exists: qwen 10 per task, Haiku 5 per task
  (these are the condition-D tests).
* Ground truth: the author's `check.sh`, run on every unique solution in a fresh sandbox.

## Analysis (same code as Experiment 1c, `audit/cross_verifier.py`, applied to tasks 101+)

Solutions deduplicated by (task, exact script); 3 tests of each verifier per solution (seed 2026); test validity as above.

* **H6 (primary):** Haiku-written tests have higher balanced accuracy (BA) than qwen-written tests on the
  human-written tasks. Read as supported only if **both**: (i) Haiku's tests are better on a majority of the tasks that
  have both good and bad solutions, with exact sign-flip p < 0.05 over those tasks; and (ii) the two-level bootstrap
  (tasks, then tests and solutions within a task) 95% interval for the difference excludes 0. With fewer than 5 such
  tasks, (i) cannot reach p < 0.05; then H6 is reported as **not testable**, with descriptive numbers only.
* **H7:** the share of valid tests (pass the reference, fail the no-op) is higher for Haiku than for qwen, counted per
  task (Haiku higher on a majority of tasks).
* **Reading for kinship:** if H6 holds on human-written tasks, kinship is not the main explanation of Experiment 1c.
  If Haiku's advantage shrinks a lot (task-averaged BA difference below half of the 1c value, +0.30 → below +0.15),
  kinship is reported as a likely part of the 1c effect.
* Secondary, descriptive: share of self-"verified" wrong solutions in condition C (Experiment 1 headline: 26% for the 7B);
  solved / confidently wrong in A vs D, per task.
* All numbers will be reported whatever they show, including null results and dropped tasks.

## Known limitations (stated in advance)

* Few tasks (5–10) from one author; one domain (Linux administration); prompts in Russian.
* Solutions are retries of the same models, not independent samples.
* The author knows the project's hypotheses; he writes tasks before seeing any result on them.
* Claude Code still writes `setup.sh`/`solution.sh` and the wrapping of `check.sh`.

## Addendum (2026-11-16, still before any task is written)

A power check (`audit/extra_analyses.py`, section 3) shows that the task-level sign-flip test in H6 (i) can reach
p < 0.05 only with at least 5 tasks that have both good and bad solutions, and only if Haiku's tests are better on all
of them; in Experiment 1c only 6 of 10 tasks were mixed. The target is therefore **10 tasks** (minimum 8), not 5–10.
Nothing else in the plan changes.

## Correction (2026-11-16, still before any task is written)

The addendum above and rule (i) of H6 say "at least 5" mixed tasks. The sign-flip test is two-sided: with 5 tasks its
smallest possible p is 2/32 = 0.0625, so p < 0.05 needs **at least 6** mixed tasks. H6 is therefore reported as
**not testable** with fewer than 6 such tasks (not 5). The 10-task target is unchanged.

## Addendum 2 (2026-11-16, before any model has seen the new tasks): where the tasks came from

* **Source changed.** The author did not write the tasks by hand: at his request **Gemini (Google)** generated
  10 tasks with setup and checks (`tasks_gemini/sysadmin_bench_v1.py`); Claude Code reviewed them in the sandbox and
  listed problems; the author sent that list to Gemini, which produced `tasks_gemini/sysadmin_bench_v2.py`. Both files
  are committed unchanged. The author selected and approved the tasks. So the experiment now tests "tasks and checks
  written by a non-Anthropic model", not "tasks from a sysadmin's practice". This still addresses the kinship concern
  (Claude wrote neither the tasks nor the checks); it no longer tests human-written tasks.
* **How they run.** `tasks_gemini/build_tasks.py` makes `tasks/101-…110-…`: `setup.sh` and `check.sh` run Gemini's
  code unchanged (`setup N` / `verify N`) from a temporary copy that is deleted; `setup.sh` also deletes itself.
  Reference solutions `tasks_gemini/solutions/*.sh` are written by Claude Code (allowed by the plan).
* **Harness changes, only for these tasks (meta.yaml):** image `verify-agent-exp7` = base image + `python3` + `sudo`
  (`docker/exp7/Dockerfile`); capabilities CHOWN, DAC_OVERRIDE, FOWNER, FSETID, SETUID, SETGID (from the existing
  allow-list); task 106 keeps its background writer alive when the harness kills the solution's processes; task 108 may
  create `/usr/local/bin/backup-site.sh` (the task asks for it) without being flagged as tampering. The sandbox's
  `no-new-privileges`, no network and the other limits are unchanged.
* **One check change, pending the author's approval:** in task 105 Gemini's check runs `sudo` as user deploy, which
  can never work under `no-new-privileges`. Proposed replacement (`tasks_gemini/overrides/5.py`, diff in that file):
  root asks sudo the same questions (`sudo -l -U deploy`, `sudo -l -U deploy /usr/sbin/nginx -V` / `-c …`). If the
  author does not approve it, task 105 is dropped.
* **Validity gate:** all 10 reference solutions pass and a no-op fails (with the task-105 change).
* Analysis, hypotheses H6/H7 and the minimum of 6 mixed tasks are unchanged.
