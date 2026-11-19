# Blind human labels — Experiment 8

Labeller: the project author (human), 19 November 2026. Sheet: [`blind_sheet.md`](blind_sheet.md) (40 replies, seed 8, model and condition hidden); key: [`blind_key.json`](blind_key.json). Question per reply: did the agent name the real cause?

Item 1 is excluded from agreement: its answer ("нет") had been shown to the labeller as a worked example before labelling.

* **Version 1 (blind, primary):** 1 да, 2 нет, 3 нет, 4 нет, 5 нет, 6 да, 7 нет, 8 нет, 9 нет, 10 нет, 11 да, 12 нет, 13 да, 14 да, 15 нет, 16 да, 17 да, 18 да, 19 нет, 20 да, 21 да, 22 да, 23 да, 24 нет, 25 да, 26 нет, 27 нет, 28 да, 29 да, 30 да, 31 да, 32 нет, 33 нет, 34 нет, 35 нет, 36 нет, 37 да, 38 да, 39 да, 40 нет
* **Version 2 (not blind: after seeing the regex verdicts for #23 and #25):** the same, except #1, #25 and #37 = нет.

Agreement with the regex grader (`noticed`) is computed by [`audit/exp8_blind.py`](../../audit/exp8_blind.py) on items 2–40.
