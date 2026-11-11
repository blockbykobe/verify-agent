#!/usr/bin/env python3
"""Графики для README из сырых результатов → docs/img/*.png. Запуск: .venv/bin/python plots.py
Цвета: категориальные слоты 1–2 проверенной палитры (синий = qwen, оранжевый = Claude Haiku)."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent
R = ROOT / "results"
OUT = ROOT / "docs/img"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
QWEN, HAIKU = "#2a78d6", "#eb6834"


def rows(path, runs=5):
    return [r for r in map(json.loads, path.read_text().splitlines()) if r["expected"] == "solve" and r["run"] <= runs]


def pct(k, n):
    return 100 * k / n if n else 0


def style(ax, title, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=10)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.set_ylim(0, 105)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9, length=0)


def bars(ax, groups, a, b, labels=("qwen2.5-coder 7B", "Claude Haiku 5.5")):
    import numpy as np
    x = np.arange(len(groups))
    w = 0.36
    for off, vals, col, lab in ((-w / 2 - 0.01, a, QWEN, labels[0]), (w / 2 + 0.01, b, HAIKU, labels[1])):
        bs = ax.bar(x + off, vals, w, color=col, label=lab, edgecolor=SURFACE, linewidth=1)
        for bar, v in zip(bs, vals):  # подписи значений: мало столбцов, текст — цветом текста, не серии
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK2)
    ax.set_xticks(x, groups)


def verification():
    conds = ["A\nno check", "C\nown test", "D\nindependent\nverifier", "E\noracle"]
    q = {c: rows(R / f"{c}.jsonl") for c in "ACDE"}
    h = {c: rows(R / f"claude/claude-haiku-5-5-low/{c}.jsonl") for c in "ACDE"}
    wrong = lambda rs: pct(sum(r["outcome"] in ("answered", "verified") and r["hidden_rc"] != 0 for r in rs), len(rs))
    solved = lambda rs: pct(sum(r["hidden_rc"] == 0 for r in rs), len(rs))
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.9), facecolor=SURFACE)
    bars(axs[0], conds, [wrong(q[c]) for c in "ACDE"], [wrong(h[c]) for c in "ACDE"])
    style(axs[0], "Confidently wrong (claimed done, hidden check FAIL)", "% of solvable tasks")
    bars(axs[1], conds, [solved(q[c]) for c in "ACDE"], [solved(h[c]) for c in "ACDE"])
    style(axs[1], "Solved (hidden check PASS)", "% of solvable tasks")
    axs[0].legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper right")
    fig.text(0.01, 0.01, "50 attempts per bar (5 runs × 10 tasks). Source: results/*.jsonl, results/claude/…", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "verification.png", dpi=160, facecolor=SURFACE)


def confession():
    conf = [json.loads(l) for l in (R / "confession.jsonl").read_text().splitlines()]
    cman = json.loads((R / "confession_manual.json").read_text())
    hk = [json.loads(l) for l in (R / "claude_confession_claude-haiku-5-5-low.jsonl").read_text().splitlines()]
    hman = json.loads((R / "claude_confession_claude-haiku-5-5-low_manual.json").read_text())

    def false_conf(rs, man, wj):
        c = [(i, r) for i, r in enumerate(rs) if not r["control"] and r["valid"] and r["with_journal"] == wj]
        return pct(sum(man.get(str(i), r["label"]) == "confessed" for i, r in c), len(c))

    def ack(path, manpath, wj):
        rs = [json.loads(l) for l in path.read_text().splitlines()]
        man = json.loads(manpath.read_text())
        c = [(i, r) for i, r in enumerate(rs) if r["valid"] and r["with_journal"] == wj]
        lab = lambda i, r: man.get(str(i), "acknowledged" if r["label"] == "confessed" else r["label"])
        return pct(sum(lab(i, r) == "acknowledged" for i, r in c), len(c))

    qx = (R / "confession_qwen_explicit.jsonl", R / "confession_qwen_explicit_manual.json")
    hx = (R / "claude_confession_claude-haiku-5-5-low-explicit.jsonl", R / "claude_confession_claude-haiku-5-5-low-explicit_manual.json")
    groups = ["no journal", "with hash‑chained\njournal"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.9), facecolor=SURFACE)
    bars(axs[0], groups, [false_conf(conf, cman, w) for w in (False, True)], [false_conf(hk, hman, w) for w in (False, True)])
    style(axs[0], "False confession (a human deleted the file)", "% of replies")
    bars(axs[1], groups, [ack(*qx, w) for w in (False, True)], [ack(*hx, w) for w in (False, True)])
    style(axs[1], "Acknowledged its own real deletion", "% of replies")
    axs[1].legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    fig.text(0.01, 0.01, "Left: 60 replies per bar. Right: 29–30 per bar. Manual labels. Source: results/confession*, results/claude_confession*",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "confession.png", dpi=160, facecolor=SURFACE)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    verification()
    confession()
    print("written:", *sorted(p.name for p in OUT.glob("*.png")))
