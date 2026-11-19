#!/usr/bin/env python3
"""Эксперимент 8b — анализ по плану docs/prereg_traps_8b.md. Читает results/exp8b/<model>_<cond>.jsonl,
пишет results/exp8b/summary.md. Тесты — точный знаковый тест перестановкой знаков по ловушкам (как в эксперименте 8).

  python audit/exp8b.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "audit"), str(ROOT / "experiments"), str(ROOT)]
import exp8  # noqa: E402
from exp8b_traps import TRAPS  # noqa: E402

D = ROOT / "results" / "exp8b"
MODELS = ["qwen", "qwen14b", "llama8b", "gemma9b", "haiku"]
NAMES = {"qwen": "qwen2.5-coder 7B (CPU)", "qwen14b": "qwen2.5-coder 14B", "llama8b": "Llama 3.1 8B",
         "gemma9b": "Gemma 2 9B", "haiku": "Claude Haiku 5.5"}


def load(m, c):
    p = D / f"{m}_{c}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def main():
    data = {(m, c): load(m, c) for m in MODELS for c in "PV"}
    out = ["# Experiment 8b — false-premise traps, fixed harness, five agents", "",
           "Plan: [`docs/prereg_traps_8b.md`](../../docs/prereg_traps_8b.md). Script: `audit/exp8b.py`.", "",
           "| Agent | Prompt | Episodes | Caught | Noticed | Harm (6 traps) | T06 key removed by agent | No FINAL / unformatted | Mean steps |",
           "|---|---|---|---|---|---|---|---|---|"]
    for (m, c), rows in data.items():
        if not rows:
            continue
        n = len(rows)
        hr = [r for r in rows if r["harm"] is not None]
        t6 = [r for r in rows if r["trap"] == "T06-vasya-key"]
        out.append(f"| {NAMES[m]} | {c} | {n} | {sum(r['caught'] for r in rows)}/{n} | {sum(r['noticed'] for r in rows)}/{n} | "
                   f"{sum(r['harm'] for r in hr)}/{len(hr)} | {sum(bool(r.get('t06_key_removed')) for r in t6)}/{len(t6)} | "
                   f"{sum(r['status'] == 'no_final' for r in rows)} / {sum(r['status'] == 'unformatted' for r in rows)} | "
                   f"{sum(r['n_steps'] for r in rows) / n:.1f} |")
    cells = [mc for mc in data if data[mc]]
    out += ["", "## Per trap (caught / runs)", "", "| Trap | " + " | ".join(f"{m} {c}" for m, c in cells) + " |",
            "|---|" + "---|" * len(cells)]
    for t in TRAPS:
        row = []
        for mc in cells:
            r = [x for x in data[mc] if x["trap"] == t]
            row.append(f"{sum(x['caught'] for x in r)}/{len(r)}")
        out.append(f"| {t} | " + " | ".join(row) + " |")
    out += ["", "## Pre-registered tests", ""]
    tests = [(("haiku", "P"), ("qwen", "P"), "H8a', Haiku vs qwen 7B, plain prompt"),
             (("qwen", "V"), ("qwen", "P"), "H8b', qwen 7B: verify-first vs plain"),
             (("qwen14b", "P"), ("qwen", "P"), "H8d, qwen 14B vs qwen 7B, plain prompt"),
             (("haiku", "P"), ("qwen14b", "P"), "H8e, Haiku vs qwen 14B, plain prompt")]
    desc = [(("haiku", "P"), ("llama8b", "P"), "descriptive, Haiku vs Llama 8B, P"),
            (("haiku", "P"), ("gemma9b", "P"), "descriptive, Haiku vs Gemma 9B, P"),
            (("haiku", "V"), ("haiku", "P"), "descriptive, Haiku V vs P")] + [
            ((m, "V"), (m, "P"), f"descriptive, {m} V vs P") for m in ("qwen14b", "llama8b", "gemma9b")]
    for a, b, label in tests + desc:
        if data[a] and data[b]:
            out.append(exp8.compare(data[a], data[b], label))
    D.mkdir(parents=True, exist_ok=True)
    (D / "summary.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
