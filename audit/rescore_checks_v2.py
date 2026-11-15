#!/usr/bin/env python3
"""Повторная оценка после исправления скрытых проверок (v2, ноябрь 2026, по код-ревью).

Исправлены проверки, которые были мягче условия задачи:
  * 004-user-group: не проверялось, что группа и пользователь системные (id < 1000) и что нет /home/deploy;
  * 006-cron-entry: права сравнивались как десятичные числа (700/755 отклонялись);
  * 003-permissions: не проверялось «владельцев не меняй» (в песочнице этой задачи chown всё равно невозможен).
Каждый сохранённый финальный скрипт этих задач заново прогоняется через hardened evaluate(). Старая оценка
сохраняется в поле hidden_rc_v1, новая записывается в hidden_rc. Модель не вызывается. Отчёт: results/rescore_v2.md.

  python audit/rescore_checks_v2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
R = ROOT / "results"
TASKS = {"003-permissions", "004-user-group", "006-cron-entry"}
FILES = [R / f"{c}.jsonl" for c in "ACDE"] + [R / "claude/claude-haiku-5-5-low" / f"{c}.jsonl" for c in "ACDE"]


def main() -> None:
    from sandbox import evaluate, load_tasks
    tasks = {t.name: t for t in load_tasks()}
    lines = ["# Повторная оценка после исправления скрытых проверок (v2)\n",
             "| Файл | Задача | Прогон | Условие | Было (v1) | Стало (v2) |", "|---|---|---|---|---|---|"]
    changed = total = 0
    for path in FILES:
        rows = [json.loads(l) for l in path.read_text().splitlines()]
        for r in rows:
            if r.get("task") not in TASKS or not r.get("final_script") or r.get("hidden_rc") is None:
                continue
            if "hidden_rc_v1" in r:  # уже переоценено
                continue
            rc, log = evaluate(tasks[r["task"]], r["final_script"])
            total += 1
            r["hidden_rc_v1"], r["hidden_rc"], r["hidden_log_v2"] = r["hidden_rc"], rc, log[-1500:]
            if (r["hidden_rc_v1"] == 0) != (rc == 0):
                changed += 1
                lines.append(f"| {path.relative_to(R)} | {r['task']} | {r['run']} | {r['cond']} | "
                             f"{'PASS' if r['hidden_rc_v1'] == 0 else 'FAIL'} | {'PASS' if rc == 0 else 'FAIL'} |")
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(path.relative_to(R), "done", flush=True)
    lines.append(f"\nПереоценено финальных скриптов: {total}; вердикт изменился: {changed}.")
    out = R / "rescore_v2.md"
    old = out.read_text() if out.exists() else ""
    out.write_text(old + "\n".join(lines) + "\n")
    print("\n".join(lines[-3:]))


if __name__ == "__main__":
    main()
