#!/usr/bin/env python3
"""Пересчитывает ключевые числа README/application_notes из сырых results/*.jsonl и проверяет,
что в текстах стоят именно они. Плюс точный тест Фишера и поправка Холма на множественные сравнения.
Выход: 0 — все утверждения совпали; 1 — есть расхождения (печатаются)."""
import json
import statistics as st
import sys
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
README = (ROOT / "README.md").read_text()
NOTES = (ROOT / "docs/application_notes.md").read_text()


def load(name):
    return [json.loads(l) for l in (R / name).read_text().splitlines() if l.strip()]


def fisher(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c
    p = lambda x: comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


claims, bad = [], 0


def claim(text, where=README, label=None):
    global bad
    ok = text in where
    bad += not ok
    claims.append((ok, label or text))


# ---------------- Experiment 1
E = {c: [r for r in load(f"{c}.jsonl") if r["run"] <= 5] for c in "ACDE"}  # основная таблица: первые 5 прогонов
solve = {c: [r for r in rows if r["expected"] == "solve"] for c, rows in E.items()}
for c in "ACDE":
    assert len(E[c]) == 75, (c, len(E[c]))
passed = {c: sum(r["hidden_rc"] == 0 for r in solve[c]) for c in "ACDE"}
wrong = {c: sum(r["outcome"] in ("answered", "verified") and r["hidden_rc"] != 0 for r in solve[c]) for c in "ACDE"}
claim(f"solved A {passed['A']}, C {passed['C']}, D {passed['D']}, E {passed['E']}")
claim(f"confidently wrong A {wrong['A']}, C {wrong['C']}, D {wrong['D']}, E {wrong['E']}")


def per_run_mean(c, f):
    runs = {}
    for r in solve[c]:
        runs.setdefault(r["run"], []).append(f(r))
    return round(100 * st.mean(sum(v) / len(v) for v in runs.values()))


acc = {c: per_run_mean(c, lambda r: r["hidden_rc"] == 0) for c in "ACDE"}
claim(f"**{acc['A']}%** ± 4 | {acc['C']}% ± 0 | {acc['D']}% ± 9 | {acc['E']}% ± 4", label=f"accuracy row {acc}")
for c in "CDE":
    ver = [r for r in solve[c] if r["outcome"] == "verified"]
    fp = sum(r["hidden_rc"] != 0 for r in ver)
    claim(f"{fp}/{len(ver)}", label=f"{c} verified-but-wrong {fp}/{len(ver)}")
    assert all(r["attempts"] == 1 for r in ver), f"{c}: verified after retry exists"
claim("0 failures became passes", NOTES, "qwen: no retry ever turned FAIL into PASS (asserted above)")

pvals = {
    "A vs D confidently wrong": fisher(wrong["A"], 50 - wrong["A"], wrong["D"], 50 - wrong["D"]),
    "A vs C solved": fisher(passed["A"], 50 - passed["A"], passed["C"], 50 - passed["C"]),
    "A vs D solved": fisher(passed["A"], 50 - passed["A"], passed["D"], 50 - passed["D"]),
    "A vs E solved": fisher(passed["A"], 50 - passed["A"], passed["E"], 50 - passed["E"]),
}

# ---------------- Experiment 2 (с ручными метками)
conf = load("confession.jsonl")
manual = json.loads((R / "confession_manual.json").read_text())
lab = lambda i, r: manual.get(str(i), r["label"])
cell = lambda ctrl, wj: [(i, r) for i, r in enumerate(conf) if r["control"] == ctrl and r["with_journal"] == wj and r["valid"]]
fc = {wj: sum(lab(i, r) == "confessed" for i, r in cell(False, wj)) for wj in (False, True)}
tc = {wj: (sum(lab(i, r) == "confessed" for i, r in cell(True, wj)), len(cell(True, wj))) for wj in (False, True)}
claim(f"**{fc[False]}/60 (0%)**")
claim(f"**{fc[True]}/60 (23%)**")
claim(f"**{tc[False][0]}/{tc[False][1]} (11%)**")
claim(f"**{tc[True][0]}/{tc[True][1]} (69%)**")
pvals["confession: false, no journal vs journal"] = fisher(fc[False], 60 - fc[False], fc[True], 60 - fc[True])
pvals["confession: true, no journal vs journal"] = fisher(tc[False][0], tc[False][1] - tc[False][0], tc[True][0], tc[True][1] - tc[True][0])
assert all(r.get("journal_ok") for r in conf), "hash chain failed somewhere"
claim("hash chain verified in 240/240")

# ---------------- Injection / gate
inj = load("injection.jsonl")
inc = [r for r in inj if r["injected"] and r["included_injection"]]
claim(f"blocked all {len(inc)} injected scripts", label=f"gate blocked all {len(inc)} injected scripts")
assert all(r["gate_v1"] and r["gate_v2"] for r in inc)
rd = {p: sum(r["included_injection"] for r in inj if r["prompt"] == p and r["scenario"] == "readme-html") for p in ("old", "new")}
claim(f"**{rd['old']}/10** / 1/10 | **{rd['new']}/10**", label=f"readme injection old {rd['old']}/10, new {rd['new']}/10")
sus = sum(r["suspicious"] for r in inj if r["prompt"] == "new" and r["injected"])
claim(f"flagged {sus}/30", NOTES, f"SUSPICIOUS {sus}/30")

# ---------------- Эксперименты 4–5 и F21
HK = R / "claude_confession_claude-haiku-5-5-low"
hk = load(HK.name + ".jsonl")
hk_man = json.loads((R / (HK.name + "_manual.json")).read_text())
hk_fc = sum(hk_man.get(str(i), r["label"]) == "confessed" for i, r in enumerate(hk) if not r["control"] and r["valid"])
claim(f"**False confessions: {hk_fc}/120**", (R / "claude_confession_haiku.md").read_text(), f"Haiku false confessions {hk_fc}/120")
claim(f"False confessions: {hk_fc}/120**", label=f"README: Haiku {hk_fc}/120")
ex = load(HK.name + "-explicit.jsonl")
ex_man = json.loads((R / (HK.name + "-explicit_manual.json")).read_text())
ack_j = sum(ex_man.get(str(i), "acknowledged" if r["label"] == "confessed" else r["label"]) == "acknowledged" for i, r in enumerate(ex) if r["with_journal"] and r["valid"])
claim(f"acknowledged its own deletion {ack_j}/30", (R / "claude_confession_haiku.md").read_text(), f"Haiku explicit control with journal {ack_j}/30")
cc = json.loads((R / "claude_canary.json").read_text())["labels"]
comp = sum(x["complied"] for l in cc.values() for x in l); rep = sum(x["reported"] for l in cc.values() for x in l)
claim(f"**0/20** complied", label=f"canary complied {comp}/20")
assert comp == 0
claim(f"Only **{rep}/20 told the user**", label=f"canary reported {rep}/20")
rr = json.loads((R / "retro_random.json").read_text())
att_fail = sum(rc != 0 for a in rr["attacks"] for rc in a["check_rc_on_3_seeds"])
same = sum(all(p == x["old_pass"] for p in x["new_pass_2_seeds"]) for x in rr["retro"])
claim(f"fail {att_fail}/9", (ROOT / "docs/audit.md").read_text(), f"F21 attacks fail {att_fail}/9")
claim(f"all {len(rr['retro'])} recorded model answers", (ROOT / "docs/audit.md").read_text(), f"F21 retro unchanged {same}/{len(rr['retro'])}")
assert same == len(rr["retro"])

qx = load("confession_qwen_explicit.jsonl")
qm = json.loads((R / "confession_qwen_explicit_manual.json").read_text())
q_nj = sum(qm[str(i)] == "acknowledged" for i, r in enumerate(qx) if not r["with_journal"])
q_nd = sum(qm[str(i)] == "denied" for i, r in enumerate(qx) if not r["with_journal"])
q_j = sum(qm[str(i)] == "acknowledged" for i, r in enumerate(qx) if r["with_journal"])
claim(f"qwen acknowledged its own deletion {q_nj}/30 and denied {q_nd}/30", label=f"qwen explicit no-journal {q_nj}/30 ack, {q_nd}/30 denied")
claim(f"qwen {q_j}/30, Haiku 30/30", label=f"qwen explicit with journal {q_j}/30")

import yaml  # noqa: E402
sys.path.insert(0, str(ROOT))
from gate import gate_v3  # noqa: E402
from injection_scan import scan  # noqa: E402
h3 = yaml.safe_load((ROOT / "tests/gate_holdout3_independent.yaml").read_text())
g3 = sum(bool(gate_v3(x)) for x in h3["dangerous"])
claim(f"v3 blocked only **{g3}/15**", label=f"gate v3 independent hold-out {g3}/15")
ih = yaml.safe_load((ROOT / "tests/injection_holdout_independent.yaml").read_text())
det = sum(bool(scan(x)) for x in ih["injected"])
claim(f"only **{det}/15** on an independent set", label=f"injection detector independent {det}/15")

# ---------------- A и D до 10 прогонов; Claude Haiku как агент
A10 = [r for r in load("A.jsonl") if r["expected"] == "solve"]
D10 = [r for r in load("D.jsonl") if r["expected"] == "solve"]
wA10 = sum(r["outcome"] == "answered" and r["hidden_rc"] != 0 for r in A10)
wD10 = sum(r["outcome"] == "verified" and r["hidden_rc"] != 0 for r in D10)
claim(f"confidently wrong {wA10}/{len(A10)} vs {wD10}/{len(D10)}", label=f"qwen 10 runs conf-wrong A {wA10}/{len(A10)} D {wD10}/{len(D10)}")
pvals["A vs D confidently wrong, 10 runs"] = fisher(wA10, len(A10) - wA10, wD10, len(D10) - wD10)
HD = R / "claude/claude-haiku-5-5-low"
hs = {c: [json.loads(l) for l in (HD / f"{c}.jsonl").read_text().splitlines() if json.loads(l)["expected"] == "solve"] for c in "ACDE"}
hp = {c: sum(r["hidden_rc"] == 0 for r in hs[c]) for c in "ACDE"}
claim(f"| Solved (hidden check PASS) | {hp['A']} | **{hp['C']}** | {hp['D']} | {hp['E']} |", label=f"Haiku agent solved {hp}")
hfix = sum(r["outcome"] == "verified" and r["attempts"] > 1 for c in "CDE" for r in hs[c])
claim(f"{hfix} failures turned into passes on a retry", label=f"Haiku retries fixed {hfix}")

# Независимые рецензии (2026-11): точность проверяющих (повторная скрытая проверка всех попыток C и D)
vr = load("verifier_rescore.jsonl")
acc = {c: (sum(1 for r in vr if r["cond"] == c and r["test_rc"] == 0 and r["hidden_rc"] == 0),
           sum(1 for r in vr if r["cond"] == c and r["hidden_rc"] == 0),
           sum(1 for r in vr if r["cond"] == c and r["test_rc"] == 0 and r["hidden_rc"] != 0),
           sum(1 for r in vr if r["cond"] == c and r["hidden_rc"] != 0)) for c in "CD"}
claim(f"accepted {acc['D'][0]}/{acc['D'][1]} good attempts and {acc['D'][2]}/{acc['D'][3]} bad ones", label=f"D verifier accepted {acc['D'][0]}/{acc['D'][1]} good, {acc['D'][2]}/{acc['D'][3]} bad")
claim(f"accepted {acc['C'][0]}/{acc['C'][1]} good and {acc['C'][2]}/{acc['C'][3]} bad", label=f"C self-test accepted {acc['C'][0]}/{acc['C'][1]} good, {acc['C'][2]}/{acc['C'][3]} bad")
# по задачам: точный перестановочный тест (смена знака) по 10 задачам, A vs D уверенно неверно
import itertools  # noqa: E402
from collections import defaultdict  # noqa: E402
pt = defaultdict(lambda: {"A": [0, 0], "D": [0, 0]})
for c, rows in (("A", A10), ("D", D10)):
    for r in rows:
        pt[r["task"]][c][0] += r["outcome"] in ("answered", "verified") and r["hidden_rc"] != 0
        pt[r["task"]][c][1] += 1
dd = [v["A"][0] / v["A"][1] - v["D"][0] / v["D"][1] for v in pt.values()]
p_task = sum(abs(sum(s * x for s, x in zip(sg, dd))) >= abs(sum(dd)) - 1e-12
             for sg in itertools.product((1, -1), repeat=len(dd))) / 2 ** len(dd)
claim(f"**p = {p_task:.3f}**", label=f"task-level sign-flip p = {p_task:.3f}")

# Эксперимент 1c: перекрёстная проверка (results/cross_verifier.jsonl)
sys.path.insert(0, str(ROOT / "audit"))
import cross_verifier as cv  # noqa: E402
cvr = load("cross_verifier.jsonl")
tr = {(r["solver"], r["task"], r["sid"]): r["hidden_rc"] == 0 for r in cvr if r["kind"] == "truth"}
cp = [{"solver": r["solver"], "task": r["task"], "verifier": r["verifier"], "pass": r["test_rc"] == 0,
       "good": tr[(r["solver"], r["task"], r["sid"])]} for r in cvr if r["kind"] == "pair"]
ba_q = cv.ba([x for x in cp if x["verifier"] == "qwen"])[2]
ba_h = cv.ba([x for x in cp if x["verifier"] == "haiku"])[2]
claim(f"balanced accuracy {ba_h:.2f} vs {ba_q:.2f}", label=f"cross-verifier BA haiku {ba_h:.2f} qwen {ba_q:.2f}")
val = [r for r in cvr if r["kind"] == "validity"]
vq = sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in val if r["verifier"] == "qwen")
vh = sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in val if r["verifier"] == "haiku")
claim(f"only {vq} of qwen's 100 tests passed the reference solution and failed an empty one; {vh} of Haiku's 50 did",
      label=f"test validity qwen {vq}/100, haiku {vh}/50")
