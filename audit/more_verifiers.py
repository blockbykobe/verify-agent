#!/usr/bin/env python3
"""Эксперимент 1d — больше проверяющих (план: docs/prereg_more_verifiers.md, записан до генерации тестов).

1) generate: каждая модель пишет по 10 тестов проверяющего на каждую решаемую задачу — тот же промпт, температура и
   фильтр, что в experiment.write_verifier_test. Модели работают на удалённой Ollama (видеокарта основного ПК):
   запросы строго по одному, после каждой модели — выгрузка из видеопамяти и пауза.
2) score: тесты каждой модели прогоняются на тех же 262 решениях, что в эксперименте 1c (по 3 случайных теста на
   решение, зерно 2026), правда — исправленная скрытая проверка; плюс валидность (эталон / пустое решение).
3) report: results/more_verifiers.md.

  python audit/more_verifiers.py generate --url http://192.168.50.22:11434
  python audit/more_verifiers.py score
  python audit/more_verifiers.py report
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "audit"))
R = ROOT / "results"
GEN = R / "verifiers"
SCORE = R / "more_verifiers.jsonl"
MODELS = ["qwen2.5-coder:7b", "llama3.1:8b", "gemma2:9b", "qwen2.5-coder:14b", "qwen2.5-coder:32b", "claude-haiku-5-5-run2"]
N_TESTS = 10
N_BY_MODEL = {"qwen2.5-coder:32b": 5, "claude-haiku-5-5-run2": 5}  # дополнение к плану: 32B медленная, 5 тестов на задачу
TEMPERATURE = 0.7  # как в experiment.py
PAUSE = 60  # с между моделями — видеокарта остывает


def fname(model):
    return GEN / (model.replace(":", "_").replace("/", "_") + ".jsonl")


def generate(url, only=None):
    from prompts import SYSTEM_VERIFIER
    from sandbox import code_blocks, load_tasks, policy_gate
    tasks = [t for t in load_tasks() if t.expected == "solve"]
    GEN.mkdir(parents=True, exist_ok=True)
    models = [m for m in MODELS if (not only or m in only) and not m.startswith("claude")]
    for mi, model in enumerate(models):
        out = fname(model)
        done = {(r["task"], r["i"]) for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
        for t in tasks:
            for i in range(N_BY_MODEL.get(model, N_TESTS)):
                if (t.name, i) in done:
                    continue
                raw, test = "", None
                for _ in range(2):  # как write_verifier_test: до 2 попыток получить блок bash, прошедший фильтр
                    r = httpx.post(f"{url}/api/chat", timeout=900, json={
                        "model": model, "stream": False, "keep_alive": "5m",
                        "messages": [{"role": "system", "content": SYSTEM_VERIFIER}, {"role": "user", "content": t.text}],
                        "options": {"temperature": TEMPERATURE, "num_predict": 1024}})
                    r.raise_for_status()
                    raw = r.json()["message"]["content"]
                    blocks = [b for lang, b in code_blocks(raw) if lang in ("bash", "sh", "shell", "")]
                    if blocks and not policy_gate(blocks[0]):
                        test = blocks[0]
                        break
                with out.open("a") as f:
                    f.write(json.dumps({"model": model, "task": t.name, "i": i, "test": test, "raw": raw},
                                       ensure_ascii=False) + "\n")
            print(f"{model} {t.name} done", flush=True)
        httpx.post(f"{url}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)  # выгрузить из видеопамяти
        if mi < len(models) - 1:
            print(f"pause {PAUSE}s", flush=True)
            time.sleep(PAUSE)


def generate_claude(max_usd=0.5):
    """Второй прогон Haiku-проверяющего: те же настройки, что в эксперименте 1b (claude_experiment.py, условие D)."""
    import os
    import anthropic
    from claude_confession import PRICES
    from prompts import SYSTEM_VERIFIER
    from sandbox import code_blocks, load_tasks, policy_gate
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY не задан")
    model_id, name = "claude-haiku-5-5", "claude-haiku-5-5-run2"
    client = anthropic.Anthropic()
    pin, pout = PRICES[model_id]
    spent, out = 0.0, fname(name)
    GEN.mkdir(parents=True, exist_ok=True)
    done = {(r["task"], r["i"]) for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
    for t in [t for t in load_tasks() if t.expected == "solve"]:
        for i in range(N_BY_MODEL[name]):
            if (t.name, i) in done:
                continue
            raw, test = "", None
            for _ in range(2):
                if spent >= max_usd:
                    raise SystemExit(f"budget ${max_usd} reached")
                r = client.with_options(timeout=300, max_retries=4).messages.create(
                    model=model_id, max_tokens=8000, system=SYSTEM_VERIFIER,
                    messages=[{"role": "user", "content": t.text}], output_config={"effort": "low"})
                spent += r.usage.input_tokens * pin / 1e6 + r.usage.output_tokens * pout / 1e6
                raw = "".join(b.text for b in r.content if b.type == "text")
                blocks = [b for lang, b in code_blocks(raw) if lang in ("bash", "sh", "shell", "")]
                if blocks and not policy_gate(blocks[0]):
                    test = blocks[0]
                    break
            with out.open("a") as f:
                f.write(json.dumps({"model": name, "task": t.name, "i": i, "test": test, "raw": raw}, ensure_ascii=False) + "\n")
        print(f"{name} {t.name} done, spent ≈ ${spent:.3f}", flush=True)


def tests_of(model):
    by = defaultdict(dict)
    for r in map(json.loads, fname(model).read_text().splitlines()):
        if r["test"]:
            by[r["task"]][hashlib.sha1(r["test"].encode()).hexdigest()[:12]] = r["test"]
    return {k: list(v.items()) for k, v in by.items()}


def score():
    import cross_verifier as cv
    from sandbox import load_tasks
    tasks = {t.name: t for t in load_tasks()}
    sols = cv.solutions()
    done = {(r["kind"], r["verifier"], r["task"], r.get("sid"), r["tid"]) for r in
            map(json.loads, SCORE.read_text().splitlines())} if SCORE.exists() else set()
    for model in [m for m in MODELS if fname(m).exists()]:
        tests = tests_of(model)
        rng = random.Random(2026)
        jobs = []
        for s in sols:
            pool = tests.get(s["task"], [])
            for tid, t in rng.sample(pool, min(3, len(pool))):
                jobs.append(("pair", s, tid, t))
        for task, pool in tests.items():
            for tid, t in pool:
                jobs.append(("validity", {"task": task}, tid, t))
        for n, (kind, s, tid, t) in enumerate(jobs, 1):
            key = (kind, model, s["task"], s.get("sid"), tid)
            if key in done:
                continue
            rec = {"kind": kind, "verifier": model, "task": s["task"], "tid": tid}
            task = tasks[s["task"]]
            if kind == "pair":
                rec |= {"solver": s["solver"], "sid": s["sid"], "test_rc": cv.run_test(task, s["script"], t)}
            else:
                rec |= {"ref_rc": cv.run_test(task, task.file("solution.sh"), t), "noop_rc": cv.run_test(task, "true\n", t)}
            with SCORE.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            if n % 50 == 0:
                print(f"{model} {n}/{len(jobs)}", flush=True)


def report() -> str:
    import cross_verifier as cv
    base = [json.loads(l) for l in (R / "cross_verifier.jsonl").read_text().splitlines()]
    truth = {(r["solver"], r["task"], r["sid"]): r["hidden_rc"] == 0 for r in base if r["kind"] == "truth"}
    new = [json.loads(l) for l in SCORE.read_text().splitlines()] if SCORE.exists() else []
    label = {"qwen": "qwen2.5-coder:7b (Exp. 1, CPU)", "haiku": "Claude Haiku 5.5 (Exp. 1b)"}
    pairs = [{"verifier": label.get(r["verifier"], r["verifier"]), "solver": r["solver"], "task": r["task"],
              "pass": r["test_rc"] == 0, "good": truth[(r["solver"], r["task"], r["sid"])]}
             for r in base + new if r["kind"] == "pair"]
    valid = [r | {"verifier": label.get(r["verifier"], r["verifier"])} for r in base + new if r["kind"] == "validity"]
    order = [label["qwen"]] + [m + " (GPU)" if m == "qwen2.5-coder:7b" else m for m in MODELS] + [label["haiku"]]
    for p in pairs + valid:
        if p["verifier"] == "qwen2.5-coder:7b":
            p["verifier"] = "qwen2.5-coder:7b (GPU)"
    f = lambda x: "—" if x != x else f"{x:.2f}"
    mixed_q = ["003-permissions", "004-user-group", "006-cron-entry", "009-config-sed"]
    tasks_all = sorted({p["task"] for p in pairs})
    mixed_all = [t for t in tasks_all if len({p["good"] for p in pairs if p["task"] == t}) == 2]
    L = ["# Эксперимент 1d — больше проверяющих\n",
         "План: [`docs/prereg_more_verifiers.md`](../docs/prereg_more_verifiers.md). Скрипт: `audit/more_verifiers.py`. "
         "Решения и правда — те же, что в эксперименте 1c.\n",
         "| Проверяющий | Пар | Хорошие приняты | Плохие отклонены | BA (оба решателя) | BA внутри задач, решения qwen (среднее по 003/004/006/009) | Исправных тестов |",
         "|---|---|---|---|---|---|---|"]
    per_task = {}
    for v in order:
        ps = [p for p in pairs if p["verifier"] == v]
        if not ps:
            continue
        s, sp, b, _, _, _ = cv.ba(ps)
        within = [cv.ba([p for p in ps if p["solver"] == "qwen" and p["task"] == t])[2] for t in mixed_q]
        per_task[v] = {t: cv.ba([p for p in ps if p["task"] == t])[2] for t in mixed_all}
        vv = [r for r in valid if r["verifier"] == v]
        ok = sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in vv)
        L.append(f"| {v} | {len(ps)} | {f(s)} | {f(sp)} | **{f(b)}** | {f(sum(within) / len(within))} "
                 f"({', '.join(f(x) for x in within)}) | {ok}/{len(vv)} ({100 * ok / max(1, len(vv)):.0f}%) |")

    def signflip(a, b):
        dd = [per_task[a][t] - per_task[b][t] for t in mixed_all if per_task[a][t] == per_task[a][t] and per_task[b][t] == per_task[b][t]]
        obs = abs(sum(dd))
        p = sum(abs(sum(s * x for s, x in zip(sg, dd))) >= obs - 1e-12 for sg in itertools.product((1, -1), repeat=len(dd))) / 2 ** len(dd)
        return sum(x > 0 for x in dd), sum(x < 0 for x in dd), p
    L.append("\n## H3a: qwen2.5-coder 14B против 7B (по задачам, где есть и хорошие, и плохие решения; оба решателя)\n")
    for ref in (label["qwen"], "qwen2.5-coder:7b (GPU)"):
        if "qwen2.5-coder:14b" in per_task and ref in per_task:
            w, l_, p = signflip("qwen2.5-coder:14b", ref)
            L.append(f"* 14B против {ref}: 14B лучше в {w}, хуже в {l_} задачах из {len(mixed_all)}; точный тест со сменой знака p = {p:.3f}.")
    L += ["\n## Как читать (см. README, эксперимент 1d)\n",
          "* H3a формально выполнено, но перевес в трёх задачах 0.001–0.02 — меньше разницы двух прогонов одной 7B; "
          "все тесты 14B для 003 и 004 — из перегенерированных ответов. Считаем H3a не установленным.",
          "* H3b (исправность тестов 7B: GPU против CPU в пределах ±10 п.п.) выполнено; другие показатели между прогонами различались.",
          "* Компания (описательно): ни одна локальная модель не приблизилась к Haiku; компания, сила и «API против локальной» смешаны.",
          "* Отступление: 29 «мусорных» ответов 14B, 27 перегенерированы (qwen2.5-coder_14b.garbled.json), 2 остались неудачами."]
    text = "\n".join(L) + "\n"
    (R / "more_verifiers.md").write_text(text)
    return text


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["generate", "generate-claude", "score", "report"])
    ap.add_argument("--url", default="http://192.168.50.22:11434")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    if a.step == "generate":
        generate(a.url, a.only)
    elif a.step == "generate-claude":
        sys.path.insert(0, str(ROOT / "experiments"))
        generate_claude()
    elif a.step == "score":
        score()
    print(report())
