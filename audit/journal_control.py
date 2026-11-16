#!/usr/bin/env python3
"""Эксперимент 2b: нерелевантный журнал как контроль (план: docs/prereg_journal_control.md).

Сравнивает три ветки ложного обвинения на одних и тех же метках правил (confession.classify):
без журнала и с журналом — из results/confession.jsonl; с нерелевантным журналом — results/confession_padding.jsonl.
Вторично — метки после ручного перечтения ИИ (results/confession_manual.json для старых веток,
results/confession_padding_manual.json для новой, если есть). Отчёт: results/journal_control.md.
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from task_level import fisher  # noqa: E402

R = HERE.parent / "results"
LEVELS = ("neutral", "confident", "pressure")


def main():
    old = [(i, json.loads(l)) for i, l in enumerate((R / "confession.jsonl").read_text().splitlines())]
    pad = [json.loads(l) for l in (R / "confession_padding.jsonl").read_text().splitlines()]
    pad = [r for r in pad if r.get("valid")]
    man = json.loads((R / "confession_manual.json").read_text())
    pm_f = R / "confession_padding_manual.json"
    pman = json.loads(pm_f.read_text()) if pm_f.exists() else {}
    arms = {
        "без журнала": [(r, man.get(str(i), r["label"])) for i, r in old if not r["control"] and not r["with_journal"] and r.get("valid")],
        "с журналом": [(r, man.get(str(i), r["label"])) for i, r in old if not r["control"] and r["with_journal"] and r.get("valid")],
        "нерелевантный журнал": [(r, pman.get(str(k), r["label"])) for k, r in enumerate(pad)],
    }
    L = ["# Эксперимент 2b: нерелевантный журнал той же длины (план записан до запуска)\n",
         "План: [`docs/prereg_journal_control.md`](../docs/prereg_journal_control.md). Ложное обвинение, qwen2.5-coder:7b, "
         "температура 0,7. Скрипт: `audit/journal_control.py`.\n",
         "## Метки правил (главные)\n", "| Ветка | n | признался | отрицал | неясно |", "|---|---|---|---|---|"]
    rule = {}
    for a, rows in arms.items():
        c = Counter(r["label"] for r, _ in rows)
        rule[a] = (c["confessed"], len(rows))
        L.append(f"| {a} | {len(rows)} | {c['confessed']} | {c['denied']} | {c['unclear']} |")
    pc, pn = rule["нерелевантный журнал"]
    for name, other in (("H8a: нерелевантный против без журнала", "без журнала"), ("H8b: нерелевантный против с журналом", "с журналом")):
        oc, on = rule[other]
        p = fisher(pc, pn - pc, oc, on - oc)
        L.append(f"\n* **{name}:** {pc}/{pn} против {oc}/{on}, точный тест Фишера p = {p:.3f}")
    L += ["\n## По уровням обвинения (метки правил, описательно)\n", "| Ветка | " + " | ".join(LEVELS) + " |",
          "|---|" + "---|" * len(LEVELS)]
    for a, rows in arms.items():
        L.append(f"| {a} | " + " | ".join(
            f"{sum(r['label'] == 'confessed' for r, _ in rows if r['level'] == lv)}/{sum(r['level'] == lv for r, _ in rows)}"
            for lv in LEVELS) + " |")
    L += ["\n## После ручного перечтения ИИ (вторично)\n", "| Ветка | n | признался | отрицал | неясно |", "|---|---|---|---|---|"]
    for a, rows in arms.items():
        c = Counter(lab for _, lab in rows)
        L.append(f"| {a} | {len(rows)} | {c['confessed']} | {c['denied']} | {c['unclear']} |")
    if not pman:
        L.append("\nОтветы новой ветки ещё не перечитаны вручную: во второй таблице для неё стоят метки правил.")
    else:
        sec = {a: (sum(lab == "confessed" for _, lab in rows), len(rows)) for a, rows in arms.items()}
        pc2, pn2 = sec["нерелевантный журнал"]
        for name, other in (("нерелевантный против без журнала", "без журнала"), ("нерелевантный против с журналом", "с журналом")):
            oc, on = sec[other]
            L.append(f"\n* {name}: {pc2}/{pn2} против {oc}/{on}, p = {fisher(pc2, pn2 - pc2, oc, on - oc):.3f}")
        L += ["\nКак перечитывали новую ветку: все её ответы, которые правила не пометили «отрицал» (32), перемешаны "
              "вслепую с такими же ответами ветки «с журналом» (30) и размечены отдельным агентом Claude, который не знал, "
              "из какой ветки ответ, и не видел журнала. На ветке «с журналом» его метки совпали с прежними метками ИИ "
              "в 28 из 30 (2 прежних «признался» он счёл «неясно»), так что разметка двух веток сопоставима."]
    text = "\n".join(L) + "\n"
    (R / "journal_control.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
