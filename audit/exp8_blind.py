#!/usr/bin/env python3
"""Эксперимент 8 — согласие слепой ручной разметки автора с regex-оценкой (`noticed`).

Метки — results/exp8/blind_labels.md (версия 1 — слепая, основная; версия 2 — после того, как автор увидел
вердикты regex по №23 и №25, не слепая). №1 исключён: ответ на него был показан разметчику как пример.

  python audit/exp8_blind.py      → печатает и пишет results/exp8/blind_agreement.md
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "results" / "exp8"


def parse(line):
    return {int(n): v == "да" for n, v in re.findall(r"(\d+) (да|нет)", line)}


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main():
    text = (D / "blind_labels.md").read_text()
    v1 = parse(re.search(r"Version 1[^:]*:\*\*(.*)", text).group(1))
    assert sorted(v1) == list(range(1, 41)), "version 1 must label all 40 items"
    v2 = dict(v1)
    exc = re.search(r"Version 2.*?except ((?:#\d+[, ]*(?:and )?)+)= нет", text).group(1)
    v2.update({int(n): False for n in re.findall(r"#(\d+)", exc)})
    assert set(int(n) for n in re.findall(r"#(\d+)", exc)) == {1, 25, 37}
    key = {k["i"]: k for k in json.loads((D / "blind_key.json").read_text())}
    out = ["# Experiment 8 — blind human labels vs regex grader", "",
           "Script: `audit/exp8_blind.py`. Items 2–40 (item 1 excluded: its answer was shown to the labeller).", "",
           "| Version | Agree | Cohen's κ | Disagreements (item: model cond trap, human / regex) |", "|---|---|---|---|"]
    for name, lab in (("1 (blind, primary)", v1), ("2 (not blind)", v2)):
        items = range(2, 41)
        h = [lab[i] for i in items]
        r = [bool(key[i]["noticed"]) for i in items]
        dis = [i for i in items if lab[i] != bool(key[i]["noticed"])]
        desc = "; ".join(f"#{i}: {key[i]['model']} {key[i]['cond']} {key[i]['trap'][:3]}, "
                         f"{'да' if lab[i] else 'нет'} / {'да' if key[i]['noticed'] else 'нет'}" for i in dis)
        out.append(f"| {name} | {sum(x == y for x, y in zip(h, r))}/{len(h)} | {kappa(h, r):.2f} | {desc} |")
    (D / "blind_agreement.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
