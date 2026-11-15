#!/usr/bin/env python3
"""База знаний для эксперимента 6: справочные страницы Linux (man) этого компьютера → rag/corpus/<cmd>.txt.
Тексты не коммитятся (у страниц свои лицензии и версии); в rag/corpus_manifest.json пишется sha256 каждой
страницы, чтобы было видно, на какой версии документации получены результаты.

  python rag/build_corpus.py
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMANDS = ["find", "chmod", "chown", "useradd", "usermod", "groupadd", "tar", "grep", "sed", "awk", "crontab", "ln",
            "du", "df", "rsync", "ss", "ps", "kill", "tail", "head", "sort", "uniq", "cut", "xargs", "gzip",
            "journalctl", "systemctl", "ip", "curl", "ssh-keygen", "passwd", "chage", "mount", "stat", "touch",
            "mkdir", "rm", "cp", "mv", "logrotate"]


def render(cmd: str) -> str:
    env = os.environ | {"LC_ALL": "C", "LANG": "C", "MANWIDTH": "100", "MAN_KEEP_FORMATTING": ""}
    raw = subprocess.run(["man", "-P", "cat", cmd], capture_output=True, env=env, check=True).stdout
    txt = subprocess.run(["col", "-bx"], input=raw, capture_output=True, check=True).stdout.decode("utf-8", "replace")
    return txt.replace("‐", "-").replace("−", "-")


def main() -> None:
    out = HERE / "corpus"
    out.mkdir(exist_ok=True)
    manifest = {}
    for cmd in COMMANDS:
        txt = render(cmd)
        (out / f"{cmd}.txt").write_text(txt)
        manifest[cmd] = {"sha256": hashlib.sha256(txt.encode()).hexdigest(), "chars": len(txt)}
    (HERE / "corpus_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(f"{len(manifest)} pages, {sum(m['chars'] for m in manifest.values()) // 1000}k chars")


if __name__ == "__main__":
    main()
