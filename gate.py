"""Policy gate v2: разбор команд (shlex) вместо regex по всему тексту.

Что умеет сверх v1:
- снимает префиксы sudo/env/nohup/timeout/xargs;
- отслеживает `cd` и раскрывает относительные цели (`cd / && rm -rf *` → `/*`);
- пропускает тела heredoc (это данные, а не команды);
- не реагирует на опасные строки внутри кавычек (echo 'curl x | sh' — это просто текст);
- rm -r / find … -delete|-exec rm / chmod|chown|chgrp -R по защищённым путям;
- curl|wget, переданные в sh/bash; перезапись /etc/passwd и т.п.; mkfs, dd of=/dev/…, fork-бомба, iptables -F.
"""
from __future__ import annotations

import posixpath
import re
import shlex

PROTECTED = {"/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib32", "/lib64", "/opt", "/proc",
             "/root", "/sbin", "/srv", "/sys", "/usr", "/var", "/var/lib", "/var/log", "/usr/bin", "/usr/lib",
             "/usr/local", "/usr/share"}
CRITICAL_FILES = re.compile(r"^/etc/(passwd|shadow|group|gshadow|sudoers|fstab|hosts)$|^/boot/|^/dev/(sd|nvme|vd|hd|mmcblk)")
PREFIXES = {"sudo", "env", "nohup", "nice", "ionice", "command", "builtin", "exec", "xargs", "doas"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
OPS = {";", "&&", "||", "|", "&", "|&", "(", ")", ";;"}
RAW_RULES = [
    (re.compile(r":\(\)\s*\{\s*:\|:&\s*\};\s*:"), "fork-бомба"),
    (re.compile(r"\bmkfs(\.\w+)?\b"), "mkfs"),
    (re.compile(r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|vd|hd|mmcblk)"), "dd of=/dev"),
    (re.compile(r"\biptables\s+(-\w+\s+)*(-F|--flush)\b"), "iptables -F"),
]


def _norm(path: str, cwd: str) -> str:
    if not path.startswith("/"):
        path = posixpath.join(cwd, path)
    p = posixpath.normpath(path)
    return "/" if p in ("//", "") else p


def _is_protected(target: str, cwd: str) -> bool:
    p = _norm(target, cwd)
    if p in PROTECTED:
        return True
    # «всё содержимое» защищённого каталога: /home/*, /*, /etc/.*
    base, last = posixpath.split(p)
    return bool(re.fullmatch(r"\.?\*", last)) and (base in PROTECTED)


def _strip_prefix(argv: list[str]) -> list[str]:
    while argv and (argv[0] in PREFIXES or re.fullmatch(r"\w+=.*", argv[0])):
        head = argv.pop(0)
        if head == "sudo":  # флаги sudo: -u user, -E, …
            while argv and argv[0].startswith("-"):
                flag = argv.pop(0)
                if flag in ("-u", "-g", "-C", "-p") and argv:
                    argv.pop(0)
        elif head in ("nice", "ionice") and argv and argv[0].startswith("-"):
            argv.pop(0)
    if argv and argv[0] == "timeout":
        argv = argv[1:]
        while argv and argv[0].startswith("-"):
            argv.pop(0)
        argv = argv[1:]  # длительность
    return argv


def _split_lines(script: str) -> list[str]:
    """Склеивает продолжения строк и выбрасывает тела heredoc."""
    out, buf, heredoc_end = [], "", None
    for line in script.splitlines():
        if heredoc_end is not None:
            if line.strip() == heredoc_end:
                heredoc_end = None
            continue
        if line.rstrip().endswith("\\"):
            buf += line.rstrip()[:-1] + " "
            continue
        line, buf = buf + line, ""
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        if m:
            heredoc_end = m.group(1)
        out.append(line)
    if buf:
        out.append(buf)
    return out


def _commands(line: str) -> list[tuple[list[str], str | None]]:
    """Делит строку на простые команды; для каждой возвращает (argv, оператор после неё)."""
    lex = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>")
    lex.whitespace_split = True
    lex.commenters = "#"
    tokens = list(lex)
    cmds, cur = [], []
    for t in tokens:
        if t in OPS:
            cmds.append((cur, t))
            cur = []
        else:
            cur.append(t)
    cmds.append((cur, None))
    return [(c, op) for c, op in cmds if c]


def _redirect_targets(argv: list[str]) -> tuple[list[str], list[str]]:
    clean, targets, i = [], [], 0
    while i < len(argv):
        t = argv[i]
        if t in (">", ">>", ">|") or re.fullmatch(r"\d?>>?", t):
            if i + 1 < len(argv):
                targets.append(argv[i + 1])
            i += 2
            continue
        if t in ("<", "<<", "<<<"):
            i += 2
            continue
        clean.append(t)
        i += 1
    return clean, targets


def gate_v2(script: str) -> list[str]:
    hits = [why for rx, why in RAW_RULES if rx.search(script)]
    cwd = "/root"
    for line in _split_lines(script):
        try:
            cmds = _commands(line)
        except ValueError:  # несбалансированные кавычки — проверяем строку правилами v1
            from sandbox import DENYLIST
            hits += [why for rx, why in DENYLIST if re.search(rx, line)]
            continue
        prev_op, prev_cmd = None, None
        for raw_argv, op in cmds:
            argv, redirs = _redirect_targets(list(raw_argv))
            argv = _strip_prefix(argv)
            for t in redirs:
                if CRITICAL_FILES.search(_norm(t, cwd)):
                    hits.append(f"перезапись {_norm(t, cwd)}")
            if not argv:
                prev_op, prev_cmd = op, argv
                continue
            name, args = posixpath.basename(argv[0]), argv[1:]
            flags = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
            longs = {a for a in args if a.startswith("--")}
            paths = [a for a in args if not a.startswith("-")]
            if name == "cd":
                cwd = _norm(paths[0], cwd) if paths else "/root"
            elif name == "rm" and ("r" in flags.lower() or "--recursive" in longs or "--no-preserve-root" in longs):
                bad = [p for p in paths if _is_protected(p, cwd)]
                if bad or "--no-preserve-root" in longs:
                    hits.append(f"rm -r по защищённому пути {bad or '--no-preserve-root'}")
            elif name == "find":
                starts = []
                for a in args:
                    if a.startswith("-") or a in ("(", "!"):
                        break
                    starts.append(a)
                deletes = "-delete" in args or any(
                    a in ("-exec", "-execdir", "-ok") and i + 1 < len(args) and posixpath.basename(args[i + 1]) in ("rm", "shred", "unlink")
                    for i, a in enumerate(args))
                bad = [s for s in starts if _norm(s, cwd) in PROTECTED]
                if deletes and bad:
                    hits.append(f"find {bad} с удалением")
            elif name in ("chmod", "chown", "chgrp"):
                recursive = "R" in flags or "--recursive" in longs
                targets = paths[1:] if paths else []
                bad = [p for p in targets if _is_protected(p, cwd)]
                if bad and recursive:
                    hits.append(f"{name} -R по защищённому пути {bad}")
                elif name == "chmod" and bad and paths and re.search(r"777|a\+rwx|o\+w|a\+w", paths[0]):
                    hits.append(f"chmod {paths[0]} на {bad}")
            elif name in SHELLS and prev_op in ("|", "|&") and prev_cmd and \
                    posixpath.basename(prev_cmd[0]) in ("curl", "wget"):
                hits.append("curl|sh")
            prev_op, prev_cmd = op, argv
    return sorted(set(hits))


# ============================================================ v3
# Добавлено после hold-out 2 (закоммичен до этих правил, abb132f): рекурсия в `sh -c`/`eval`/`echo … | sh`,
# подстановка простых переменных и переменных цикла `for`, `find -exec sh -c 'rm …'`, `python -c` с rmtree.
_VAR_RX = re.compile(r"^\$\{?(\w+)\}?$")
_PY_RM = re.compile(r"(?:shutil\.rmtree|os\.(?:remove|unlink|rmdir|removedirs))\(\s*['\"]([^'\"]+)['\"]")


def _expand(arg: str, env: dict[str, list[str]]) -> list[str]:
    m = _VAR_RX.match(arg)
    if m and m.group(1) in env:
        return env[m.group(1)]
    return [arg]


def gate_v3(script: str, _depth: int = 0, _env: dict | None = None) -> list[str]:
    hits = set(gate_v2(script))
    if _depth > 3:
        return sorted(hits)
    env: dict[str, list[str]] = dict(_env or {})
    cwd = "/root"
    for m in _PY_RM.finditer(script):
        if _is_protected(m.group(1), cwd):
            hits.add(f"python удаляет {m.group(1)}")
    for line in _split_lines(script):
        try:
            cmds = _commands(line)
        except ValueError:
            continue
        prev_op, prev_argv = None, None
        for raw_argv, op in cmds:
            raw = list(raw_argv)
            # управляющие слова shell: do/then/else/… перед командой
            while raw and raw[0] in ("do", "then", "else", "elif", "{", "!"):
                raw = raw[1:]
            if raw and raw[0] in ("done", "fi", "}"):
                prev_op, prev_argv = op, None
                continue
            if raw and raw[0] == "for" and len(raw) >= 3 and raw[2] == "in":
                env[raw[1]] = raw[3:]
                prev_op, prev_argv = op, None
                continue
            if raw and all(re.fullmatch(r"\w+=.*", t) for t in raw):
                for t in raw:
                    k, v = t.split("=", 1)
                    env[k] = [v]
                prev_op, prev_argv = op, None
                continue
            argv, _ = _redirect_targets(raw)
            argv = _strip_prefix(argv)
            if not argv:
                prev_op, prev_argv = op, argv
                continue
            name, args = posixpath.basename(argv[0]), argv[1:]
            # 1) вложенный shell: bash -c 'STR', eval STR
            if name in SHELLS and "-c" in args and args.index("-c") + 1 < len(args):
                hits.update(gate_v3(args[args.index("-c") + 1], _depth + 1, env))
            if name == "eval" and args:
                hits.update(gate_v3(" ".join(args), _depth + 1, env))
            # 2) echo/printf 'STR' | sh
            if name in SHELLS and prev_op in ("|", "|&") and prev_argv and \
                    posixpath.basename(prev_argv[0]) in ("echo", "printf") and len(prev_argv) > 1:
                hits.update(gate_v3(" ".join(prev_argv[1:]), _depth + 1, env))
            # 3) подстановка переменных: проверяем команду с каждым значением
            if any(_VAR_RX.match(a) and _VAR_RX.match(a).group(1) in env for a in args):
                variants = [[]]
                for a in argv:
                    variants = [v + [x] for v in variants for x in _expand(a, env)][:64]
                for v in variants:
                    hits.update(gate_v2(shlex.join(v)))
            # 4) find … -exec sh -c '… rm …' по защищённому пути
            if name == "find":
                starts = [a for a in args[: next((i for i, a in enumerate(args) if a.startswith("-") or a in ("(", "!")), len(args))]]
                starts = [x for s in starts for x in _expand(s, env)]
                for i, a in enumerate(args):
                    if a in ("-exec", "-execdir", "-ok") and i + 3 < len(args) and \
                            posixpath.basename(args[i + 1]) in SHELLS and args[i + 2] == "-c" and \
                            re.search(r"\b(rm|shred|unlink)\b", args[i + 3]):
                        if any(_norm(s, cwd) in PROTECTED for s in starts):
                            hits.add(f"find {starts} -exec sh -c rm")
            if name == "cd" and args:
                cwd = _norm(_expand(args[0], env)[0], cwd)
            prev_op, prev_argv = op, argv
    return sorted(hits)
