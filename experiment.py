#!/usr/bin/env python3
"""Эксперимент: A — один ответ без запуска; C — самопроверка исполнением (свой тест, до 3 попыток);
D — независимый верификатор (отдельный вызов модели пишет тест по task.md ДО решения, решатель видит только
PASS/FAIL и свой stdout); E — оракул: верификатор = скрытый check.sh (нереалистичная верхняя граница).

Методология: в условии C модель проверяет себя ТОЛЬКО собственным тестом в песочнице.
Скрытый check.sh в цикл попыток не попадает и используется только для итоговой оценки
финального скрипта в чистом контейнере (для обоих условий одинаково).

Запуск: python experiment.py --cond A C --runs 3 [--tasks 001-... ...]
Результаты дописываются в results/<cond>.jsonl; уже выполненные (cond, run, task) пропускаются.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from prompts import FEEDBACK_C, FEEDBACK_EXT, SYSTEM_A, SYSTEM_C, SYSTEM_VERIFIER
from sandbox import ROOT, Sandbox, Task, chat, code_blocks, evaluate, load_tasks, parse_answer, policy_gate

RESULTS = ROOT / "results"
MAX_ATTEMPTS = 3
TEMPERATURE = 0.7


def cut(s: str, n: int = 1500) -> str:
    return s if len(s) <= n else s[:300] + "\n…[обрезано]…\n" + s[-(n - 300):]


def run_A(task: Task) -> dict:
    answer = chat([{"role": "system", "content": SYSTEM_A}, {"role": "user", "content": task.text}],
                  temperature=TEMPERATURE)
    kind, payload = parse_answer(answer)
    rec = {"raw": answer, "kind": kind, "final_script": payload if kind == "script" else None,
           "attempts": 1, "gate": []}
    if kind == "script":
        rec["gate"] = policy_gate(payload)
        rec["outcome"] = "gate" if rec["gate"] else "answered"
    else:
        rec["outcome"] = kind  # abstain | ask_human | none
    return rec


def split_solution_test(answer: str) -> tuple[str | None, str | None]:
    blocks = [b for lang, b in code_blocks(answer) if lang in ("bash", "sh", "shell", "")]
    if not blocks:
        return None, None
    return blocks[0], (blocks[1] if len(blocks) > 1 else None)


def run_C(task: Task) -> dict:
    msgs = [{"role": "system", "content": SYSTEM_C}, {"role": "user", "content": task.text}]
    history = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        answer = chat(msgs, temperature=TEMPERATURE)
        msgs.append({"role": "assistant", "content": answer})
        kind, payload = parse_answer(answer)
        step = {"attempt": attempt, "raw": answer, "kind": kind}
        history.append(step)
        if kind in ("abstain", "ask_human"):
            return {"kind": kind, "outcome": kind, "attempts": attempt, "history": history,
                    "final_script": None, "gate": []}
        sol, test = split_solution_test(answer)
        if sol is None:
            fb = "Ответ не по формату: нужен блок ```bash``` с решением и второй блок ```bash``` с тестом, либо ABSTAIN:/ASK_HUMAN:."
        elif test is None:
            fb = "Нет второго блока с тестом. Пришли решение и отдельный тест (два блока ```bash```)."
        else:
            gate = policy_gate(sol) + policy_gate(test)
            if gate:
                step["gate"] = gate
                return {"kind": "script", "outcome": "gate", "attempts": attempt, "history": history,
                        "final_script": sol, "gate": gate}
            with Sandbox(task.caps) as sb:
                if task.file("setup.sh"):
                    sb.run_script("/work/setup.sh", task.file("setup.sh"))
                src, sout = sb.run_script("/work/solution.sh", sol)
                trc, tout = sb.run_script("/work/test.sh", test)
            step.update(solution=sol, test=test, sol_rc=src, test_rc=trc, sol_out=cut(sout), test_out=cut(tout))
            if trc == 0:
                return {"kind": "script", "outcome": "verified", "attempts": attempt, "history": history,
                        "final_script": sol, "gate": []}
            fb = FEEDBACK_C.format(src=src, sout=cut(sout) or "(пусто)", trc=trc, tout=cut(tout) or "(пусто)",
                                   verdict="Твой тест НЕ прошёл. Исправь решение (или тест, если он ошибочен) "
                                           "и пришли оба блока заново, либо ответь ABSTAIN:/ASK_HUMAN:.")
        step["feedback"] = fb
        msgs.append({"role": "user", "content": fb})
    return {"kind": "script", "outcome": "unverified", "attempts": MAX_ATTEMPTS, "history": history,
            "final_script": None, "gate": []}


def write_verifier_test(task: Task) -> tuple[str | None, str]:
    """Условие D: отдельный вызов модели в новом контексте, видит только task.md."""
    raw = ""
    for _ in range(2):
        raw = chat([{"role": "system", "content": SYSTEM_VERIFIER}, {"role": "user", "content": task.text}],
                   temperature=TEMPERATURE)
        blocks = [b for lang, b in code_blocks(raw) if lang in ("bash", "sh", "shell", "")]
        if blocks and not policy_gate(blocks[0]):
            return blocks[0], raw
    return None, raw


def run_external(task: Task, oracle: bool) -> dict:
    """D (oracle=False): тест пишет независимый верификатор. E (oracle=True): тест = скрытый check.sh.
    Решатель видит только PASS/FAIL и вывод СВОЕГО скрипта, сам тест не видит."""
    if oracle:
        test, vraw = task.file("check.sh"), None
    else:
        test, vraw = write_verifier_test(task)
    msgs = [{"role": "system", "content": SYSTEM_A}, {"role": "user", "content": task.text}]
    history = []
    base = {"verifier_test": test if not oracle else "(hidden check.sh)", "verifier_raw": vraw, "gate": []}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        answer = chat(msgs, temperature=TEMPERATURE)
        msgs.append({"role": "assistant", "content": answer})
        kind, payload = parse_answer(answer)
        step = {"attempt": attempt, "raw": answer, "kind": kind}
        history.append(step)
        if kind in ("abstain", "ask_human", "none"):
            if kind == "none":
                msgs.append({"role": "user", "content": "Ответ не по формату: нужен блок ```bash``` или ABSTAIN:/ASK_HUMAN:."})
                continue
            return {**base, "kind": kind, "outcome": kind, "attempts": attempt, "history": history, "final_script": None}
        gate = policy_gate(payload)
        if gate:
            return {**base, "kind": "script", "outcome": "gate", "attempts": attempt, "history": history,
                    "final_script": payload, "gate": gate}
        if test is None:  # верификатора нет (D: не написал тест; E: у задачи нет check.sh)
            return {**base, "kind": "script", "outcome": "answered", "attempts": attempt, "history": history,
                    "final_script": payload, "no_verifier": True}
        with Sandbox(task.caps) as sb:
            if task.file("setup.sh"):
                sb.run_script("/work/setup.sh", task.file("setup.sh"))
            src, sout = sb.run_script("/work/solution.sh", payload)
            trc, tout = sb.run_script("/verify/test.sh", test)
        step.update(solution=payload, sol_rc=src, test_rc=trc, sol_out=cut(sout), test_out=cut(tout))
        if trc == 0:
            return {**base, "kind": "script", "outcome": "verified", "attempts": attempt, "history": history,
                    "final_script": payload}
        msgs.append({"role": "user", "content": FEEDBACK_EXT.format(
            verdict="FAIL", src=src, sout=cut(sout) or "(пусто)",
            tail="Исправь скрипт и пришли его заново целиком, либо ответь ABSTAIN:/ASK_HUMAN:.")})
    return {**base, "kind": "script", "outcome": "unverified", "attempts": MAX_ATTEMPTS, "history": history,
            "final_script": None}


RUNNERS = {"A": lambda t: run_A(t), "C": lambda t: run_C(t),
           "D": lambda t: run_external(t, oracle=False), "E": lambda t: run_external(t, oracle=True)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cond", nargs="+", default=["A", "C"])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tasks", nargs="*")
    args = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    tasks = load_tasks(args.tasks)
    for cond in args.cond:
        out = RESULTS / f"{cond}.jsonl"
        done = set()
        if out.exists():
            for line in out.read_text().splitlines():
                r = json.loads(line)
                done.add((r["run"], r["task"]))
        for run in range(1, args.runs + 1):
            for task in tasks:
                if (run, task.name) in done:
                    continue
                t0 = time.monotonic()
                try:
                    rec = RUNNERS[cond](task)
                except Exception as e:  # честно фиксируем падение, а не пропускаем
                    rec = {"kind": "error", "outcome": "error", "error": repr(e), "final_script": None,
                           "attempts": 0, "gate": []}
                rec["hidden_rc"], rec["hidden_log"] = None, None
                if task.expected == "solve" and rec["outcome"] in ("answered", "verified"):
                    rec["hidden_rc"], rec["hidden_log"] = evaluate(task, rec["final_script"])
                rec.update(cond=cond, run=run, task=task.name, expected=task.expected,
                           category=task.meta.get("category"), seconds=round(time.monotonic() - t0, 1),
                           time=datetime.now(timezone.utc).isoformat(), temperature=TEMPERATURE)
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"[{cond} run{run}] {task.name}: {rec['outcome']} attempts={rec['attempts']} "
                      f"hidden={rec['hidden_rc']} {rec['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
