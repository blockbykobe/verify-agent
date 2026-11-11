#!/usr/bin/env python3
"""Ретро-проверка: все финальные скрипты модели из results/{A,C,D,E}.jsonl (solve-задачи, answered/verified)
заново оцениваются защищённой evaluate(hardened=True) и сравниваются с записанным hidden_rc.
Цель: защита не меняет честных результатов; и было ли в данных хоть одно «решение-подделка»."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sandbox import ROOT, evaluate, load_tasks  # noqa: E402

tasks = {t.name: t for t in load_tasks()}
rows, cache = [], {}
for cond in "ACDE":
    for l in (ROOT / f"results/{cond}.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r["expected"] != "solve" or r["hidden_rc"] is None:
            continue
        key = (r["task"], r["final_script"])
        if key not in cache:
            rc, log = evaluate(tasks[r["task"]], r["final_script"], hardened=True)
            cache[key] = (rc, "[tamper]" in log)
        rc, tamper = cache[key]
        rows.append({"cond": cond, "run": r["run"], "task": r["task"], "old_rc": r["hidden_rc"],
                     "new_rc": rc, "tamper": tamper, "same": (r["hidden_rc"] == 0) == (rc == 0)})
diff = [x for x in rows if not x["same"]]
print(f"re-evaluated {len(rows)} records ({len(cache)} unique scripts); verdict changed: {len(diff)}; "
      f"tamper flagged: {sum(x['tamper'] for x in rows)}")
for x in diff:
    print("  CHANGED", x)
(ROOT / "results/retro_eval.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
