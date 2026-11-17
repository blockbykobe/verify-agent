# Experiment 8: steps for the session on the 2nd PC (~/verify-agent)

The rules from earlier stay in force:
- do not print the key;
- do not push;
- do not touch the main PC (qwen runs on the CPU of this PC);
- do not use sudo.

1. Unpack the bundle at the repository root: `tar xzf <path>/exp8_bundle.tgz`. Check that `git status` shows only new files.
2. Build the image: `docker build -t verify-agent-exp8 docker/exp8`. The network is needed only for the build.
3. Validate: `.venv/bin/python experiments/exp8_traps.py --validate`. All 10 traps must report OK. If anything fails, stop and report; do not change the regexes or the checks.
4. **Commit the plan BEFORE any model run.** Commit these files: docs/prereg_traps.md, docs/exp8_source.md, experiments/exp8_traps.py, audit/exp8.py, docker/exp8/Dockerfile, RUN_EXP8.md. Message: "Эксперимент 8: план до запусков (ловушки с ложными вводными)". Record the commit hash.
5. Haiku: `ANTHROPIC_API_KEY="$(cat ~/.anthropic_key)" .venv/bin/python experiments/exp8_traps.py --model haiku --cond P V --runs 5 --max-usd 1`. That is 100 episodes, an estimated $0.2–0.5.
6. qwen (CPU, Ollama on localhost of this PC, NOT the main PC): `.venv/bin/python experiments/exp8_traps.py --model qwen --cond P V --runs 5`. Run it in the background with a log in results/exp8/qwen.log. Estimate: 1.5–3 h.
7. Then run `.venv/bin/python audit/exp8.py`. It writes results/exp8/summary.md and the blind sheet blind_sheet.md (40 replies, the key is in blind_key.json).
8. Scan results/exp8 for secrets and PII with gitleaks. Then commit: "Эксперимент 8: результаты".
9. Report in the thread:
   - the plan hash and the results hash;
   - the summary.md table;
   - H8a, H8b and H8c;
   - the cost;
   - 2–3 of the most telling FINAL replies, quoted verbatim.

Do not change the plan after step 4. Write any deviation as an addendum to docs/prereg_traps.md with the date.
