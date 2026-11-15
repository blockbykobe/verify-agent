#!/usr/bin/env python3
"""Дополнительные расчёты по уже записанным данным (без новых запусков моделей) — после независимого разбора
«что спросит опытный исследователь». НЕ из плана: всё это post hoc и описательно.

1. Риск и охват: что было бы, если ответы условия A (без проверки) пропускать через уже записанные тесты проверяющих
   (данные эксперимента 1c: по 3 теста каждого проверяющего на решение). Правила: все 3 / большинство / хотя бы один.
2. Случайный отказ: точная вероятность получить ≤ 5 уверенно неверных при отказе с охватом D внутри каждой задачи.
3. Мощность: какой эффект вообще можно было заметить при наших n (точный тест Фишера, α = 0,05, симуляция).
4. Совпадение ошибок проверяющего и решателя: доля неверных решений, которые тесты приняли (по решателю и проверяющему).
5. Цена проверки: время по условиям; токены и доллары Haiku.

Отчёт: results/extra_analyses.md.
"""
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import sys  # noqa
sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_level import fisher  # noqa: E402  (точный двусторонний тест Фишера, без scipy)

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
HK = R / "claude/claude-haiku-5-5-low"


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def cross():
    truth, pairs = {}, defaultdict(lambda: defaultdict(list))
    for j in load(R / "cross_verifier.jsonl"):
        k = (j["solver"], j["task"], j["sid"])
        if j["kind"] == "truth":
            truth[k] = j["hidden_rc"] == 0
        elif j["kind"] == "pair":
            pairs[k][j["verifier"]].append(j["test_rc"] == 0)
    return truth, pairs


RULES = {"все 3": all, "большинство": lambda t: sum(t) >= 2, "хотя бы 1": any}


def gating(L, truth, pairs):
    L += ["## 1. Риск и охват: ответы без проверки (A), пропущенные через записанные тесты\n",
          "Симуляция по записанным данным, без повторных попыток (в живом D решатель получает отказ и пробует снова). "
          "«Верно» и «уверенно неверно» — по скрытой проверке.\n",
          "| Решатель (условие A) | Фильтр | Правило | Ответов | Верно | Уверенно неверно |", "|---|---|---|---|---|---|"]
    out = {}
    for solver, path in (("qwen", R / "A.jsonl"), ("haiku", HK / "A.jsonl")):
        rows = [r for r in load(path) if r["expected"] == "solve" and r.get("final_script")]
        raw_right = sum(int(r["hidden_rc"]) == 0 for r in rows)
        L.append(f"| {solver} | без фильтра | — | {len(rows)} | {raw_right} | {len(rows) - raw_right} |")
        for ver in ("qwen", "haiku"):
            for rn, rule in RULES.items():
                ans = right = 0
                per_task = defaultdict(lambda: [0, 0])
                for r in rows:
                    k = (solver, r["task"], h(r["final_script"]))
                    if k not in pairs or not pairs[k][ver]:
                        continue
                    if rule(pairs[k][ver]):
                        ans += 1
                        right += truth[k]
                        per_task[r["task"]][0 if truth[k] else 1] += 1
                out[(solver, ver, rn)] = (ans, right, ans - right, per_task)
                L.append(f"| {solver} | тесты {ver} | {rn} | {ans} | {right} | {ans - right} |")
    d = [r for r in load(R / "D.jsonl") if r["expected"] == "solve"]
    d_ans = [r for r in d if r["outcome"] in ("answered", "verified") and r.get("final_script")]
    d_right = sum(int(r["hidden_rc"]) == 0 for r in d_ans)
    L.append(f"| qwen | живой D (тесты qwen, до 3 попыток) | — | {len(d_ans)} | {d_right} | {len(d_ans) - d_right} |")
    a = out[("qwen", "haiku", "большинство")]
    q = out[("qwen", "qwen", "большинство")]
    L += ["", f"* Слабый решатель + сильный проверяющий (эта клетка не была запущена вживую): тесты Haiku по большинству "
          f"оставили {a[1]} верных и {a[2]} уверенно неверных; тесты qwen — {q[1]} и {q[2]}. "
          "Это оценка сверху для живого запуска: здесь нет повторных попыток и нет отказов от трудных задач. "
          "Оговорка о родстве та же, что в 1c: скрытые проверки писались с помощью Claude.",
          "* Чем строже правило, тем меньше ошибок и тем меньше ответов: это кривая «безопасность — полезность», "
          "как в работах по контролю ИИ (Ctrl-Z).\n"]
    return out


def random_refusal(L):
    a = [r for r in load(R / "A.jsonl") if r["expected"] == "solve"]
    d = [r for r in load(R / "D.jsonl") if r["expected"] == "solve"]
    ans = lambda r: r["outcome"] in ("answered", "verified") and r.get("final_script")
    dist = {0: 1.0}
    from math import comb
    tasks = sorted({r["task"] for r in a})
    d_wrong = 0
    for t in tasks:
        at = [r for r in a if r["task"] == t and ans(r)]
        n, K = len(at), sum(int(r["hidden_rc"]) != 0 for r in at)
        k = min(n, sum(1 for r in d if r["task"] == t and ans(r)))
        d_wrong += sum(1 for r in d if r["task"] == t and ans(r) and int(r["hidden_rc"]) != 0)
        if n == 0:
            continue
        pt = {x: comb(K, x) * comb(n - K, k - x) / comb(n, k) for x in range(max(0, k - (n - K)), min(K, k) + 1)}
        new = defaultdict(float)
        for e1, p1 in dist.items():
            for e2, p2 in pt.items():
                new[e1 + e2] += p1 * p2
        dist = new
    p = sum(v for e, v in dist.items() if e <= d_wrong)
    mean = sum(e * v for e, v in dist.items())
    L += ["## 2. Лучше ли D случайного отказа?\n",
          f"Случайный отказ, который внутри каждой задачи оставляет столько же ответов, сколько D, в среднем даёт "
          f"{mean:.1f} уверенно неверных. Точная вероятность получить {d_wrong} или меньше: **p = {p:.2f}**. "
          "То есть внутри задач D от случайного отказа не отличим.\n"]
    return p, d_wrong


