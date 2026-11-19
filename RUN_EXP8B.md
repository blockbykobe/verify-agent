# Experiment 8b: steps for the 2nd PC session (~/verify-agent)

The bundle contains only NEW files, so it does not overwrite anything:
- docs/prereg_traps_8b.md
- experiments/exp8b_traps.py
- audit/exp8b.py
- RUN_EXP8B.md

The rules stay the same:
- do not print the key;
- do not push;
- do not use sudo;
- touch the main PC only through the Ollama API.

1. Unpack the bundle at the repository root (`tar xzf …/exp8b_bundle.tgz`). Check that `git status` shows only these 4 new files. If a file with the same name already exists, stop and report.
2. Run `.venv/bin/python experiments/exp8b_traps.py --validate`. It must print `all OK` and `mechanics OK`.
3. **Commit before any run.** Commit the 4 files with the message "Эксперимент 8b: план до запусков — исправленная программа, 5 агентов".
4. Run these on this PC; they can run in parallel:
   - Haiku: `ANTHROPIC_API_KEY="$(cat ~/.anthropic_key)" .venv/bin/python experiments/exp8b_traps.py --model haiku --cond P V --runs 5 --max-usd 1`
   - qwen 7B on the CPU, in the background with a log at results/exp8b/qwen.log: `.venv/bin/python experiments/exp8b_traps.py --model qwen --cond P V --runs 5`
5. Main PC. Do this only after the author writes "основной ПК свободен" and Ollama at 192.168.50.22:11434 answers.
   - Run the models one at a time, in this order: qwen14b, llama8b, gemma9b.
   - Use `--url http://192.168.50.22:11434`.
   - Run in batches with cooling breaks.
   - Unload each model when it is done (`keep_alive: 0`).
   - If the GPU overheats or the author asks you to stop, stop. Report any missing episodes in an addendum.
6. Run `.venv/bin/python audit/exp8b.py`, then gitleaks. Commit with the message "Эксперимент 8b: результаты".
7. Report:
   - the commit hashes;
   - the table from summary.md;
   - H8a′, H8b′, H8d and H8e;
   - the cost;
   - what happened with the main PC (time, and temperature if known).
