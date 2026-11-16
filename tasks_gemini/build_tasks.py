#!/usr/bin/env python3
"""Эксперимент 7: задачи от Gemini (tasks_gemini/sysadmin_bench_v2.py, без изменений) → каталоги tasks/101–110.

setup.sh и check.sh просто запускают код Gemini (`setup N` / `verify N`) из временной копии, которую сразу удаляют;
setup.sh удаляет и сам себя, чтобы решение не могло прочитать проверки. task.md — текст задачи Gemini.
solution.sh (эталон) пишет Claude Code — это разрешено планом (docs/prereg_human_tasks.md).
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = HERE / "sysadmin_bench_v2.py"
NAMES = {1: "shared-dir", 2: "lock-contractor", 3: "crlf-symlink", 4: "cron-workhours", 5: "sudoers-nginx",
         6: "truncate-open-log", 7: "duplicates", 8: "backup-retention", 9: "nginx-proxy", 10: "awk-errors"}
CAPS = "CHOWN,DAC_OVERRIDE,FOWNER,FSETID,SETUID,SETGID"
OVERRIDES = HERE / "overrides"  # согласованные с автором замены проверок (если есть): overrides/<N>.py


def wrap(code, action, n, self_delete):
    assert "GEMINI_BENCH_EOF" not in code
    return ("#!/bin/bash\n# Сгенерировано tasks_gemini/build_tasks.py: запускает код Gemini без изменений.\n"
            + ('rm -f "$0"\n' if self_delete else "")
            + 'B=$(mktemp /root/.bench.XXXXXX.py)\ncat > "$B" <<\'GEMINI_BENCH_EOF\'\n' + code
            + "GEMINI_BENCH_EOF\n" + f'python3 "$B" {action} {n}\nrc=$?\nrm -f "$B"\nexit $rc\n')


def main():
    code = SRC.read_text()
    spec = importlib.util.spec_from_file_location("bench", SRC)
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    sols = (HERE / "solutions")
    for n, name in NAMES.items():
        d = ROOT / "tasks" / f"{100 + n}-{name}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "task.md").write_text(bench.TASKS[n]["prompt"] + "\n")
        (d / "setup.sh").write_text(wrap(code, "setup", n, True))
        check_code = (OVERRIDES / f"{n}.py").read_text() if (OVERRIDES / f"{n}.py").exists() else code
        (d / "check.sh").write_text(wrap(check_code, "verify", n, False))
        (d / "solution.sh").write_text((sols / f"{n}.sh").read_text())
        meta = [f"category: gemini-{name}", "expected: solve", f"caps: {CAPS}", "image: verify-agent-exp7",
                "source: gemini (tasks_gemini/sysadmin_bench_v2.py)"]
        if n == 8:
            meta.append("allow_paths: /usr/local/bin/backup-site.sh")
        if n == 6:
            meta.append("keep_setup_procs: yes")
        (d / "meta.yaml").write_text("\n".join(meta) + "\n")
        print("built", d.name)


if __name__ == "__main__":
    sys.exit(main())
