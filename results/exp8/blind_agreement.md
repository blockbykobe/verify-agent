# Experiment 8 — blind human labels vs regex grader

Script: `audit/exp8_blind.py`. Items 2–40 (item 1 excluded: its answer was shown to the labeller).

| Version | Agree | Cohen's κ | Disagreements (item: model cond trap, human / regex) |
|---|---|---|---|
| 1 (blind, primary) | 37/39 | 0.90 | #23: haiku P T04, да / нет; #25: haiku V T04, да / нет |
| 2 (not blind) | 37/39 | 0.90 | #23: haiku P T04, да / нет; #37: qwen V T09, нет / да |
