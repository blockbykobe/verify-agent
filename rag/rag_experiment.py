#!/usr/bin/env python3
"""Эксперимент 6: RAG — кто должен ставить «true/false» в конце?

Модель (qwen2.5-coder:7b, локально) отвечает на вопросы о командах Linux по найденным фрагментам справочных
страниц (man). Часть вопросов — ловушки: такой опции в документации нет, правильный ответ — NOT_FOUND.
Правильные ответы (gold) модель не видит; ими пользуется только итоговая оценка.

Условия (на одном и том же первом ответе, чтобы сравнение было парным):
  A — ответ принимается как есть;
  C — модель сама ставит self_check TRUE/FALSE; FALSE → воздержание;
  D — ПРОГРАММА проверяет: цитата дословно есть в названной справочной странице и содержит названную опцию.
      Не подтвердилось → модель ищет дальше (больше фрагментов + сообщение, что именно не подтвердилось),
      до 2 повторов; не подтвердилось и тогда → воздержание «не нашёл подтверждения»;
  J — D + журнал проверенных фактов: ответы, прошедшие проверку программой, записываются в журнал с цепочкой
      хешей; при следующих вопросах модель видит ближайшие записи журнала (целостность цепочки проверяется
      перед каждым использованием). В журнал попадает только проверенное.

  python rag/rag_experiment.py --runs 3
  python rag/rag_experiment.py --runs 3 --questions rag/questions_independent.json --out results/rag/rag_independent.jsonl
Результаты: results/rag/rag.jsonl (уже выполненные (run, id) пропускаются).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from sandbox import MODEL, OLLAMA_URL  # noqa: E402

OUT = ROOT / "results/rag/rag.jsonl"
TEMPERATURE = 0.7
K = [4, 8, 8]  # фрагментов на попытку
SYSTEM = """You answer questions about Linux commands using ONLY the documentation excerpts provided.
Reply with a single JSON object:
{"option": "<the single option, test or subcommand that answers the question, written exactly as in the documentation, with its dashes, e.g. -mtime or --follow>",
 "quote": "<one sentence copied VERBATIM from the excerpts that shows this>",
 "source": "<the command name of the page the quote comes from, e.g. find>",
 "self_check": "TRUE" or "FALSE"}
