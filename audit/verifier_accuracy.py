#!/usr/bin/env python3
"""Насколько верен сам проверяющий? (ответ на независимые рецензии, 2026-11)

Каждую попытку решения из условий C (тест пишет сама модель) и D (тест пишет независимый проверяющий)
заново прогоняем через скрытую проверку в чистом контейнере и сравниваем с вердиктом теста:
  тест PASS / скрытая PASS — верно принято;   тест FAIL / скрытая PASS — зря отклонено;
  тест PASS / скрытая FAIL — ошибка пропущена; тест FAIL / скрытая FAIL — верно отклонено.
Новых обращений к модели нет: используются сохранённые решения из results/{C,D}.jsonl.

  python audit/verifier_accuracy.py            # кэш: results/verifier_rescore.jsonl (повторный запуск дописывает)
  python audit/verifier_accuracy.py --report   # только отчёт: results/verifier_accuracy.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
R = ROOT / "results"
CACHE = R / "verifier_rescore.jsonl"


def attempts():
    for cond in "CD":
        for r in map(json.loads, (R / f"{cond}.jsonl").read_text().splitlines()):
            if r["expected"] != "solve":
                continue
            for h in r.get("history") or []:
                if h.get("kind") == "script" and h.get("solution") and "test_rc" in h:
                    yield {"cond": cond, "run": r["run"], "task": r["task"], "attempt": h["attempt"],
                           "test_rc": h["test_rc"], "solution": h["solution"]}


def rescore() -> None:
    from sandbox import evaluate, load_tasks
    tasks = {t.name: t for t in load_tasks()}
    done = {(c["cond"], c["run"], c["task"], c["attempt"]) for c in map(json.loads, CACHE.read_text().splitlines())} \
        if CACHE.exists() else set()
    todo = [a for a in attempts() if (a["cond"], a["run"], a["task"], a["attempt"]) not in done]
    for n, a in enumerate(todo, 1):
        rc, _ = evaluate(tasks[a["task"]], a["solution"])
        with CACHE.open("a") as f:
            f.write(json.dumps({k: a[k] for k in ("cond", "run", "task", "attempt", "test_rc")} | {"hidden_rc": rc}) + "\n")
        print(f"{n}/{len(todo)} {a['cond']} {a['task']} test={a['test_rc']} hidden={rc}", flush=True)


def report() -> str:
    rows = [json.loads(l) for l in CACHE.read_text().splitlines()]
    L = ["# Насколько верен проверяющий (C — свой тест модели, D — независимый проверяющий)\n",
         "Каждая попытка решения повторно оценена скрытой проверкой в чистом контейнере. "
         "Источник: results/verifier_rescore.jsonl (скрипт audit/verifier_accuracy.py).\n",
         "| | Попыток | Верно принято | Зря отклонено (хорошее решение) | Ошибка пропущена | Верно отклонено | "
         "Чувствительность (хорошие приняты) | Точность (принятые верны) |", "|---|---|---|---|---|---|---|---|"]
    for cond in "CD":
        c = Counter((r["test_rc"] == 0, r["hidden_rc"] == 0) for r in rows if r["cond"] == cond)
        tp, fn, fp, tn = c[(True, True)], c[(False, True)], c[(True, False)], c[(False, False)]
        sens = f"{tp}/{tp + fn} ({100 * tp / (tp + fn):.0f}%)" if tp + fn else "—"
        prec = f"{tp}/{tp + fp} ({100 * tp / (tp + fp):.0f}%)" if tp + fp else "—"
        L.append(f"| **{cond}** | {tp + fn + fp + tn} | {tp} | {fn} | {fp} | {tn} | {sens} | {prec} |")
    L.append("\n## По задачам (D): хорошие решения, которые тест проверяющего отклонил\n")
    L.append("| Задача | Попыток | Хорошие решения (скрытая PASS) | из них тест отклонил |")
    L.append("|---|---|---|---|")
    by = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        if r["cond"] == "D":
            b = by[r["task"]]
            b[0] += 1
            b[1] += r["hidden_rc"] == 0
            b[2] += r["hidden_rc"] == 0 and r["test_rc"] != 0
    for t in sorted(by):
        L.append(f"| {t} | {by[t][0]} | {by[t][1]} | {by[t][2]} |")
    L.append("\nОговорка: скрытая проверка использует новое случайное зерно данных (VA_SEED), поэтому для задач "
             "007/009/010 данные отличаются от исходного прогона; верное решение от зерна не зависит.")
    text = "\n".join(L) + "\n"
    (R / "verifier_accuracy.md").write_text(text)
    return text


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if not a.report:
        rescore()
    print(report())