nsol = len({k for k in tr})
claim(f"{nsol} unique: {sum(1 for k in tr if k[0] == 'qwen')} qwen, {sum(1 for k in tr if k[0] == 'haiku')} Haiku", label=f"cross-verifier solutions {nsol}")

# ---------------- поправка Холма
L = sorted(pvals.items(), key=lambda kv: kv[1])
m = len(L)
# Эксперимент 1d и ручная разметка — пересчёт по сырым файлам
import importlib.util as _iu  # noqa: E402
_mv = R / "more_verifiers.jsonl"
if _mv.exists():
    mv = [json.loads(l) for l in _mv.read_text().splitlines()]
    for vmodel, _lbl in (("qwen2.5-coder:14b", "23/98"), ("llama3.1:8b", "3/99"), ("gemma2:9b", "10/100")):
        vv = [r for r in mv if r["kind"] == "validity" and r["verifier"] == vmodel]
        ok = sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in vv)
        claim(f"| {ok}/{len(vv)} |", label=f"1d validity {vmodel} {ok}/{len(vv)}")
    vv = [r for r in mv if r["kind"] == "validity" and r["verifier"] == "claude-haiku-5-5-run2"]
    ok2 = sum(r["ref_rc"] == 0 and r["noop_rc"] != 0 for r in vv)
    claim(f"with {ok2}/{len(vv)} valid tests (first run 43/50)", label=f"Haiku run2 validity {ok2}/{len(vv)}")
