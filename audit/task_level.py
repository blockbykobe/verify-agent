#!/usr/bin/env python3
"""Анализ на уровне задач (ответ на независимые рецензии, 2026-11).

Попытки одной задачи не независимы: 10 прогонов × 10 задач — это 10 кластеров, а не 100 наблюдений.
Поэтому кроме точного теста Фишера по попыткам считаем:
  * таблицу A vs D по каждой задаче;
  * бутстрэп по задачам (95% интервал для разницы долей уверенно неверных ответов);
  * точный перестановочный тест по задачам (смена знака разницы внутри задачи);
  * «плацебо»: случайный отказ с тем же охватом, что у D (ожидаемое число ошибок);
  * точность принятых ответов (доля верных среди выданных).
Новых обращений к модели нет. Результат: results/task_level.md.
"""
from __future__ import annotations

import itertools
import json
import random
from collections import defaultdict
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"


def fisher(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


def load(path):
    return [r for r in map(json.loads, Path(path).read_text().splitlines()) if r["expected"] == "solve"]


answered = lambda r: r["outcome"] in ("answered", "verified")
wrong = lambda r: answered(r) and r["hidden_rc"] != 0
right = lambda r: answered(r) and r["hidden_rc"] == 0


def main() -> None:
    A, D = load(R / "A.jsonl"), load(R / "D.jsonl")
    per = defaultdict(lambda: {c: {"n": 0, "ans": 0, "ok": 0, "wrong": 0} for c in "AD"})
    for c, rows in (("A", A), ("D", D)):
        for r in rows:
            k = per[r["task"]][c]
            k["n"] += 1
            k["ans"] += answered(r)
            k["ok"] += right(r)
            k["wrong"] += wrong(r)
    tasks = sorted(per)
    L = ["# Анализ по задачам: A (без проверки) vs D (независимый проверяющий), qwen 7B, 10 прогонов\n",
         "| Задача | A: ответов / верно / уверенно неверно | D: ответов / верно / уверенно неверно |", "|---|---|---|"]
    for t in tasks:
        a, d = per[t]["A"], per[t]["D"]
        L.append(f"| {t} | {a['ans']} / {a['ok']} / {a['wrong']} | {d['ans']} / {d['ok']} / {d['wrong']} |")
    tot = {c: {k: sum(per[t][c][k] for t in tasks) for k in ("n", "ans", "ok", "wrong")} for c in "AD"}
    a, d = tot["A"], tot["D"]
    L.append(f"| **всего** | {a['ans']} / {a['ok']} / {a['wrong']} | {d['ans']} / {d['ok']} / {d['wrong']} |\n")

    # бутстрэп по задачам
    rng = random.Random(0)
    diffs = []
    for _ in range(20000):
        s = [rng.choice(tasks) for _ in tasks]
        fa = sum(per[t]["A"]["wrong"] for t in s) / sum(per[t]["A"]["n"] for t in s)
        fd = sum(per[t]["D"]["wrong"] for t in s) / sum(per[t]["D"]["n"] for t in s)
        diffs.append(fa - fd)
    diffs.sort()
    # перестановочный тест по задачам
    dd = [per[t]["A"]["wrong"] / per[t]["A"]["n"] - per[t]["D"]["wrong"] / per[t]["D"]["n"] for t in tasks]
    obs = abs(sum(dd))
    signs = list(itertools.product((1, -1), repeat=len(dd)))
    p_perm = sum(abs(sum(s * x for s, x in zip(sg, dd))) >= obs - 1e-12 for sg in signs) / len(signs)
    nz = sum(x != 0 for x in dd)
    import statistics
    m, se = statistics.mean(dd), statistics.stdev(dd) / len(dd) ** 0.5
    t_lo, t_hi = m - 2.262 * se, m + 2.262 * se  # t(0.975, df=9)
    placebo_task = sum(per[t]["A"]["wrong"] * per[t]["D"]["ans"] / per[t]["A"]["ans"] for t in tasks if per[t]["A"]["ans"])
    p_fisher = fisher(a["wrong"], a["n"] - a["wrong"], d["wrong"], d["n"] - d["wrong"])
    L += ["## Значимость разницы «уверенно неверно» (A vs D)\n",
          f"* По попыткам (точный тест Фишера, попытки считаются независимыми): {a['wrong']}/{a['n']} vs "
          f"{d['wrong']}/{d['n']}, p = {p_fisher:.1g}. Это завышает уверенность: попытки одной задачи похожи.",
          f"* Разница {100 * (a['wrong'] / a['n'] - d['wrong'] / d['n']):.0f} п.п. t-интервал по 10 задачам (95%): "
          f"[{100 * t_lo:.0f}; {100 * t_hi:.0f}] п.п. (бутстрэп по задачам даёт [{100 * diffs[500]:.0f}; {100 * diffs[19500]:.0f}], "
          f"но при 10 задачах он слишком узкий).",
          f"* Точный перестановочный тест по задачам (двусторонний): p = {p_perm:.3f}. Разница есть только в {nz} задачах "
          f"из {len(tasks)}, поэтому меньше p = {2 / 2 ** nz:.4f} этот тест дать не может.",
          f"* Задачи, где A ошибался, а D нет: {sum(x > 0 for x in dd)}; где D хуже A: {sum(x < 0 for x in dd)}.\n"]

    ds = [per[t]["A"]["ok"] / per[t]["A"]["n"] - per[t]["D"]["ok"] / per[t]["D"]["n"] for t in tasks]
    obs_s = abs(sum(ds))
    p_solved = sum(abs(sum(x * y for x, y in zip(sg, ds))) >= obs_s - 1e-12 for sg in signs) / len(signs)
    L.append(f"* Решено (A vs D): {a['ok']}/{a['n']} vs {d['ok']}/{d['n']}; задач, где A лучше: {sum(x > 0 for x in ds)}, "
             f"где D лучше: {sum(x < 0 for x in ds)}; точный тест по задачам p = {p_solved:.3f}.\n")
    # плацебо и точность
    keep = d["ans"] / a["ans"]
    L += ["## Чем объясняется снижение: отказом или различением?\n",
          f"* Охват: A выдал {a['ans']} ответов, D — {d['ans']} ({100 * keep:.0f}% от A).",
          f"* Плацебо — случайный отказ с тем же охватом: ожидалось бы {a['wrong'] * keep:.1f} уверенно неверных "
          f"(у D — {d['wrong']}). Точность принятых ответов: A {a['ok']}/{a['ans']} ({100 * a['ok'] / a['ans']:.0f}%), "
          f"D {d['ok']}/{d['ans']} ({100 * d['ok'] / d['ans']:.0f}%), случайный отказ — те же {100 * a['ok'] / a['ans']:.0f}%.",
          f"* Плацебо с тем же охватом ПО КАЖДОЙ ЗАДАЧЕ (отказ с частотой D внутри задачи): ожидалось бы "
          f"{placebo_task:.1f} уверенно неверных (у D — {d['wrong']}). Внутри задач D не лучше случайного отказа.",
          "* Но отказы D не случайны по задачам: на трёх самых трудных задачах (nginx, cron, logrotate) D не выдал "
          "ни одного ответа, а на лёгких выдавал 3–4 из 10. Значит, бо́льшая часть выигрыша — отказ от целых трудных "
          "задач, а не различение верного и неверного решения внутри задачи. Насколько точен сам тест проверяющего — "
          "см. results/verifier_accuracy.md."]

    # Haiku: где ошибки
    H = load(R / "claude/claude-haiku-5-5-low/A.jsonl")
    hw = defaultdict(int)
    for r in H:
        hw[r["task"]] += wrong(r)
    L += ["\n## Claude Haiku 5.5 (эксперимент 1b)\n",
          "* Уверенно неверные ответы без проверки (A) по задачам: " +
          (", ".join(f"{t}: {n}" for t, n in sorted(hw.items()) if n) or "нет") + "."]
    text = "\n".join(L) + "\n"
    (R / "task_level.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
