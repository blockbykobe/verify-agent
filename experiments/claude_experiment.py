#!/usr/bin/env python3
"""Эксперимент 1 (A/C/D/E) с Claude в роли агента вместо qwen. Задачи, песочница, скрытые проверки,
промпты и метрики — те же (experiment.py используется как есть, подменяется только обращение к модели).
Результаты: results/claude/<model>/{A,C,D,E}.jsonl; сводка: python analyze.py --dir results/claude/<model>

Ключ — ТОЛЬКО из переменной окружения ANTHROPIC_API_KEY (например, ANTHROPIC_API_KEY="$(cat ~/.anthropic_key)").
Расход ограничен параметром --max-usd: при его достижении прогон останавливается.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from claude_confession import PRICES  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--cond", nargs="+", default=["A", "C", "D", "E"])
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--max-usd", type=float, default=2.0)
    args = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY не задан — ничего не запускаю.")
        return 2
    import anthropic
    import experiment

    out = ROOT / "results/claude" / f"{args.model}-{args.effort}"
    out.mkdir(parents=True, exist_ok=True)
    usage_log = out / "usage.jsonl"
    pin, pout = PRICES[args.model]
    client = anthropic.Anthropic()

    def spent() -> float:
        if not usage_log.exists():
            return 0.0
        u = [json.loads(l) for l in usage_log.read_text().splitlines()]
        return sum(x["input_tokens"] for x in u) * pin / 1e6 + sum(x["output_tokens"] for x in u) * pout / 1e6

    def chat(messages, temperature=None, num_predict=1024, timeout=900):
        if spent() >= args.max_usd:
            raise RuntimeError(f"budget ${args.max_usd} reached")
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        r = client.with_options(timeout=timeout, max_retries=4).messages.create(
            model=args.model, max_tokens=8000, system=system or anthropic.NOT_GIVEN, messages=msgs,
            output_config={"effort": args.effort})
        with usage_log.open("a") as f:
            f.write(json.dumps({"model": r.model, "stop_reason": r.stop_reason,
                                "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}) + "\n")
        return "[REFUSAL]" if r.stop_reason == "refusal" else "".join(b.text for b in r.content if b.type == "text")

    experiment.chat = chat
    experiment.RESULTS = out
    experiment.TEMPERATURE = None  # Haiku 5.5 / Sonnet 5.5 не принимают нестандартную temperature
    sys.argv = [sys.argv[0], "--cond", *args.cond, "--runs", str(args.runs)]
    experiment.main()
    print(f"spent ≈ ${spent():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
