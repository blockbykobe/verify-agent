#!/usr/bin/env python3
"""Один прогон одной задачи (условие A без повторов): модель → policy gate → чистый контейнер → скрытый check."""
import json
import sys
import time
from datetime import datetime, timezone

from sandbox import ROOT, chat, evaluate, load_tasks, parse_answer, policy_gate
from prompts import SYSTEM_A


def main() -> int:
    task = load_tasks([sys.argv[1] if len(sys.argv) > 1 else "001-delete-old-logs"])[0]
    t0 = time.monotonic()
    answer = chat([{"role": "system", "content": SYSTEM_A}, {"role": "user", "content": task.text}])
    kind, payload = parse_answer(answer)
    gate = policy_gate(payload) if kind == "script" else []
    print(f"=== Ответ модели: {kind} ===\n{payload}")
    check_rc, output = None, ""
    if kind == "script" and not gate and task.expected == "solve":
        check_rc, output = evaluate(task, payload)
        print("=== Вывод ===\n" + output)
    verdict = "PASS" if check_rc == 0 else ("GATE" if gate else ("FAIL" if check_rc is not None else kind.upper()))
    print(f"=== {verdict} ({time.monotonic() - t0:.1f} с) ===")
    with (ROOT / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "task": task.name, "kind": kind,
                            "script": payload, "gate": gate, "output": output, "check_rc": check_rc,
                            "verdict": verdict, "seconds": round(time.monotonic() - t0, 1)},
                           ensure_ascii=False) + "\n")
    return 0 if check_rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
