#!/usr/bin/env python3
"""Эксперимент 6 (RAG) с Claude вместо qwen: те же вопросы, поиск, проверка программой, журнал и оценка
(rag_experiment.py используется как есть, подменяется только обращение к модели). Можно сразу прогнать и
независимого судью смысла (judge_e.py) — тоже на Claude.

Ключ — ТОЛЬКО из переменной окружения ANTHROPIC_API_KEY (ANTHROPIC_API_KEY="$(cat ~/.anthropic_key)").
Расход ограничен --max-usd: при достижении прогон останавливается.

  python rag/claude_rag.py --runs 3 [--questions rag/questions_independent.json] [--judge]
Результаты: results/rag/<model>/rag[_independent].jsonl (+ _E.jsonl), расход — usage.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "experiments"))
from claude_confession import PRICES  # noqa: E402

import rag_experiment as rx  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--questions", default=str(HERE / "questions.json"))
    ap.add_argument("--judge", action="store_true", help="после прогона запустить судью смысла (условие E)")
    ap.add_argument("--max-usd", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0, help="только первые N вопросов (проверочный запуск)")
    args = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY не задан — ничего не запускаю.")
        return 2
    import anthropic

    out_dir = ROOT / "results/rag" / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    usage_log = out_dir / "usage.jsonl"
    pin, pout = PRICES[args.model]
    client = anthropic.Anthropic()

    def spent() -> float:
        if not usage_log.exists():
            return 0.0
        u = [json.loads(l) for l in usage_log.read_text().splitlines()]
        return sum(x["input_tokens"] for x in u) * pin / 1e6 + sum(x["output_tokens"] for x in u) * pout / 1e6

    def ask(messages: list[dict]) -> tuple[dict, str]:
        if spent() >= args.max_usd:
            raise RuntimeError(f"budget ${args.max_usd} reached")
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        r = client.with_options(timeout=300, max_retries=4).messages.create(
            model=args.model, max_tokens=4000, system=system, messages=msgs, output_config={"effort": args.effort})
        with usage_log.open("a") as f:
            f.write(json.dumps({"model": r.model, "stop_reason": r.stop_reason,
                                "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}) + "\n")
        raw = "".join(b.text for b in r.content if b.type == "text")
        m = re.search(r"\{.*\}", raw, re.S)  # у API нет режима «только JSON» — берём объект из текста
        try:
            d = json.loads(m.group()) if m else None
            if not isinstance(d, dict):
                raise ValueError
        except ValueError:
            d = {"option": "", "quote": "", "source": "", "self_check": "FALSE"}
        return d, raw

    rx.ask = ask  # solve() и judge_e вызывают ask через модуль rx
    name = "rag" if Path(args.questions).name == "questions.json" else "rag_independent"
    out = out_dir / f"{name}.jsonl"
    sys.argv = [sys.argv[0], "--runs", str(args.runs), "--questions", args.questions, "--out", str(out)] + (["--limit", str(args.limit)] if args.limit else [])
    rx.main()
    if args.judge:
        import judge_e
        sys.argv = [sys.argv[0], "--in", str(out)]
        judge_e.main()
    print(f"spent ≈ ${spent():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
