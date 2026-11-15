#!/usr/bin/env python3
"""Эксперимент 6, условие E (добавлено после просмотра первых данных): D + независимый проверяющий смысла.

Проверка программой (D) доказывает, что цитата настоящая и опция в ней есть, но не что опция отвечает на вопрос
(модель приводила реальные цитаты к опциям с обратным смыслом). Здесь отдельный вызов модели — без истории
решающего, без правильных ответов — видит только вопрос, опцию и её пункт справки и отвечает YES/NO:
«делает ли эта опция то, о чём спрашивают?». E = ответ D, если судья сказал YES, иначе воздержание.

  python rag/judge_e.py [--in results/rag/rag.jsonl] → results/rag/rag_E.jsonl (повторный запуск пропускает готовое)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rag_experiment as rx  # noqa: E402

JUDGE = """You are a strict reviewer. You see a question about a Linux command, a proposed option, and the
documentation entry the answer cites. Decide ONLY from the documentation entry whether the proposed option does
exactly what the question asks (same effect, not the opposite, not a related feature, and for the command asked about).
Reply with a JSON object: {"verdict": "YES" or "NO", "reason": "<one short sentence>"}."""


def entry_text(doc: str, quote: str) -> str:
    """Пункт справки вокруг цитаты: от пустой строки выше до пустой строки ниже (как видит его человек)."""
    keep = [i for i, ch in enumerate(doc) if ch.isascii() and ch.isalnum()]
    norm = "".join(doc[i].lower() for i in keep)
    q = rx.alnum(quote)
    pos = norm.find(q)
    if pos < 0:
        return quote
    start, end = keep[pos], keep[pos + len(q) - 1] + 1
    blanks = [m.end() for m in re.finditer(r"\n[ \t]*\n", doc[:start])]
    s = max(blanks[-1] if blanks else 0, start - rx.HEADER_WINDOW)
    m = re.search(r"\n[ \t]*\n", doc[end:])
    e = end + (m.start() if m else 0)
    return doc[s:min(e, end + 600)].strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(HERE.parent / "results/rag/rag.jsonl"))
    args = ap.parse_args()
    inp = Path(args.inp)
    out = inp.with_name(inp.stem + "_E.jsonl")
    docs = {p.stem: p.read_text() for p in (HERE / "corpus").glob("*.txt")}
    done = {(r["run"], r["id"]) for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
    rows = [json.loads(l) for l in inp.read_text().splitlines() if l.strip()]
    for n, r in enumerate(rows, 1):
        if (r["run"], r["id"]) in done:
            continue
        last = r["D"]["attempts"][-1]
        rec = {"run": r["run"], "id": r["id"], "verdict": None}
        if last["verified"]:
            a = last["ans"]
            src = str(a.get("source", "")).strip().lower()
            entry = entry_text(docs[src], str(a.get("quote", "")))
            user = (f"Question: {r['question']}\nProposed option: {rx.first_token(a.get('option', ''))}\n"
                    f"Cited page: {src}\nDocumentation entry:\n{entry}")
            ans, raw = rx.ask([{"role": "system", "content": JUDGE}, {"role": "user", "content": user}])
            rec |= {"verdict": str(ans.get("verdict", "")).upper(), "reason": ans.get("reason", ""), "raw": raw}
        with out.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"E {n}/{len(rows)} {r['id']} {rec['verdict']}", flush=True)


if __name__ == "__main__":
    main()
