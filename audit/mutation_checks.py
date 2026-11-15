#!/usr/bin/env python3
"""Мутационная проверка скрытых проверок (не из плана, после разбора «что спросит опытный рецензент»).

audit/mutants.json — «почти верные» решения: каждое нарушает ровно одно требование task.md. Их написал отдельный
агент Claude, который видел только task.md, setup.sh, solution.sh и meta.yaml (НЕ check.sh). Каждый мутант
прогоняется через скрытую проверку (sandbox.evaluate). Хорошая проверка отклоняет мутанта.
Выжившие мутанты разбираются вручную: настоящая дыра в проверке или мутант на самом деле не нарушает условие.
Кэш: results/mutation_checks.jsonl; отчёт: results/mutation_checks.md.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
R = ROOT / "results"
OUT = R / "mutation_checks.jsonl"


def run():
    from sandbox import evaluate, load_tasks
    tasks = {t.name: t for t in load_tasks()}
    muts = json.loads((HERE / "mutants.json").read_text())
    done = {(r["task"], r["id"]) for r in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else set()
    with OUT.open("a") as f:
        for task, ms in muts.items():
            for m in ms:
                if (task, m["id"]) in done:
                    continue
                rc, log = evaluate(tasks[task], m["script"])
                f.write(json.dumps({"task": task, "id": m["id"], "violates": m["violates"], "hidden_rc": rc,
                                    "log": log[-1500:]}, ensure_ascii=False) + "\n")
                f.flush()
                print(task, m["id"], "killed" if rc else "SURVIVED", flush=True)


def report():
    rows = [json.loads(l) for l in OUT.read_text().splitlines()]
    review = json.loads((R / "mutation_review.json").read_text()) if (R / "mutation_review.json").exists() else {}
    by = defaultdict(list)
    for r in rows:
        by[r["task"]].append(r)
    killed = sum(r["hidden_rc"] != 0 for r in rows)
    L = ["# Мутационная проверка скрытых проверок (не из плана)\n",
         "Скрипт: `audit/mutation_checks.py`. Мутанты (`audit/mutants.json`) написал отдельный агент Claude, "
         "не видевший `check.sh`; каждый нарушает одно требование `task.md`.\n",
         f"**Убито {killed} из {len(rows)} мутантов ({killed / len(rows):.0%}).**\n",
         "| Задача | Убито | Выжили (какое требование нарушено) |", "|---|---|---|"]
    for t in sorted(by):
        rs = by[t]
        surv = [r for r in rs if r["hidden_rc"] == 0]
        L.append(f"| {t} | {len(rs) - len(surv)}/{len(rs)} | " + "; ".join(f"{r['id']}: {r['violates']}" for r in surv) + " |")
    if review:
        L += ["\n## Разбор выживших\n", "| Мутант | Вердикт | Почему |", "|---|---|---|"]
        for k, v in review.items():
            L.append(f"| {k} | {v['verdict']} | {v['why']} |")
    text = "\n".join(L) + "\n"
    (R / "mutation_checks.md").write_text(text)
    print(text)


if __name__ == "__main__":
    if "--report" not in sys.argv:
        run()
    report()
