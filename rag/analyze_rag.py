#!/usr/bin/env python3
"""Анализ эксперимента 6 (RAG): results/rag/rag.jsonl → results/rag/summary.md.

  python rag/analyze_rag.py [--in results/rag/rag.jsonl]
"""
from __future__ import annotations

import argparse
import sys
import json
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDS = {"A": "без проверки", "C": "модель сама ставит TRUE/FALSE", "D": "программа проверяет цитату, ищет дальше",
         "J": "D + журнал проверенных фактов",
         "D_src": "D + источник должен быть той командой, о которой вопрос (добавлено после просмотра данных)"}


def fisher(a, b, c, d):
    """Двусторонний точный тест Фишера для таблицы [[a, b], [c, d]]."""
    n, r1, c1 = a + b + c + d, a + b, a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


def pct(k, n):
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "—"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(ROOT / "results/rag/rag.jsonl"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()]
    sys.path.insert(0, str(ROOT / "rag"))
    import rag_experiment as rx
    qmap = {q["id"]: q for f in ("questions.json", "questions_independent.json") if (ROOT / "rag" / f).exists()
            for q in json.loads((ROOT / "rag" / f).read_text())}
    epath = Path(args.inp).with_name(Path(args.inp).stem + "_E.jsonl")
    ev = {(e["run"], e["id"]): e["verdict"] for e in map(json.loads, epath.read_text().splitlines())} if epath.exists() else {}
    if ev:
        rows = [r for r in rows if (r["run"], r["id"]) in ev]  # E сравниваем на тех же ответах
    for r in rows:  # оценку пересчитываем текущими правилами (одинаково для всех условий)
        q = qmap[r["id"]]
        dec = {c: (rx.first_token(a) or None) if a else None for c, a in r["decision"].items()}
        # пост-хок (после просмотра данных): D_src — D + программа требует, чтобы источник совпадал с командой из вопроса
        last = r["D"]["attempts"][-1]
        dec["D_src"] = dec["D"] if str(last["ans"].get("source", "")).strip().lower() == q["source"] else None
        if ev:  # пост-хок: E — D + независимый судья смысла (отдельный вызов модели, YES/NO)
            dec["E"] = dec["D"] if ev[(r["run"], r["id"])] == "YES" else None
        r["grade"] = {c: rx.grade(q, a) for c, a in dec.items()}
    ans = [r for r in rows if r["kind"] == "answerable"]
    trap = [r for r in rows if r["kind"] == "trap"]
    para = [r for r in ans if r["paraphrase_of"]]
    runs = sorted({r["run"] for r in rows})
    L = [f"# Эксперимент 6: RAG — кто ставит «true/false»\n",
         f"Прогонов: {len(runs)}; ответов: {len(rows)} (вопросов с ответом: {len(ans)}, ловушек: {len(trap)}).\n",
         "«Уверенно неверно» — условие выдало ответ, а скрытая оценка его не подтвердила "
         "(на ловушке любой ответ, кроме NOT_FOUND, — неверный).\n",
         "| Условие | Уверенно неверно (все вопросы) ↓ | Верно (вопросы с ответом) ↑ | Ловушки распознаны ↑ | Воздержался на вопросе с ответом |",
         "|---|---|---|---|---|"]
    wrong = {}
    if ev:
        CONDS["E"] = "D + независимый судья смысла (добавлено после просмотра данных)"
    for c, name in CONDS.items():
        g = Counter(r["grade"][c] for r in rows)
        ga = Counter(r["grade"][c] for r in ans)
        gt = Counter(r["grade"][c] for r in trap)
        wrong[c] = g["wrong"]
        L.append(f"| **{c}** — {name} | {pct(g['wrong'], len(rows))} | {pct(ga['correct'], len(ans))} | "
                 f"{pct(gt['correct_abstain'], len(trap))} | {pct(ga['abstain'], len(ans))} |")
    n = len(rows)
    L.append("\nТочный тест Фишера (уверенно неверно, двусторонний):\n")
    for a, b in (("A", "C"), ("A", "D"), ("C", "D"), ("D", "J"), ("A", "D_src")) + ((("A", "E"), ("D", "E")) if ev else ()):
        L.append(f"* {a} vs {b}: {wrong[a]}/{n} vs {wrong[b]}/{n}, p = {fisher(wrong[a], n - wrong[a], wrong[b], n - wrong[b]):.2g}")

    # самооценка модели: насколько TRUE совпадает с правдой
    st = Counter((str(r["first"].get("self_check", "")).upper() == "TRUE", r["grade"]["A"]) for r in rows)
    L.append("\n## Самооценка модели (условие C)\n")
    L.append(f"* Неверных ответов, которые модель пометила TRUE: {st[(True, 'wrong')]} из {st[(True, 'wrong')] + st[(False, 'wrong')]}.")
    L.append(f"* Верных ответов, которые модель пометила FALSE: {st[(False, 'correct')]} из {st[(True, 'correct')] + st[(False, 'correct')]}.")

    # что дал поиск дальше (повторы D)
    fixed = sum(1 for r in rows if r["grade"]["A"] != "correct" and r["grade"]["D"] == "correct" and len(r["D"]["attempts"]) > 1)
    rescued_wrong = sum(1 for r in rows if r["grade"]["A"] == "wrong" and r["grade"]["D"] in ("abstain", "correct_abstain"))
    lost = sum(1 for r in rows if r["grade"]["A"] == "correct" and r["grade"]["D"] == "abstain")
    why = Counter(a["why"].split(" '")[0].split(" was")[0] for r in rows for a in r["D"]["attempts"] if not a["verified"] and a["why"] != "not_found")
    L.append("\n## Проверка программой (условие D)\n")
    L.append(f"* Ошибок A, которые D остановил (воздержался вместо неверного ответа): {rescued_wrong}.")
    L.append(f"* Ответов, ставших верными после «поиска дальше» (повтор после неподтверждённой цитаты): {fixed}.")
    L.append(f"* Верных ответов A, которые D отклонил (не смог подтвердить цитатой): {lost}.")
    L.append("* Почему не подтверждалось: " + "; ".join(f"{k} — {v}" for k, v in why.most_common()))

    # журнал: перефразированные вопросы
    if para:
        gd, gj = Counter(r["grade"]["D"] for r in para), Counter(r["grade"]["J"] for r in para)
        used = sum(1 for r in para if r["J"]["attempts"][0]["journal_facts"])
        L.append("\n## Журнал проверенных фактов (условие J), перефразированные вопросы\n")
        L.append(f"* Верно: D {pct(gd['correct'], len(para))}, J {pct(gj['correct'], len(para))}; "
                 f"уверенно неверно: D {gd['wrong']}, J {gj['wrong']}. Записи журнала были показаны в {used} из {len(para)}.")
        sec = lambda c: sum(a["sec"] for r in para for a in r[c]["attempts"]) / len(para)
        L.append(f"* Среднее время модели на вопрос (с повторами): D {sec('D'):.0f} с, J {sec('J'):.0f} с.")
    out = ROOT / "results/rag/summary.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