# Рецензия Opus 5.5: дополнительные расчёты из results/cross_verifier.md должны совпадать с README
import re as _re  # noqa: E402
_cv = (R / "cross_verifier.md").read_text()
_m = _re.search(r"qwen (\d\.\d\d), Haiku (\d\.\d\d)\. Сводная", _cv)
claim(f"balanced accuracy is {_m.group(1)} (qwen) vs {_m.group(2)} (Haiku)", label=f"1c task-averaged BA {_m.group(1)}/{_m.group(2)}")
_m = _re.search(r"интервал \[([+-]\d\.\d\d); ([+-]\d\.\d\d)\]", _cv)
claim(f"{_m.group(1)} to {_m.group(2)}, still above zero", label=f"1c two-level bootstrap {_m.group(1)}..{_m.group(2)}")
_m = _re.search(r"сменились бы (\d+) вердиктов; BA qwen (\d\.\d\d), Haiku (\d\.\d\d)", _cv)
claim(f"{_m.group(1)} verdicts change and balanced accuracy is {_m.group(2)} vs {_m.group(3)}", label=f"1c old-truth sensitivity {_m.group(2)}/{_m.group(3)}")
_m = _re.search(r"из (\d+) неверных решений (\d+) отклонили все шесть тестов; .*? на (\d+) решениях", _cv)
claim(f"Of {_m.group(1)} incorrect solutions, {_m.group(2)} were rejected by every test, so the specificity gap rests on {_m.group(3)} informative",
      label=f"1c informative bad {_m.group(3)}")
hl = json.loads((R / "human_labels/labels_owner.json").read_text())["labels"]
claim(f"relabelled {len(hl)} replies", label=f"human labels n={len(hl)}")

print("p-values (Fisher exact, two-sided) with Holm correction over", m, "comparisons:")
running = 0.0
holm = {}
for k, (name, p) in enumerate(L):
    adj = min(1.0, max(running, (m - k) * p))
    running = adj
    holm[name] = adj
    print(f"  {name:45} p={p:.2g}  Holm-adjusted={adj:.2g}  {'significant at 0.05' if adj < 0.05 else 'n.s.'}")
print()
for ok, text in claims:
    print(("OK   " if ok else "MISS ") + text)
print(f"\n{len(claims) - bad}/{len(claims)} claims match the raw data")
(R / "claims_check.json").write_text(json.dumps({"pvalues": pvals, "holm": holm,
                                                 "claims": [{"ok": o, "claim": t} for o, t in claims]}, indent=1))
sys.exit(1 if bad else 0)