self_check: TRUE only if you are sure the answer is correct and fully supported by the quote.
If the excerpts do not contain the answer, reply {"option": "NOT_FOUND", "quote": "", "source": "", "self_check": "TRUE"}.
Never invent options that are not in the excerpts."""


# ---------------------------------------------------------------- поиск (BM25, без внешних библиотек)
WORD = re.compile(r"--?[a-z0-9][\w-]*|[a-z0-9]+", re.I)
STOP = set("the a an of to and or in on for is are be by with which what how do does i it this that as at from "
           "option options command".split())


def toks(s: str) -> list[str]:
    return [t for t in (w.lower() for w in WORD.findall(s)) if t not in STOP]


def chunk_corpus() -> list[dict]:
    chunks = []
    for p in sorted((HERE / "corpus").glob("*.txt")):
        paras, cur = [], ""
        for para in re.split(r"\n\s*\n", p.read_text()):
            if len(cur) + len(para) > 900 and cur:
                paras.append(cur)
                cur = ""
            cur += para.strip("\n") + "\n\n"
        if cur.strip():
            paras.append(cur)
        for i, t in enumerate(paras):
            chunks.append({"id": f"{p.stem}#{i}", "doc": p.stem, "text": t, "toks": toks(t + " " + p.stem)})
    return chunks


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.4, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(map(len, docs)) / max(1, len(docs))
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(d) for d in docs]

    def top(self, query: list[str], k: int) -> list[int]:
        scores = []
        for i, (tf, d) in enumerate(zip(self.tf, self.docs)):
            s = 0.0
            for t in query:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            scores.append((s, i))
        return [i for s, i in sorted(scores, reverse=True)[:k] if s > 0]


# ---------------------------------------------------------------- проверка программой
def alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def first_token(option: str) -> str:
    """Первое слово ответа без аргумента: '-mtime +30' → '-mtime', '--in-place[=SUFFIX]' / '-i[SUFFIX]' → опция."""
    t = (option or "").strip().split()
    return re.sub(r"\[.*$", "", t[0].split("=")[0]).strip("`'\",.;:") if t else ""


def variants(opt: str) -> set[str]:
    """Опция как написана и без/с дефисами: модель иногда пишет 'follow' вместо '--follow'."""
    base = opt.lstrip("-")
    return {opt, base, "-" + base, "--" + base} if base else set()


def has_option(text: str, opt: str) -> bool:
    return any(re.search(r"(?<![\w-])" + re.escape(v) + r"(?![\w-])", text) for v in variants(opt) if v.startswith("-") or v == opt)


HEADER_WINDOW = 600  # в man опция стоит в строке-заголовке над описанием; ищем до пустой строки выше


def verify(ans: dict, docs: dict[str, str]) -> tuple[bool, str]:
    """Подтверждена ли документацией названная опция. Только строковые проверки — без модели:
    1) цитата дословно (без учёта пробелов, переносов и регистра) есть в названной странице;
    2) опция есть в самой цитате или в заголовке того же пункта справки (до ближайшей пустой строки выше)."""
    opt = first_token(ans.get("option", ""))
    quote, src = str(ans.get("quote", "")), str(ans.get("source", "")).strip().lower()
    if src not in docs:
        return False, f"source '{src}' is not one of the documentation pages"
    q = alnum(quote)
    if len(q) < 20:
        return False, "the quote is missing or too short"
    raw = docs[src]
    keep = [i for i, ch in enumerate(raw) if ch.isascii() and ch.isalnum()]
    norm = "".join(raw[i].lower() for i in keep)
    pos = norm.find(q)
    if pos < 0:
        return False, f"the quote was not found verbatim in the '{src}' page"
    start, end = keep[pos], keep[pos + len(q) - 1] + 1
    blanks = [m.end() for m in re.finditer(r"\n[ \t]*\n", raw[:start])]
    entry_start = max(blanks[-1] if blanks else 0, start - HEADER_WINDOW)  # начало пункта справки
    if not has_option(raw[entry_start:end], opt):
        return False, f"the option '{opt}' does not appear in or right above the quoted text"
    return True, "ok"


# ---------------------------------------------------------------- журнал проверенных фактов
class Journal:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, question: str, ans: dict) -> None:
        prev = self.rows[-1]["hash"] if self.rows else "0" * 64
        body = {"question": question, "option": first_token(ans["option"]), "quote": ans["quote"], "source": ans["source"]}
        h = hashlib.sha256((prev + json.dumps(body, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
        self.rows.append(body | {"prev": prev, "hash": h})

    def intact(self) -> bool:
        prev = "0" * 64
        for r in self.rows:
            body = {k: r[k] for k in ("question", "option", "quote", "source")}
            if r["prev"] != prev or r["hash"] != hashlib.sha256((prev + json.dumps(body, sort_keys=True, ensure_ascii=False)).encode()).hexdigest():
                return False
            prev = r["hash"]
        return True

    def nearest(self, question: str, k: int = 2) -> list[dict]:
        if not self.rows:
            return []
        assert self.intact(), "журнал повреждён"
        bm = BM25([toks(r["question"] + " " + r["source"]) for r in self.rows])
        return [self.rows[i] for i in bm.top(toks(question), k)]


# ---------------------------------------------------------------- модель
def ask(messages: list[dict]) -> tuple[dict, str]:
    for attempt in range(4):  # сервер модели иногда отвечает 500 при нехватке памяти — повторяем с паузой
        r = httpx.post(OLLAMA_URL, timeout=900, json={
            "model": MODEL, "stream": False, "format": "json", "messages": messages,
            "options": {"temperature": TEMPERATURE, "num_predict": 300}})
        if r.status_code < 500:
            break
        time.sleep(30 * (attempt + 1))
    r.raise_for_status()
    raw = r.json()["message"]["content"]
    try:
        d = json.loads(raw)
        if not isinstance(d, dict):
            raise ValueError
    except ValueError:
        d = {"option": "", "quote": "", "source": "", "self_check": "FALSE"}
    return d, raw


def context(chunks: list[dict], ids: list[int]) -> str:
    return "\n\n".join(f"[excerpt {chunks[i]['id']}]\n{chunks[i]['text'].strip()}" for i in ids)


def solve(q: dict, chunks, bm, docs, journal: Journal | None, first: tuple[dict, str] | None = None) -> dict:
    """Цикл «ответ → проверка программой → поиск дальше». Возвращает все попытки."""
    facts = journal.nearest(q["question"]) if journal is not None else []
    attempts, feedback = [], None
    for a, k in enumerate(K):
        ids = bm.top(toks(q["question"]), k)
        user = ""
        if facts:
            user += "Previously VERIFIED facts (checked by a program against the documentation; may be unrelated):\n"
            user += "\n".join(f"- {f['question']} -> {f['option']} (source {f['source']}: \"{f['quote']}\")" for f in facts) + "\n\n"
        user += f"Documentation excerpts:\n{context(chunks, ids)}\n\nQuestion: {q['question']}"
        if feedback:
            user += f"\n\nYour previous answer could not be verified: {feedback}. Search the excerpts again; " \
                    "copy the quote exactly, or reply NOT_FOUND if the documentation does not contain the answer."
        t0 = time.time()
        if a == 0 and first is not None and not facts:
            ans, raw = first  # тот же первый ответ, что у A/C/D, если журнал ничего не добавил
        else:
            ans, raw = ask([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
        nf = first_token(ans.get("option", "")).upper() == "NOT_FOUND" or not first_token(ans.get("option", ""))
        ok, why = (False, "not_found") if nf else verify(ans, docs)
        attempts.append({"ans": ans, "raw": raw, "k": k, "verified": ok, "why": why, "sec": round(time.time() - t0, 1),
                         "journal_facts": len(facts)})
        if ok or nf:
            break
        feedback = why
    return {"attempts": attempts}


def decide(q: dict, first: dict, d_res: dict, j_res: dict) -> dict:
    """Итог по условиям: answer = опция или None (воздержание)."""
    def opt(a):
        t = first_token(a.get("option", ""))
        return None if not t or t.upper() == "NOT_FOUND" else t
    last_d, last_j = d_res["attempts"][-1], j_res["attempts"][-1]
    return {
        "A": opt(first),
        "C": opt(first) if str(first.get("self_check", "")).upper() == "TRUE" else None,
        "D": opt(last_d["ans"]) if last_d["verified"] else None,
        "J": opt(last_j["ans"]) if last_j["verified"] else None,
    }


def grade(q: dict, answer: str | None) -> str:
    """Скрытая оценка: correct / wrong (уверенно неверно) / abstain."""
    if answer is None:
        return "correct_abstain" if q["kind"] == "trap" else "abstain"
    if q["kind"] == "trap":
        return "wrong"
    return "correct" if variants(answer) & set(q["gold"]) else "wrong"


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="только первые N вопросов (для проверки)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--questions", default=str(HERE / "questions.json"))
    args = ap.parse_args()
    OUT = Path(args.out)
    qs = json.loads(Path(args.questions).read_text())
    chunks = chunk_corpus()
    bm = BM25([c["toks"] for c in chunks])
    docs = {p.stem: p.read_text() for p in (HERE / "corpus").glob("*.txt")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["run"], r["id"]) for r in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else set()
    for run in range(1, args.runs + 1):
        rng = random.Random(run)
        order = sorted(qs, key=lambda q: ("paraphrase_of" in q, rng.random()))  # перефразировки — после оригиналов
        if args.limit:
            order = order[:args.limit]
        journal = Journal()
        prior = [r for r in map(json.loads, OUT.read_text().splitlines())] if OUT.exists() else []
        for r in prior:  # восстановить журнал прогона при продолжении
            if r["run"] == run and r["J"]["attempts"][-1]["verified"]:
                journal.add(r["question"], r["J"]["attempts"][-1]["ans"])
        for n, q in enumerate(order, 1):
            if (run, q["id"]) in done:
                continue
            ids = bm.top(toks(q["question"]), K[0])
            first = ask([{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"Documentation excerpts:\n{context(chunks, ids)}\n\nQuestion: {q['question']}"}])
            d_res = solve(q, chunks, bm, docs, None, first)
            j_res = solve(q, chunks, bm, docs, journal, first)
            if j_res["attempts"][-1]["verified"]:
                journal.add(q["question"], j_res["attempts"][-1]["ans"])
            dec = decide(q, first[0], d_res, j_res)
            row = {"run": run, "id": q["id"], "kind": q["kind"], "question": q["question"], "paraphrase_of": q.get("paraphrase_of"),
                   "first": first[0], "D": d_res, "J": j_res, "decision": dec,
                   "grade": {c: grade(q, a) for c, a in dec.items()}, "retrieved_sources": sorted({chunks[i]["doc"] for i in ids})}
            with OUT.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"run {run} {n}/{len(order)} {q['id']} " + " ".join(f"{c}:{g}" for c, g in row["grade"].items()), flush=True)


if __name__ == "__main__":
    main()
