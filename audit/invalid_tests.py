#!/usr/bin/env python3
"""Почему тесты проверяющих неисправны? (после разбора «что спросит опытный рецензент», не из плана)

Каждый тест, который ПРОВАЛИЛ эталонное решение в эксперименте 1c, прогоняется заново (setup.sh → solution.sh → тест)
с записью вывода; причина классифицируется по выводу простыми правилами. Тесты, пропустившие пустое решение,
считаются отдельно (они «слишком мягкие»). Кэш: results/invalid_tests.jsonl; отчёт: results/invalid_tests.md.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
R = ROOT / "results"
OUT = R / "invalid_tests.jsonl"

RULES = [  # (категория, регулярное выражение по выводу) — первая подходящая
    ("нет нужной программы в песочнице", r"command not found"),
    ("неверный путь или файл (нет такого файла)", r"No such file or directory|cannot access|cannot stat|does not exist"),
    ("нет прав в песочнице", r"Permission denied|Operation not permitted|must be root|not permitted"),
    ("нужна сеть или служба", r"Could not resolve|Connection refused|Failed to connect|System has not been booted|systemctl|Failed to get D-Bus"),
    ("синтаксис или ошибка в самом тесте", r"syntax error|unexpected|unbound variable|bad substitution|integer expression expected|too many arguments"),
]


def classify(out):
    for name, rx in RULES:
        if re.search(rx, out, re.I):
            return name
    return "проверка не совпала с условием (тихий отказ или своё сообщение)"


def run():
    from cross_verifier import verifier_tests
    from sandbox import Sandbox, load_tasks
    tasks = {t.name: t for t in load_tasks()}
    val = [json.loads(l) for l in (R / "cross_verifier.jsonl").read_text().splitlines()]
    val = {(r["verifier"], r["task"], r["tid"]): r for r in val if r["kind"] == "validity"}
    tests = verifier_tests()
    done = {(r["verifier"], r["task"], r["tid"]) for r in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else set()
    with OUT.open("a") as f:
        for fam in ("qwen", "haiku"):
            for task, pool in tests[fam].items():
                for tid, t in pool:
                    v = val[(fam, task, tid)]
                    if v["ref_rc"] == 0 or (fam, task, tid) in done:
                        continue
                    tk = tasks[task]
                    with Sandbox(tk.caps, tk.image) as sb:
                        if tk.file("setup.sh"):
                            sb.run_script("/work/setup.sh", tk.file("setup.sh"))
                        sb.run_script("/work/solution.sh", tk.file("solution.sh"))
                        rc, out = sb.run_script("/verify/test.sh", t)
                    f.write(json.dumps({"verifier": fam, "task": task, "tid": tid, "rc": rc, "out": out[-2000:],
                                        "test": t}, ensure_ascii=False) + "\n")
                    f.flush()


def report():
    rows = [json.loads(l) for l in OUT.read_text().splitlines()]
    val = [json.loads(l) for l in (R / "cross_verifier.jsonl").read_text().splitlines()]
    val = [r for r in val if r["kind"] == "validity"]
    L = ["# Почему тесты проверяющих неисправны (не из плана)\n",
         "Скрипт: `audit/invalid_tests.py`. Тесты, проваливавшие эталонное решение в эксперименте 1c, прогнаны заново с "
         "записью вывода; причина определена простыми правилами по выводу (грубая классификация, не ручная).\n"]
    for fam in ("qwen", "haiku"):
        vv = [r for r in val if r["verifier"] == fam]
        fr = [r for r in rows if r["verifier"] == fam]
        soft = sum(r["ref_rc"] == 0 and r["noop_rc"] == 0 for r in vv)
        L += [f"## Тесты {fam}: всего {len(vv)}; проваливают эталон {sum(r['ref_rc'] != 0 for r in vv)}; "
              f"пропускают пустое решение (слишком мягкие, эталон проходят) {soft}\n"]
        if not fr:
            continue
        again = sum(r["rc"] != 0 for r in fr)
        L.append(f"При повторном прогоне эталон снова провален в {again} из {len(fr)} (остальное — нестабильность).\n")
        c = Counter(classify(r["out"]) for r in fr if r["rc"] != 0)
        L += ["| Причина | Тестов |", "|---|---|"] + [f"| {k} | {v} |" for k, v in c.most_common()]
        bt = defaultdict(int)
        for r in fr:
            if r["rc"] != 0:
                bt[r["task"][:3]] += 1
        L.append("\nПо задачам: " + ", ".join(f"{t}: {n}" for t, n in sorted(bt.items())) + "\n")
    cf = R / "invalid_tests_coded.json"
    if cf.exists():
        c = json.loads(cf.read_text())
        names = {"A": "проверяет не то, что просили", "B": "перевёрнутая или противоречивая логика",
                 "C": "слишком буквальное совпадение", "D": "тест сам меняет систему", "E": "предположение об окружении "
                 "(нет прав, файла, службы)", "F": "другое (в основном механика: неэкранированный * в grep и т.п.)"}
        L += ["## Ручная кодировка причин (агент Claude, читал тест, вывод, task.md и эталон; check.sh не видел)\n",
              "| Причина | qwen | Haiku |", "|---|---|---|"]
        L += [f"| {k} — {v} | {c['summary']['qwen'].get(k, 0)} | {c['summary']['haiku'].get(k, 0)} |" for k, v in names.items()]
        L += ["", "* Тесты qwen ломаются из-за собственных ошибок логики, а не из-за песочницы: окружение виновато в "
              f"{c['summary']['qwen'].get('E', 0)} из {sum(c['summary']['qwen'].values())}.",
              f"* У Haiku {c['summary']['haiku'].get('E', 0)} из {sum(c['summary']['haiku'].values())} — лишние пробы, "
              "которым не хватает прав в песочнице (все проверки самой задачи в них прошли). То есть исправность тестов "
              "Haiku (43 из 50) скорее занижена, чем завышена.\n"]
    text = "\n".join(L) + "\n"
    (R / "invalid_tests.md").write_text(text)
    print(text)


if __name__ == "__main__":
    if "--report" not in sys.argv:
        run()
    report()
