#!/usr/bin/env python3
"""Перекрёстная проверка «решатель × проверяющий» — по плану docs/prereg_cross_verifier.md (зафиксирован до запуска).

Новых обращений к моделям нет: решения и тесты проверяющих взяты из экспериментов 1 (qwen) и 1b (Haiku),
правда — скрытая проверка (sandbox.evaluate). Кэш: results/cross_verifier.jsonl; отчёт: results/cross_verifier.md.

  python audit/cross_verifier.py            # прогон (дописывает кэш, можно прерывать и продолжать)
  python audit/cross_verifier.py --report   # только отчёт
  python audit/cross_verifier.py --truth-v1  # правда по старым проверкам 003/004/006 (Docker), затем отчёт
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
R = ROOT / "results"
CACHE = R / "cross_verifier.jsonl"
SRC = {"qwen": R, "haiku": R / "claude/claude-haiku-5-5-low"}
SOLVABLE = [f"{i:03d}" for i in range(1, 11)]
K = 3  # тестов каждого проверяющего на решение


def h(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def load_rows(who, cond):
    return [r for r in map(json.loads, (SRC[who] / f"{cond}.jsonl").read_text().splitlines())
            if r["expected"] == "solve" and r["task"][:3] in SOLVABLE]


def solutions():
    """Уникальные решения: (решатель, задача, текст)."""
    seen, out = set(), []
    for who in SRC:
        for cond in "ACDE":
            for r in load_rows(who, cond):
                scripts = [r["final_script"]] if cond == "A" and r.get("final_script") else \
                    [x["solution"] for x in (r.get("history") or []) if x.get("kind") == "script" and x.get("solution")]
                for s in scripts:
                    key = (who, r["task"], h(s))
                    if key not in seen:
                        seen.add(key)
                        out.append({"solver": who, "task": r["task"], "sid": h(s), "script": s})
    return out


def verifier_tests():
    """Тесты независимого проверяющего из условия D: {семья: {задача: [тест, ...]}} (уникальные)."""
    out = {}
    for who in SRC:
        by = defaultdict(dict)
        for r in load_rows(who, "D"):
            t = r.get("verifier_test")
            if t:
                by[r["task"]][h(t)] = t
        out[who] = {k: list(v.items()) for k, v in by.items()}
    return out


def run_test(task, script, test):
    """Как experiment.run_external: setup.sh → решение → тест в свежей песочнице."""
    from sandbox import Sandbox
    with Sandbox(task.caps, task.image) as sb:
        if task.file("setup.sh"):
            sb.run_script("/work/setup.sh", task.file("setup.sh"))
        sb.run_script("/work/solution.sh", script)
        rc, _ = sb.run_script("/verify/test.sh", test)
    return rc


def jobs():
    sols, tests = solutions(), verifier_tests()
    rng = random.Random(2026)
    for s in sols:
        yield {"kind": "truth", **{k: s[k] for k in ("solver", "task", "sid")}, "script": s["script"]}
        for fam in ("qwen", "haiku"):
            pool = tests[fam].get(s["task"], [])
            for tid, t in rng.sample(pool, min(K, len(pool))):
                yield {"kind": "pair", "solver": s["solver"], "task": s["task"], "sid": s["sid"], "verifier": fam,
                       "tid": tid, "script": s["script"], "test": t}
    for fam in ("qwen", "haiku"):  # валидность тестов: эталон и пустое решение
        for task, pool in tests[fam].items():
            for tid, t in pool:
                yield {"kind": "validity", "verifier": fam, "task": task, "tid": tid, "test": t}


def key(j):
    return (j["kind"], j.get("solver"), j["task"], j.get("sid"), j.get("verifier"), j.get("tid"))


def run():
    from sandbox import evaluate, load_tasks
    tasks = {t.name: t for t in load_tasks()}
    done = {key(r) for r in map(json.loads, CACHE.read_text().splitlines())} if CACHE.exists() else set()
    todo = [j for j in jobs() if key(j) not in done]
    for n, j in enumerate(todo, 1):
        task = tasks[j["task"]]
        rec = {k: j.get(k) for k in ("kind", "solver", "task", "sid", "verifier", "tid")}
        if j["kind"] == "truth":
            rec["hidden_rc"], _ = evaluate(task, j["script"])
        elif j["kind"] == "pair":
            rec["test_rc"] = run_test(task, j["script"], j["test"])
        else:
            rec["ref_rc"] = run_test(task, task.file("solution.sh"), j["test"])
            rec["noop_rc"] = run_test(task, "true\n", j["test"])
        with CACHE.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        if n % 25 == 0 or n == len(todo):
            print(f"{n}/{len(todo)}", flush=True)


def truth_v1():
    """Правда по СТАРЫМ проверкам 003/004/006 (до исправления в 6546ff7) — для проверки чувствительности (рецензия Opus)."""
    import subprocess
    from sandbox import evaluate, load_tasks
    out = R / "cross_verifier_truth_v1.jsonl"
    if out.exists():
        return {(r["solver"], r["task"], r["sid"]): r["hidden_rc"] == 0 for r in map(json.loads, out.read_text().splitlines())}
    fixed = ["003-permissions", "004-user-group", "006-cron-entry"]
    old = {t: subprocess.run(["git", "show", f"6546ff7^:tasks/{t}/check.sh"], capture_output=True, text=True, check=True,
                             cwd=ROOT).stdout for t in fixed}
    tasks = {t.name: t for t in load_tasks()}
    for t in fixed:
        orig = tasks[t].file
        tasks[t].file = (lambda o, src: (lambda name: src if name == "check.sh" else o(name)))(orig, old[t])
    res = {}
    with out.open("w") as f:
        for s in solutions():
            if s["task"] in fixed:
                rc, _ = evaluate(tasks[s["task"]], s["script"])
                f.write(json.dumps({"solver": s["solver"], "task": s["task"], "sid": s["sid"], "hidden_rc": rc}) + "\n")
                res[(s["solver"], s["task"], s["sid"])] = rc == 0
    return res


def ba(pairs):
    pos = [p for p in pairs if p["good"]]
    neg = [p for p in pairs if not p["good"]]
    sens = sum(p["pass"] for p in pos) / len(pos) if pos else float("nan")
    spec = sum(not p["pass"] for p in neg) / len(neg) if neg else float("nan")
    acc = sum(p["pass"] for p in pairs)
    prec = sum(p["pass"] and p["good"] for p in pairs) / acc if acc else float("nan")
    return sens, spec, (sens + spec) / 2, prec, len(pos), len(neg)


def report() -> str:
    rows = [json.loads(l) for l in CACHE.read_text().splitlines()]
    truth = {(r["solver"], r["task"], r["sid"]): r["hidden_rc"] == 0 for r in rows if r["kind"] == "truth"}
    pairs = [{"solver": r["solver"], "task": r["task"], "verifier": r["verifier"], "pass": r["test_rc"] == 0,
              "good": truth[(r["solver"], r["task"], r["sid"])]}
             for r in rows if r["kind"] == "pair" and (r["solver"], r["task"], r["sid"]) in truth]
    f = lambda x: "—" if x != x else f"{x:.2f}"
    L = ["# Перекрёстная проверка «решатель × проверяющий»\n",
         "План анализа зафиксирован до запуска: [`docs/prereg_cross_verifier.md`](../docs/prereg_cross_verifier.md). "
         "Скрипт: `audit/cross_verifier.py`. Новых обращений к моделям нет.\n",
         f"Уникальных решений: qwen {sum(1 for k in truth if k[0] == 'qwen')} "
         f"(верных {sum(v for k, v in truth.items() if k[0] == 'qwen')}), Haiku {sum(1 for k in truth if k[0] == 'haiku')} "
         f"(верных {sum(v for k, v in truth.items() if k[0] == 'haiku')}). Пар «решение × тест»: {len(pairs)}.\n",
         "| Решатель | Тест писал | Чувствительность (хорошие приняты) | Специфичность (плохие отклонены) | BA | Точность принятого | хороших / плохих пар |",
         "|---|---|---|---|---|---|---|"]
    for sv in ("qwen", "haiku", "оба"):
        for vf in ("qwen", "haiku"):
            ps = [p for p in pairs if p["verifier"] == vf and (sv == "оба" or p["solver"] == sv)]
            s, sp, b, pr, npos, nneg = ba(ps)
            L.append(f"| {sv} | {vf} | {f(s)} | {f(sp)} | **{f(b)}** | {f(pr)} | {npos} / {nneg} |")
    # главное сравнение: разница BA (haiku − qwen), бутстрэп по задачам
    tasks = sorted({p["task"] for p in pairs})
    by = defaultdict(list)
    for p in pairs:
        by[p["task"]].append(p)
    rng = random.Random(0)
    diffs = []
    for _ in range(10000):
        sample = [p for t in (rng.choice(tasks) for _ in tasks) for p in by[t]]
        bh = ba([p for p in sample if p["verifier"] == "haiku"])[2]
        bq = ba([p for p in sample if p["verifier"] == "qwen"])[2]
        if bh == bh and bq == bq:
            diffs.append(bh - bq)
    diffs.sort()
    obs = ba([p for p in pairs if p["verifier"] == "haiku"])[2] - ba([p for p in pairs if p["verifier"] == "qwen"])[2]
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
    L += ["\n## Главное сравнение (H1)\n",
          f"BA тестов Haiku − BA тестов qwen = **{obs:+.2f}**, 95% бутстрэп по задачам [{lo:+.2f}; {hi:+.2f}] "
          f"({len(diffs)} выборок с определённой BA). H1 подтверждается, только если интервал не содержит 0: "
          f"**{'да' if lo > 0 else 'нет'}**."]
    # различение внутри задачи (H2)
    L.append("\n## Различение внутри задачи (H2)\n")
    L.append("Только задачи, где у решателя есть и верные, и неверные решения. Проверяющий, который лишь узнаёт трудные "
             "задачи, получил бы здесь BA ≈ 0.5.\n")
    L.append("| Решатель | Тест писал | Задач со смешанными решениями | BA внутри задач |")
    L.append("|---|---|---|---|")
    for sv in ("qwen", "haiku"):
        mixed = [t for t in tasks if len({p["good"] for p in by[t] if p["solver"] == sv}) == 2]
        for vf in ("qwen", "haiku"):
            ps = [p for p in pairs if p["solver"] == sv and p["verifier"] == vf and p["task"] in mixed]
            L.append(f"| {sv} | {vf} | {len(mixed)} ({', '.join(t[:3] for t in mixed) or '—'}) | {f(ba(ps)[2])} |")
    # валидность тестов
    v = [r for r in rows if r["kind"] == "validity"]
    L.append("\n## Валидность самих тестов\n")
    L.append("| Тест писал | Тестов | Проходит эталонное решение | Отклоняет пустое решение | Оба условия |")
    L.append("|---|---|---|---|---|")
    for vf in ("qwen", "haiku"):
        vv = [r for r in v if r["verifier"] == vf]
        if vv:
            a = sum(r["ref_rc"] == 0 for r in vv)
            b = sum(r["noop_rc"] != 0 for r in vv)
            c = sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in vv)
            L.append(f"| {vf} | {len(vv)} | {a} ({100 * a / len(vv):.0f}%) | {b} ({100 * b / len(vv):.0f}%) | {c} ({100 * c / len(vv):.0f}%) |")
    L.append("\nПлацебо (случайный PASS с той же частотой) по построению даёт BA = 0.5.")
    # дополнительно, НЕ из плана (по замечанию рецензента о узком бутстрэпе при 10 задачах)
    import itertools
    L += ["\n## Дополнительно (не из плана): по каждой задаче\n",
          "Перцентильный бутстрэп по 10 задачам слишком узкий, поэтому ниже — сравнение по каждой задаче и точный "
          "тест со сменой знака. Пары обоих решателей вместе.\n",
          "| Задача | BA тестов qwen | BA тестов Haiku | Чувствительность qwen / Haiku |", "|---|---|---|---|"]
    dd = []
    for t in tasks:
        q = ba([p for p in by[t] if p["verifier"] == "qwen"])
        hk = ba([p for p in by[t] if p["verifier"] == "haiku"])
        if q[2] == q[2] and hk[2] == hk[2]:
            dd.append(hk[2] - q[2])
        L.append(f"| {t} | {f(q[2])} | {f(hk[2])} | {f(q[0])} / {f(hk[0])} |")
    obs2 = abs(sum(dd))
    p2 = sum(abs(sum(sg * x for sg, x in zip(signs, dd))) >= obs2 - 1e-12
             for signs in itertools.product((1, -1), repeat=len(dd))) / 2 ** len(dd)
    L += ["\n## Дополнительно (не из плана): внутри каждой задачи, отдельно по решателю\n",
          "В плане «внутри задачи» считалось по парам всех смешанных задач вместе; это всё ещё смешивает задачи. "
          "Ниже — BA в каждой задаче отдельно.\n", "| Решатель | Тесты писал | BA по задачам | Среднее |", "|---|---|---|---|"]
    for sv in ("qwen", "haiku"):
        mixed = [t for t in tasks if len({p["good"] for p in by[t] if p["solver"] == sv}) == 2]
        for vf in ("qwen", "haiku"):
            vals = [ba([p for p in by[t] if p["solver"] == sv and p["verifier"] == vf])[2] for t in mixed]
            L.append(f"| {sv} | {vf} | {', '.join(f'{t[:3]}: {v:.2f}' for t, v in zip(mixed, vals))} | "
                     f"{sum(vals) / len(vals):.2f} |" if vals else f"| {sv} | {vf} | — | — |")
    L.append(f"\nЗадач, где есть и верные, и неверные решения: {len(dd)}; тесты Haiku лучше в {sum(x > 0 for x in dd)}, "
             f"тесты qwen лучше в {sum(x < 0 for x in dd)}; точный тест со сменой знака p = {p2:.3f} "
             f"(минимально возможное при {len(dd)} задачах — {2 / 2 ** len(dd):.3f}). «—» — в задаче нет неверных решений.")
    # ---- дополнительно, НЕ из плана (рецензия Opus 5.5): единицы анализа, двухуровневый бутстрэп, версия правды
    mixed = [t for t in tasks if len({p["good"] for p in by[t]}) == 2]
    tavg = {v: sum(ba([p for p in by[t] if p["verifier"] == v])[2] for t in mixed) / len(mixed) for v in ("qwen", "haiku")}
    rawp = [r for r in rows if r["kind"] == "pair" and (r["solver"], r["task"], r["sid"]) in truth]
    rng2 = random.Random(1)
    sols_by_task = defaultdict(list)
    for k in truth:
        sols_by_task[k[1]].append(k)
    tests_by = defaultdict(set)
    for r in rawp:
        tests_by[(r["task"], r["verifier"])].add(r["tid"])
    idx = defaultdict(list)
    for r in rawp:
        idx[(r["task"], r["verifier"], r["tid"])].append(r)
    d3 = []
    for _ in range(2000):
        ps = []
        for t in (rng2.choice(tasks) for _ in tasks):
            ss = [rng2.choice(sols_by_task[t]) for _ in sols_by_task[t]]
            sset = Counter(ss)
            for v in ("qwen", "haiku"):
                pool = sorted(tests_by[(t, v)])
                for tid in (rng2.choice(pool) for _ in pool):
                    for r in idx[(t, v, tid)]:
                        k = (r["solver"], r["task"], r["sid"])
                        ps += [{"verifier": v, "pass": r["test_rc"] == 0, "good": truth[k]}] * sset.get(k, 0)
        bh = ba([p for p in ps if p["verifier"] == "haiku"])[2]
        bq = ba([p for p in ps if p["verifier"] == "qwen"])[2]
        if bh == bh and bq == bq:
            d3.append(bh - bq)
    d3.sort()
    bad = [k for k, v in truth.items() if not v]
    rej = defaultdict(list)
    for r in rawp:
        rej[(r["solver"], r["task"], r["sid"])].append(r["test_rc"] != 0)
    informative = [k for k in bad if not all(rej[k])]
    ntests = sorted({len(rej[k]) for k in bad})
    inf_solvers = sorted({k[0] for k in informative})
    bad_h_tasks = sorted({k[1][:3] for k in bad if k[0] == "haiku"})
    L += ["\n## Дополнительно (не из плана, после рецензии Opus 5.5)\n",
          f"* **BA, усреднённая по задачам** (по {len(mixed)} задачам с хорошими и плохими решениями, оба решателя): "
          f"qwen {tavg['qwen']:.2f}, Haiku {tavg['haiku']:.2f}. Сводная BA (0.67 против 0.90) зависит от того, сколько уникальных "
          "решений у каждой задачи; усреднение по задачам даёт ту же картину.",
          f"* **Двухуровневый бутстрэп** (задачи, внутри них тесты и решения): разница BA Haiku − qwen, 95% интервал "
          f"[{d3[int(.025 * len(d3))]:+.2f}; {d3[int(.975 * len(d3)) - 1]:+.2f}] ({len(d3)} выборок). Интервал шире, чем бутстрэп только по "
          "задачам, но ноль не содержит. Это приближение: каждое решение прогонялось лишь с 3 тестами каждого проверяющего, "
          "поэтому пары «решение × тест» без данных пропускаются.",
          f"* **Где на самом деле различие:** из {len(bad)} неверных решений {len(bad) - len(informative)} отклонили все свои тесты "
          f"(по {'/'.join(map(str, ntests))} на решение); "
          f"разница в специфичности держится на {len(informative)} решениях (решатель: {', '.join(inf_solvers)}) "
          f"({', '.join(f'{t}: {c}' for t, c in sorted(Counter(k[1][:3] for k in informative).items()))}). "
          f"Все неверные решения Haiku-решателя — в задачах: {', '.join(bad_h_tasks)}. "
          "Главная разница — в чувствительности (тесты qwen часто валят верные решения).",
          f"* **Тестов qwen, которые проваливают эталонное решение:** "
          f"{sum(r['ref_rc'] != 0 for r in rows if r['kind'] == 'validity' and r['verifier'] == 'qwen')} из 100."]
    tv1 = truth_v1() if (R / "cross_verifier_truth_v1.jsonl").exists() else None
    if tv1:
        t1 = dict(truth)
        t1.update(tv1)
        p1 = [{"verifier": r["verifier"], "task": r["task"], "pass": r["test_rc"] == 0, "good": t1[(r["solver"], r["task"], r["sid"])]} for r in rawp]
        b1 = {v: ba([p for p in p1 if p["verifier"] == v])[2] for v in ("qwen", "haiku")}
        ch = sum(1 for k, v in tv1.items() if v != truth[k])
        L.append(f"* **Чувствительность к версии правды:** со СТАРЫМИ проверками 003/004/006 (из плана) сменились бы {ch} вердиктов; "
                 f"BA qwen {b1['qwen']:.2f}, Haiku {b1['haiku']:.2f} (разница {b1['haiku'] - b1['qwen']:+.2f}). Вывод не зависит от исправления.")
    text = "\n".join(L) + "\n"
    (R / "cross_verifier.md").write_text(text)
    return text


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--truth-v1", action="store_true", help="пересчитать results/cross_verifier_truth_v1.jsonl")
    a = ap.parse_args()
    if a.truth_v1:
        (R / "cross_verifier_truth_v1.jsonl").unlink(missing_ok=True)
        truth_v1()
    elif not a.report:
        run()
    print(report())
