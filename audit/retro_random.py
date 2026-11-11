#!/usr/bin/env python3
"""F21: (1) атаки «готовый ответ» red team против случайных данных; (2) все записанные финальные скрипты
модели для 007/009/010 заново оцениваются на 2 случайных зёрнах — совпадает ли вердикт с записанным."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sandbox import ROOT, evaluate, load_tasks  # noqa: E402

tasks = {t.name: t for t in load_tasks()}
out = {"attacks": [], "retro": []}
for f, t in (("attack1_hardcode007.sh", "007-top-ips-500"), ("attack6_hardcode009.sh", "009-config-sed"),
             ("attack5_hardcode010.sh", "010-big-files")):
    rcs = [evaluate(tasks[t], (ROOT / "redteam" / f).read_text())[0] for _ in range(3)]
    out["attacks"].append({"attack": f, "task": t, "check_rc_on_3_seeds": rcs})
    print(f"{f}: {rcs}  ({'всё ещё проходит!' if 0 in rcs else 'больше не проходит'})")
cache = {}
for cond in "ACDE":
    for l in (ROOT / f"results/{cond}.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r["task"] not in ("007-top-ips-500", "009-config-sed", "010-big-files") or r["hidden_rc"] is None:
            continue
        key = (r["task"], r["final_script"])
        if key not in cache:
            cache[key] = [evaluate(tasks[r["task"]], r["final_script"])[0] for _ in range(2)]
        new = cache[key]
        out["retro"].append({"cond": cond, "run": r["run"], "task": r["task"], "old_pass": r["hidden_rc"] == 0,
                             "new_pass_2_seeds": [x == 0 for x in new]})
same = sum(all(p == x["old_pass"] for p in x["new_pass_2_seeds"]) for x in out["retro"])
print(f"retro: {len(out['retro'])} records ({len(cache)} unique scripts); verdict unchanged on both seeds: {same}")
for x in out["retro"]:
    if not all(p == x["old_pass"] for p in x["new_pass_2_seeds"]):
        print("  CHANGED", x)
(ROOT / "results/retro_random.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
