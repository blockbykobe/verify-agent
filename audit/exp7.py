#!/usr/bin/env python3
"""Эксперимент 7 — перекрёстная проверка на задачах Gemini (101–110), план: docs/prereg_human_tasks.md.

Тот же код, что в эксперименте 1c (audit/cross_verifier.py), с другими источниками данных:
решения и тесты D — results/exp7/{qwen,haiku}/{A,C,D}.jsonl; кэш и отчёт 1c-формата — results/exp7/.
Сверху — чтение по плану: H6 (знаковый тест по смешанным задачам и двухуровневый бутстрэп), H7 (исправность тестов
по задачам), правило про «родство» (разница BA, усреднённой по задачам, против +0,30 в 1c).

  python audit/exp7.py          # прогон пар в Docker (можно прерывать) + отчёт
  python audit/exp7.py --report
"""
import itertools
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import cross_verifier as cv  # noqa: E402

E7 = cv.R / "exp7"
cv.R = E7
cv.CACHE = E7 / "cross_verifier.jsonl"
cv.SRC = {"qwen": E7 / "qwen", "haiku": E7 / "haiku"}
cv.SOLVABLE = [str(100 + i) for i in range(1, 11)]
cv.HEADER = ("Эксперимент 7: тот же анализ, что в 1c, на задачах Gemini 101–110; план — "
             "[`docs/prereg_human_tasks.md`](../../docs/prereg_human_tasks.md); решения и тесты — из новых запусков "
             "(results/exp7/). Скрипт: `audit/exp7.py`.\n")
BASE_1C = 0.30  # разница BA, усреднённой по задачам, в 1c (0.86 − 0.56)


def signflip(dd):
    obs = abs(sum(dd))
    return sum(abs(sum(s * x for s, x in zip(sg, dd))) >= obs - 1e-12
               for sg in itertools.product((1, -1), repeat=len(dd))) / 2 ** len(dd)


def readout():
    rows = [json.loads(l) for l in cv.CACHE.read_text().splitlines()]
    truth = {(r["solver"], r["task"], r["sid"]): r["hidden_rc"] == 0 for r in rows if r["kind"] == "truth"}
    pairs = [{"task": r["task"], "verifier": r["verifier"], "pass": r["test_rc"] == 0,
              "good": truth[(r["solver"], r["task"], r["sid"])]} for r in rows if r["kind"] == "pair"]
    tasks = sorted({p["task"] for p in pairs})
    mixed = [t for t in tasks if len({p["good"] for p in pairs if p["task"] == t}) == 2]
    per = {v: {t: cv.ba([p for p in pairs if p["task"] == t and p["verifier"] == v])[2] for t in mixed}
           for v in ("qwen", "haiku")}
    # задача без тестов одного из проверяющих (BA = NaN) в знаковый тест не входит
    dd = [per["haiku"][t] - per["qwen"][t] for t in mixed if per["haiku"][t] == per["haiku"][t] and per["qwen"][t] == per["qwen"][t]]
    better = sum(x > 0 for x in dd)
    p = signflip(dd) if dd else float("nan")
    rep = (E7 / "cross_verifier.md").read_text()
    m = re.search(r"интервал \[([+-]\d\.\d\d); ([+-]\d\.\d\d)\]", rep)
    lo, hi = (float(m.group(1)), float(m.group(2))) if m else (float("nan"), float("nan"))
    tavg = {v: sum(per[v].values()) / len(mixed) for v in per} if mixed else {}
    val = [r for r in rows if r["kind"] == "validity"]
    vt = {}
    for t in tasks:
        vt[t] = {v: (sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in val if r["task"] == t and r["verifier"] == v),
                     sum(1 for r in val if r["task"] == t and r["verifier"] == v)) for v in ("qwen", "haiku")}
    h7 = sum(1 for t in tasks if vt[t]["haiku"][1] and vt[t]["qwen"][1] and
             vt[t]["haiku"][0] / vt[t]["haiku"][1] > vt[t]["qwen"][0] / vt[t]["qwen"][1])
    L = ["# Эксперимент 7 — задачи от Gemini: чтение по плану\n",
         "План: [`docs/prereg_human_tasks.md`](../../docs/prereg_human_tasks.md) (с дополнениями). Полный отчёт в формате 1c: "
         "[`cross_verifier.md`](cross_verifier.md).\n",
         f"* Задач с хорошими и плохими решениями (смешанных): **{len(mixed)}** из {len(tasks)} ({', '.join(t[:3] for t in mixed)}).",
         "| Задача | BA тестов qwen | BA тестов Haiku |", "|---|---|---|"]
    L += [f"| {t} | {per['qwen'][t]:.2f} | {per['haiku'][t]:.2f} |" for t in mixed]
    if len(mixed) < 6:
        h6 = "не проверяемо (меньше 6 смешанных задач)"
    else:
        h6 = ("подтверждено" if better > len(mixed) / 2 and p < 0.05 and lo > 0 else "не подтверждено")
    L += ["", f"* **H6:** Haiku лучше в {better} из {len(mixed)} смешанных задач, точный знаковый тест p = {p:.3f}; "
          f"двухуровневый бутстрэп разницы [{lo:+.2f}; {hi:+.2f}]. **Итог: {h6}.**",
          f"* **H7:** исправных тестов у Haiku больше, чем у qwen, в {h7} из {len(tasks)} задач "
          f"(**{'подтверждено' if h7 > len(tasks) / 2 else 'не подтверждено'}**).",
          "| Задача | Исправных тестов qwen | Исправных тестов Haiku |", "|---|---|---|"]
    L += [f"| {t} | {vt[t]['qwen'][0]}/{vt[t]['qwen'][1]} | {vt[t]['haiku'][0]}/{vt[t]['haiku'][1]} |" for t in tasks]
    if tavg:
        d = tavg["haiku"] - tavg["qwen"]
        L += ["", f"* **Родство:** BA, усреднённая по смешанным задачам: qwen {tavg['qwen']:.2f}, Haiku {tavg['haiku']:.2f}, "
              f"разница {d:+.2f} (в 1c {BASE_1C:+.2f}). Правило плана: меньше {BASE_1C / 2:+.2f} → родство, вероятно, "
              f"часть эффекта 1c. **Итог: {'родство вероятно' if d < BASE_1C / 2 else ('родство не главное объяснение' if h6 == 'подтверждено' else 'не решено (H6 не подтверждено)')}.**"]
    L += ["\n## Решатели по задачам (по плану, описательно): верно / уверенно неверно\n",
          "| Задача | qwen A | qwen C | qwen D | Haiku A | Haiku C | Haiku D |", "|---|---|---|---|---|---|---|"]
    runs = {(w, c): [json.loads(l) for l in (E7 / w / f"{c}.jsonl").read_text().splitlines()]
            for w in ("qwen", "haiku") for c in "ACD"}
    for t in sorted({r["task"] for r in runs[("qwen", "A")]}):
        cells = []
        for w in ("qwen", "haiku"):
            for c in "ACD":
                a = [r for r in runs[(w, c)] if r["task"] == t and r["outcome"] in ("answered", "verified")]
                cells.append(f"{sum(r['hidden_rc'] == 0 for r in a)} / {sum(r['hidden_rc'] != 0 for r in a)}")
        L.append(f"| {t} | " + " | ".join(cells) + " |")
    text = "\n".join(L) + "\n"
    (E7 / "summary.md").write_text(text)
    print(text)


if __name__ == "__main__":
    if "--report" not in sys.argv:
        cv.run()
    cv.report()
    readout()
