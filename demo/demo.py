#!/usr/bin/env python3
"""Демо: «проверено моделью» ≠ «верно». Повторяет реальный ответ модели из results/C.jsonl
(задача 009-config-sed, условие C) и по-настоящему исполняет его в песочнице:
  1) скрипт модели  2) тест, который написала сама модель → PASS  3) скрытый check.sh → FAIL.
Запуск: .venv/bin/python demo/demo.py [--live]   (--live: спросить модель заново вместо повтора)"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sandbox import ROOT, Sandbox, load_tasks  # noqa: E402

B, G, R, Y, D, X = "\033[1m", "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def say(s="", pause=0.6):
    print(s, flush=True)
    time.sleep(pause)


def main():
    task = load_tasks(["009-config-sed"])[0]
    rec = next(r for r in map(json.loads, (ROOT / "results/C.jsonl").read_text().splitlines())
               if r["task"] == task.name and r["outcome"] == "verified" and r["hidden_rc"] != 0)
    step = rec["history"][-1]
    sol, test = step["solution"], step["test"]
    if "--live" in sys.argv:
        from experiment import run_C
        live = run_C(task)
        if live["outcome"] == "verified":
            sol, test = live["history"][-1]["solution"], live["history"][-1]["test"]
    say(f"{B}verify-agent demo — «verified by the model» is not «correct»{X}", 1)
    say(f"{D}model: qwen2.5-coder:7b · sandbox: docker, network none, cap_drop ALL{X}")
    say(f"{D}replaying a real answer from results/C.jsonl (run {rec['run']}){X}\n", 1)
    say(f"{B}Task:{X} {task.text}\n", 1.5)
    say(f"{B}Model's solution:{X}")
    for l in sol.strip().splitlines():
        say(f"  {Y}{l}{X}", 0.3)
    say(f"\n{B}Model's own test:{X}")
    for l in test.strip().splitlines():
        say(f"  {Y}{l}{X}", 0.3)
    say()
    with Sandbox(task.caps) as sb:
        sb.run_script("/work/setup.sh", task.file("setup.sh"))
        _, before = sb.exec(["cat", "/etc/app/app.conf"])
        say(f"{B}[sandbox]{X} config before:")
        for l in before.strip().splitlines():
            say(f"  {D}{l}{X}", 0.2)
        rc, _ = sb.run_script("/work/solution.sh", sol)
        say(f"{B}[sandbox]{X} solution exit code: {rc}", 0.8)
        trc, tout = sb.run_script("/work/test.sh", test)
        say(f"{B}[sandbox]{X} model's test: {G + 'PASS' if trc == 0 else R + 'FAIL'}{X}  {D}{tout.strip()[:80]}{X}", 1.5)
        say(f"  → the model would report: {G}«verified, done»{X}\n", 1.5)
    say(f"{B}Hidden check (never shown to the model), clean container:{X}", 1)
    with Sandbox(task.caps) as sb:
        sb.run_script("/work/setup.sh", task.file("setup.sh"))
        sb.run_script("/work/solution.sh", sol)
        crc, cout = sb.run_script("/check/check.sh", task.file("check.sh"))
    say(f"  hidden check: {G + 'PASS' if crc == 0 else R + 'FAIL'}{X}", 0.8)
    for l in cout.strip().splitlines():
        say(f"  {D}{l}{X}", 0.25)
    say(f"\n{B}Verified, not guessed:{X} the agent's own «PASS» was wrong; only an independent check caught it.", 2)


if __name__ == "__main__":
    main()
