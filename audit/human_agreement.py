#!/usr/bin/env python3
"""Слепая ручная разметка признаний человеком (эксперимент 2) и согласие с метками ИИ.

Выборка: results/human_labels/items.json (60 ответов, зерно 2026): 30 ответов с меткой правил «denied», которые раньше
никто не перечитывал, все 14 ложных признаний по ручной разметке ИИ и 16 других ответов из ручной разметки ИИ.
Разметчик видел только вопрос-обвинение и ответ модели (без условия, журнала и правды).
Метки человека: results/human_labels/labels_owner.json. Отчёт: results/human_labels/agreement.md.
"""
import json
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"
CODE = {"confessed": "c", "denied": "d", "unclear": "u"}
NAME = {"c": "признался", "d": "отрицал", "u": "неясно"}


def main():
    items = json.loads((R / "human_labels/items.json").read_text())["items"]
    H = {int(k): v for k, v in json.loads((R / "human_labels/labels_owner.json").read_text())["labels"].items()}
    rows = [json.loads(l) for l in (R / "confession.jsonl").read_text().splitlines()]
    man = json.loads((R / "confession_manual.json").read_text())
    pairs, groups = [], {"правила «отрицал», не перечитывались": [], "ИИ вручную: ложное признание": [],
                         "ИИ вручную: прочие": []}
    for it in items:
        i, r = it["row"], rows[it["row"]]
        ai = CODE[man.get(str(i), r["label"])]
        h = H[it["n"]]
        pairs.append((ai, h))
        g = ("правила «отрицал», не перечитывались" if str(i) not in man else
             "ИИ вручную: ложное признание" if man[str(i)] == "confessed" and not r["control"] else "ИИ вручную: прочие")
        groups[g].append((ai, h, r["control"], r["with_journal"]))
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, ch = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * ch[k] for k in "cdu") / n / n
    kappa = (po - pe) / (1 - pe)
    L = ["# Слепая ручная разметка признаний: человек против ИИ\n",
         "Разметчик — автор проекта (человек); он не видел условия, журнала и правды, но знал гипотезу проекта. "
         "Один разметчик. Скрипт: `audit/human_agreement.py`.\n",
         f"* Все {n} ответов: совпадение {po:.0%}, κ Коэна = **{kappa:.2f}** (умеренное согласие).",
         f"* Из них 30 ответов ИИ перечитывал вручную (сравнение с меткой ИИ), 30 — только с меткой правил.",
         "* Где расходятся: " + ", ".join(f"ИИ «{NAME[a]}» → человек «{NAME[b]}»: {c}" for (a, b), c in Counter(pairs).most_common() if a != b) + ".\n",
         "| Группа | Ответов | Человек: признался / отрицал / неясно | Совпало с ИИ |", "|---|---|---|---|"]
    for g, v in groups.items():
        c = Counter(h for _, h, _, _ in v)
        L.append(f"| {g} | {len(v)} | {c['c']} / {c['d']} / {c['u']} | {sum(a == h for a, h, _, _ in v)} |")
    extra = [(ctrl, wj) for a, h, ctrl, wj in groups["правила «отрицал», не перечитывались"] if h == "c"]
    fc = groups["ИИ вручную: ложное признание"]
    L += ["\nЧто это значит для эксперимента 2:",
          f"* Ложные признания (ИИ: 14/60 с журналом): человек согласился в {sum(h == 'c' for _, h, _, _ in fc)} из {len(fc)}, "
          f"остальные — «неясно».",
          f"* Среди 30 непрочитанных «отрицал» человек нашёл {len(extra)} признания: "
          f"{sum(1 for ctrl, _ in extra if ctrl)} в контроле (агент действительно удалял), "
          f"{sum(1 for ctrl, wj in extra if not ctrl and wj)} — ложное обвинение с журналом, "
          f"{sum(1 for ctrl, wj in extra if not ctrl and not wj)} — ложное обвинение без журнала.",
          "* Из 60 ответов с журналом на ложное обвинение человек видел 25; по его оценке ложных признаний не меньше 15 из 60 "
          "(по ИИ — 14). Без журнала человек не нашёл ни одного признания, но 6 из 11 таких ответов в выборке отметил «неясно»; "
          "67 из 97 непрочитанных ответов «отрицал» человек не смотрел.",
          "* Разметка правилами пропускает частичные и условные признания: из 30 непрочитанных «отрицал» человек счёл "
          "4 признаниями и ещё 9 — неясными."]
    text = "\n".join(L) + "\n"
    (R / "human_labels/agreement.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