def power(L):
    rng = random.Random(2026)

    def pw(p1, p2, n1, n2, sims=2000):
        hit = 0
        for _ in range(sims):
            x1 = sum(rng.random() < p1 for _ in range(n1))
            x2 = sum(rng.random() < p2 for _ in range(n2))
            hit += fisher(x1, n1 - x1, x2, n2 - x2) < 0.05
        return hit / sims

    rows = [("Атаки (эксп. 3): защита 10 против 10 попыток", 0.9, 0.7, 10, 10),
            ("то же, большой эффект", 0.9, 0.3, 10, 10),
            ("Haiku A против C: ошибки 4/50 против 0/50", 0.08, 0.0, 50, 50),
            ("Признания (эксп. 2): 20 против 20, 0,1 → 0,4", 0.1, 0.4, 20, 20),
            ("Признания: 60 против 60, 0,1 → 0,25", 0.1, 0.25, 60, 60)]
    L += ["## 3. Мощность: какой эффект можно было заметить\n",
          "Точный тест Фишера, α = 0,05, 2000 симуляций. Мощность — вероятность заметить эффект, если он есть.\n",
          "| Сравнение | Доля 1 | Доля 2 | n | Мощность |", "|---|---|---|---|---|"]
    res = {}
    for name, p1, p2, n1, n2 in rows:
        res[name] = pw(p1, p2, n1, n2)
        L.append(f"| {name} | {p1} | {p2} | {n1} / {n2} | {res[name]:.0%} |")
    L += ["", "* Значит, «нет значимой разницы» в атаках и в Haiku A против C — это отсутствие доказательств, а не "
          "доказательство отсутствия эффекта.",
          "* Эксперимент 7: точный тест со сменой знака по задачам даёт p < 0,05 только при 5+ смешанных задачах и только "
          "если Haiku лучше во всех (при 5 задачах минимум p = 0,0625 для двустороннего, 0,031 для одностороннего). В 1c "
          "смешанными были 6 из 10 задач, поэтому для эксперимента 7 нужно 10 задач, а не 5.\n"]
    return res


def correlation(L, truth, pairs):
    L += ["## 4. Совпадают ли ошибки проверяющего и решателя\n",
          "Доля неверных решений, которые тест проверяющего ПРИНЯЛ (ложное принятие), по парам «решение × тест».\n",
          "| Решатель | Проверяющий | Неверных пар | Ложно принято |", "|---|---|---|---|"]
    out = {}
    for s in ("qwen", "haiku"):
        for v in ("qwen", "haiku"):
            ps = [p for k, d in pairs.items() if k[0] == s and not truth.get(k, True) for p in d[v]]
            out[(s, v)] = (len(ps), sum(ps))
            L.append(f"| {s} | {v} | {len(ps)} | {sum(ps)} ({sum(ps) / len(ps):.0%}) |" if ps else f"| {s} | {v} | 0 | — |")
    L += ["", "* Тесты qwen ложно принимают неверные решения qwen, но не неверные решения Haiku (они все в одной задаче, 005). "
          "Это намёк на общие слепые пятна у решателя и проверяющего из одной модели (как у Goel et al., 2025), "
          "но данных мало: неверные решения Haiku только в одной задаче.\n"]
    return out


def cost(L):
    L += ["## 5. Цена проверки\n", "| Решатель | Условие | Попыток (задачи 001–015) | Время, мин | Среднее на попытку, с |",
          "|---|---|---|---|---|"]
    for solver, base in (("qwen 7B (CPU)", R), ("Claude Haiku (API)", HK)):
        for c in "ACDE":
            rows = [r for r in load(base / f"{c}.jsonl") if r["run"] <= 5]
            sec = sum(r.get("seconds", 0) for r in rows)
            L.append(f"| {solver} | {c} | {len(rows)} | {sec / 60:.1f} | {sec / len(rows):.0f} |")
    u = load(HK / "usage.jsonl")
    tin, tout = sum(x["input_tokens"] for x in u), sum(x["output_tokens"] for x in u)
    usd = (tin * 0.10 + tout * 0.50) / 1e6
    L += ["", f"* Haiku, все условия эксперимента 1b: {len(u)} вызовов, {tin} входных и {tout} выходных токенов, ≈ ${usd:.2f} "
          "(цены из `experiments/claude_confession.py`). По условиям токены не разделены.",
          "* D в 5–8 раз дольше A и у qwen, и у Haiku: проверяющий пишет тест, затем до трёх попыток. "
          "В абсолютных цифрах у Haiku это секунды на задачу, у qwen 7B на процессоре — около минуты.\n"]


def main():
    truth, pairs = cross()
    L = ["# Дополнительные расчёты (не из плана, по уже записанным данным)\n",
         "Скрипт: `audit/extra_analyses.py`. Новых запусков моделей нет. Всё это post hoc и описательно.\n"]
    gating(L, truth, pairs)
    random_refusal(L)
    power(L)
    correlation(L, truth, pairs)
    cost(L)
    text = "\n".join(L) + "\n"
    (R / "extra_analyses.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
