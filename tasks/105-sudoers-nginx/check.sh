#!/bin/bash
# Сгенерировано tasks_gemini/build_tasks.py: запускает код Gemini без изменений.
B=$(mktemp /root/.bench.XXXXXX.py)
cat > "$B" <<'GEMINI_BENCH_EOF'
#!/usr/bin/env python3
"""
Ubuntu 24.04 Container Sysadmin Benchmark Runner & JSON Reporter (10 Tasks)
Usage:
    python3 sysadmin_bench.py setup [1..10|all]
    python3 sysadmin_bench.py verify [1..10|all] [--json]
    python3 sysadmin_bench.py reset [1..10|all]
    python3 sysadmin_bench.py prompt [1..10|all] [--json]
"""

import argparse
import grp
import json
import os
import pwd
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Tuple


def run_cmd(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["/bin/bash", "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


TASKS: Dict[int, dict] = {
    1: {
        "title": "Shared directory with SGID and sticky bit",
        "difficulty": "easy",
        "prompt": (
            "Настройте директорию /srv/projects для совместной работы группы devteam. "
            "Участники группы должны иметь полные права на создание и чтение файлов внутри, "
            "но удалять или переименовывать чужие файлы должен иметь право только их владелец или root. "
            "Все новые файлы и подпапки внутри /srv/projects должны автоматически наследовать группу devteam."
        ),
    },
    2: {
        "title": "Lock contractor account and preserve SSH keys",
        "difficulty": "easy",
        "prompt": (
            "Сотрудник contractor переведён в архив. Полностью заблокируйте для него возможность входа в систему "
            "(как по паролю, так и по SSH-ключу): заблокируйте пароль, установите дату истечения срока действия "
            "учётной записи на 1970-01-02 и назначьте ему неинтерактивную оболочку (/usr/sbin/nologin или /bin/false). "
            "При этом сам аккаунт, его домашнюю директорию и файл authorized_keys удалять запрещено."
        ),
    },
    3: {
        "title": "Fix Windows CRLF without breaking symlinks",
        "difficulty": "easy",
        "prompt": (
            "Скрипт /usr/local/bin/run-backup при запуске выдаёт ошибку bad interpreter: No such file or directory, "
            "а конфигурация /etc/app/hosts.conf содержит символы возврата каретки Windows (\\r). "
            "Исправьте окончания строк в целевом скрипте и /etc/app/hosts.conf на формат Unix (LF), "
            "сохранив символические ссылки и права на выполнение."
        ),
    },
    4: {
        "title": "System cron in /etc/cron.d",
        "difficulty": "medium",
        "prompt": (
            "Настройте системное задание в /etc/cron.d/app-cleanup, которое будет запускаться от имени пользователя root "
            "каждые 15 минут в рабочие часы (с 09:00 до 18:59 включительно) с понедельника по пятницу. "
            "Задача должна удалять файлы старше 7 дней в /var/log/app и дописывать время завершения в /var/log/cleanup.log."
        ),
    },
    5: {
        "title": "Granular NOPASSWD sudoers rules",
        "difficulty": "medium",
        "prompt": (
            "Разрешите пользователю deploy запускать через sudo без ввода пароля исключительно две команды: "
            "/usr/sbin/nginx -t и /usr/sbin/nginx -s reload. Конфигурацию разместите в /etc/sudoers.d/deploy-nginx. "
            "Убедитесь, что deploy не может запустить nginx с другими флагами (например, -c или -V) и конфигурация sudoers не содержит синтаксических ошибок."
        ),
    },
    6: {
        "title": "Truncate open log file without breaking file descriptor",
        "difficulty": "medium",
        "prompt": (
            "Файл /var/log/billing/transaction.log разросся до 50 МБ и заполняет диск. Некий фоновый процесс "
            "(его PID записан в /tmp/billing_worker.pid) продолжает непрерывно дописывать в этот файл. "
            "Очистите содержимое файла так, чтобы место на диске освободилось немедленно, а процесс продолжил писать "
            "в этот же файл без перезапуска и без потери файлового дескриптора (inode)."
        ),
    },
    7: {
        "title": "Find duplicate configs with spaces in filenames",
        "difficulty": "medium",
        "prompt": (
            "В директории /etc/app/nodes находятся конфигурационные файлы разных узлов. Найдите все файлы с идентичным содержимым "
            "(по SHA-256 хэшу) и запишите их полные пути в файл /tmp/duplicates.txt (по одному пути на строку, отсортированному по алфавиту). "
            "Уникальные файлы попадать в отчёт не должны."
        ),
    },
    8: {
        "title": "Backup script with exclusions, hidden .env, and N-latest retention",
        "difficulty": "hard",
        "prompt": (
            "Напишите и выполните скрипт /usr/local/bin/backup-site.sh, который создаёт сжатый tar.gz архив директории /var/www/site "
            "в папке /var/backups/site/ с именем site_YYYY-MM-DD_HH-MM-SS.tar.gz. В архив не должны попасть директории cache, tmp и .git, "
            "но скрытый файл .env в корне сайта должен попасть в архив. После создания нового архива скрипт должен удалить старые архивы "
            "в /var/backups/site/, оставив только 3 самых свежих по времени модификации файла (mtime)."
        ),
    },
    9: {
        "title": "Fix Nginx reverse-proxy syntax and trailing slash URI bug",
        "difficulty": "hard",
        "prompt": (
            "В конфигурации /etc/nginx/sites-enabled/api.conf допущено несколько синтаксических и логических ошибок. "
            "Исправьте файл так, чтобы: 1) конфигурация проходила проверку nginx -t; "
            "2) запросы к /v1/users проксировались на бэкенд http://127.0.0.1:9000/v1/users (сохраняя префикс /v1/), а не обрезали его до /users; "
            "3) доступ к /status был закрыт для всех, кроме 127.0.0.1."
        ),
    },
    10: {
        "title": "AWK access.log error report (4xx/5xx excluding 404)",
        "difficulty": "hard",
        "prompt": (
            "Проанализируйте /var/log/nginx/custom_access.log и сформируйте отчёт в /tmp/error_report.txt. "
            "В отчёт должны попасть только запросы, завершившиеся ошибкой клиента или сервера (HTTP-статусы 4xx и 5xx), "
            "за исключением кода 404. Для каждого уникального IP-адреса, совершившего такие запросы, выведите количество ошибочных запросов "
            "и сам IP через пробел (формат: <количество> <IP>), отсортировав список по убыванию количества ошибок."
        ),
    },
}


# --- SETUP & RESET ---
def reset_task(tid: int) -> None:
    cmds = {
        1: "rm -rf /srv/projects; userdel -r alice 2>/dev/null || true; userdel -r bob 2>/dev/null || true; groupdel devteam 2>/dev/null || true",
        2: "userdel -r contractor 2>/dev/null || true",
        3: "rm -f /usr/local/bin/run-backup /etc/app/hosts.conf; rm -rf /opt/scripts; rmdir /etc/app 2>/dev/null || true",
        4: "rm -f /etc/cron.d/app-cleanup /var/log/cleanup.log; rm -rf /var/log/app",
        5: "rm -f /etc/sudoers.d/deploy-nginx; userdel -r deploy 2>/dev/null || true",
        6: "[ -f /tmp/billing_worker.pid ] && kill -9 $(cat /tmp/billing_worker.pid) 2>/dev/null || true; rm -rf /tmp/billing_worker.pid /tmp/billing_worker.sh /tmp/billing_inode.txt /var/log/billing",
        7: "rm -rf /etc/app/nodes /tmp/duplicates.txt; rmdir /etc/app 2>/dev/null || true",
        8: "rm -rf /usr/local/bin/backup-site.sh /var/www/site /var/backups/site",
        9: "rm -f /etc/nginx/sites-enabled/api.conf; [ -f /etc/nginx/sites-available/default ] && ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default || true",
        10: "rm -rf /var/log/nginx/custom_access.log /tmp/error_report.txt",
    }
    run_cmd(cmds[tid])


def setup_task(tid: int) -> None:
    reset_task(tid)
    if tid == 1:
        run_cmd("""
            groupadd -f devteam
            useradd -M -s /bin/bash alice
            useradd -M -s /bin/bash bob
            usermod -aG devteam alice
            usermod -aG devteam bob
            mkdir -p /srv/projects
            touch /srv/projects/readme.txt
            chown root:root /srv/projects && chmod 755 /srv/projects
        """)
    elif tid == 2:
        run_cmd("""
            useradd -m -s /bin/bash contractor
            echo "contractor:TempPass123!" | chpasswd
            mkdir -p /home/contractor/.ssh
            echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl test" > /home/contractor/.ssh/authorized_keys
            chown -R contractor:contractor /home/contractor/.ssh
            chmod 700 /home/contractor/.ssh && chmod 600 /home/contractor/.ssh/authorized_keys
        """)
    elif tid == 3:
        Path("/etc/app").mkdir(parents=True, exist_ok=True)
        Path("/opt/scripts").mkdir(parents=True, exist_ok=True)
        Path("/etc/app/hosts.conf").write_bytes(
            b"127.0.0.1\tlocalhost\r\n10.10.5.15\tdb-master.internal\r\n"
        )
        run_sh = Path("/opt/scripts/run.sh")
        run_sh.write_bytes(b"#!/bin/bash\r\necho 'Backup started'\r\n")
        run_sh.chmod(0o755)
        link = Path("/usr/local/bin/run-backup")
        link.unlink(missing_ok=True)
        link.symlink_to("/opt/scripts/run.sh")
    elif tid == 4:
        Path("/var/log/app").mkdir(parents=True, exist_ok=True)
    elif tid == 5:
        run_cmd("useradd -m -s /bin/bash deploy")
    elif tid == 6:
        log_dir = Path("/var/log/billing")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "transaction.log"
        # Создаём 50 МБ без null-байтов в аргументах subprocess
        with open(log_file, "wb") as f:
            f.write(b"A" * (50 * 1024 * 1024))
        Path("/tmp/billing_inode.txt").write_text(str(log_file.stat().st_ino))

        worker_sh = Path("/tmp/billing_worker.sh")
        worker_sh.write_text(
            "#!/bin/bash\n"
            "exec >> /var/log/billing/transaction.log 2>/dev/null < /dev/null\n"
            "while true; do\n"
            "  echo \"$(date -Is) TX_OK\"\n"
            "  sleep 1\n"
            "done\n"
        )
        worker_sh.chmod(0o755)
        # Запускаем полностью отвязанным от pipe-дескрипторов Python
        proc = subprocess.Popen(
            ["/bin/bash", "/tmp/billing_worker.sh"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        Path("/tmp/billing_worker.pid").write_text(str(proc.pid))
    elif tid == 7:
        for d in ("node 1", "node 2", "node 3"):
            Path(f"/etc/app/nodes/{d}").mkdir(parents=True, exist_ok=True)
        Path("/etc/app/nodes/node 1/config main.ini").write_text("server_id=101\n")
        Path("/etc/app/nodes/node 2/config backup.ini").write_text("server_id=101\n")
        Path("/etc/app/nodes/node 3/config main.ini").write_text("server_id=102\n")
    elif tid == 8:
        run_cmd("""
            mkdir -p /var/www/site/{public,cache,tmp,.git} /var/backups/site
            echo "index" > /var/www/site/public/index.html
            echo "secret" > /var/www/site/.env
            echo "trash" > /var/www/site/cache/data.bin
            echo "temp" > /var/www/site/tmp/sess_1
            echo "gitobj" > /var/www/site/.git/HEAD
            # Выставляем согласованный порядок: 01 самый старый и по имени, и по mtime; 04 самый свежий
            touch -d "4 days ago" /var/backups/site/site_2026-01-01_00-00-00.tar.gz
            touch -d "3 days ago" /var/backups/site/site_2026-01-02_00-00-00.tar.gz
            touch -d "2 days ago" /var/backups/site/site_2026-01-03_00-00-00.tar.gz
            touch -d "1 day ago"  /var/backups/site/site_2026-01-04_00-00-00.tar.gz
        """)
    elif tid == 9:
        # Убираем default-конфиг со слушающим [::]:80, чтобы nginx -t не падал в контейнерах без IPv6
        Path("/etc/nginx/sites-enabled/default").unlink(missing_ok=True)
        Path("/etc/nginx/sites-enabled").mkdir(parents=True, exist_ok=True)
        Path("/var/www/html").mkdir(parents=True, exist_ok=True)
        Path("/etc/nginx/sites-enabled/api.conf").write_text(
            "server {\n"
            "    listen 8080;\n"
            "    server_name api.local;\n\n"
            "    location /v1/ {\n"
            "        proxy_pass http://127.0.0.1:9000/\n"
            "        proxy_set_header Host $host;\n"
            "        client_max_body_size 50m\n"
            "    }\n\n"
            "    location /status {\n"
            "        stub_status on;\n"
            "        allow 127.0.0.1;\n"
            "        deny all\n"
            "    }\n"
            "}\n"
        )
    elif tid == 10:
        Path("/var/log/nginx").mkdir(parents=True, exist_ok=True)
        Path("/var/log/nginx/custom_access.log").write_text(
            '192.168.1.10 - - [16/Nov/2026:10:00:01 +0000] "GET /api/data HTTP/1.1" 200 1024 "-" "Mozilla/5.0"\n'
            '192.168.1.10 - - [16/Nov/2026:10:00:02 +0000] "POST /api/login HTTP/1.1" 401 512 "-" "curl/8.5"\n'
            '10.0.0.5 - - [16/Nov/2026:10:00:03 +0000] "GET /admin HTTP/1.1" 403 256 "-" "Mozilla/5.0 (EvilBot)"\n'
            '10.0.0.5 - - [16/Nov/2026:10:00:04 +0000] "GET /admin HTTP/1.1" 403 256 "-" "Mozilla/5.0 (EvilBot)"\n'
            '10.0.0.5 - - [16/Nov/2026:10:00:05 +0000] "GET /index.html HTTP/1.1" 200 4096 "-" "Mozilla/5.0"\n'
            '172.16.0.8 - - [16/Nov/2026:10:00:06 +0000] "GET /api/items HTTP/1.1" 500 128 "-" "Python-urllib/3.12"\n'
            '172.16.0.8 - - [16/Nov/2026:10:00:07 +0000] "GET /api/items HTTP/1.1" 502 128 "-" "Python-urllib/3.12"\n'
            '192.168.1.10 - - [16/Nov/2026:10:00:08 +0000] "GET /missing HTTP/1.1" 404 128 "-" "curl/8.5"\n'
        )


# --- VERIFIERS ---
def verify_1() -> Tuple[bool, str]:
    p = Path("/srv/projects")
    if not p.is_dir():
        return False, "/srv/projects missing"
    st = p.stat()
    mode = oct(st.st_mode)[-4:]
    gname = grp.getgrgid(st.st_gid).gr_name
    if mode not in ("3770", "3775") or gname != "devteam":
        return False, f"Expected mode 3770/3775 & group devteam, got {mode} & {gname}"
    test_f = p / ".py_test_alice"
    test_f.unlink(missing_ok=True)
    run_cmd("su - alice -c 'touch /srv/projects/.py_test_alice'")
    if not test_f.exists():
        return False, "alice cannot write to /srv/projects"
    fgname = grp.getgrgid(test_f.stat().st_gid).gr_name
    if fgname != "devteam":
        test_f.unlink(missing_ok=True)
        return False, f"SGID failed: inherited group {fgname}"
    rc, _, _ = run_cmd("su - bob -c 'rm -f /srv/projects/.py_test_alice'")
    test_f.unlink(missing_ok=True)
    if rc == 0:
        return False, "Sticky bit failed: bob deleted alice's file"
    return True, "OK"


def verify_2() -> Tuple[bool, str]:
    try:
        pw = pwd.getpwnam("contractor")
    except KeyError:
        return False, "User contractor was deleted"
    if pw.pw_shell not in ("/usr/sbin/nologin", "/bin/false"):
        return False, f"Invalid shell: {pw.pw_shell} (expected /usr/sbin/nologin or /bin/false)"
    _, shadow_pw, _ = run_cmd("grep '^contractor:' /etc/shadow | cut -d: -f2")
    if not shadow_pw.startswith(("!", "*")):
        return False, "Password not locked in /etc/shadow"
    _, chage_out, _ = run_cmd("chage -l contractor | grep 'Account expires'")
    if "Jan 02, 1970" not in chage_out:
        return False, f"Expiration mismatch: {chage_out}"
    if not Path("/home/contractor/.ssh/authorized_keys").is_file():
        return False, "authorized_keys missing"
    return True, "OK"


def verify_3() -> Tuple[bool, str]:
    for fp in ("/etc/app/hosts.conf", "/opt/scripts/run.sh"):
        p = Path(fp)
        if not p.is_file():
            return False, f"File missing: {fp}"
        if b"\r" in p.read_bytes():
            return False, f"CRLF still present in {fp}"
    if not Path("/usr/local/bin/run-backup").is_symlink():
        return False, "/usr/local/bin/run-backup is no longer a symlink"
    rc, out, err = run_cmd("/usr/local/bin/run-backup")
    if rc != 0 or out != "Backup started":
        return False, f"Execution failed: rc={rc}, out={out}, err={err}"
    return True, "OK"


def verify_4() -> Tuple[bool, str]:
    f = Path("/etc/cron.d/app-cleanup")
    if not f.is_file():
        return False, "/etc/cron.d/app-cleanup missing"
    st = f.stat()
    if oct(st.st_mode)[-3:] != "644" or st.st_uid != 0:
        return False, "File permissions/owner must be 644 root"

    lines = [
        ln.strip()
        for ln in f.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#") and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", ln.strip())
    ]
    if not lines:
        return False, "No active cron job line found in /etc/cron.d/app-cleanup"

    job = lines[0]
    parts = job.split(None, 6)
    if len(parts) < 7:
        return False, "Cron entry must have 5 schedule fields + user (root) + command"

    minute, hour, dom, mon, dow, user, cmd = parts
    valid_minutes = {"*/15", "0,15,30,45", "0-59/15", "0-45/15"}
    valid_hours = {"9-18", "09-18", "9,10,11,12,13,14,15,16,17,18"}
    valid_dows = {"1-5", "mon-fri", "MON-FRI", "Mon-Fri", "1,2,3,4,5"}

    if minute not in valid_minutes or hour not in valid_hours or dom != "*" or mon != "*" or dow not in valid_dows:
        return False, f"Invalid schedule fields: '{minute} {hour} {dom} {mon} {dow}'"
    if user != "root":
        return False, f"Expected user 'root', got '{user}'"
    if re.search(r"date[^#]*[^\\]%", cmd):
        return False, "Unescaped '%' in date command inside crontab"

    # Поведенческая проверка: создаём старый и свежий файлы, запускаем команду из cron
    app_dir = Path("/var/log/app")
    app_dir.mkdir(parents=True, exist_ok=True)
    old_f = app_dir / "old_test.log"
    new_f = app_dir / "new_test.log"
    old_f.write_text("old")
    new_f.write_text("new")
    ten_days_ago = time.time() - 10 * 86400
    os.utime(old_f, (ten_days_ago, ten_days_ago))

    # Заменяем экранированный \% на % как это делает сам демон cron перед передачей в /bin/sh
    shell_cmd = cmd.replace(r"\%", "%")
    rc, _, err = run_cmd(shell_cmd)
    if rc != 0:
        return False, f"Cron command failed when executed: {err}"
    if old_f.exists():
        return False, "Cron command did not delete files older than 7 days in /var/log/app"
    if not new_f.exists():
        return False, "Cron command deleted recent files (< 7 days old)"
    new_f.unlink(missing_ok=True)

    clog = Path("/var/log/cleanup.log")
    if not clog.is_file() or clog.stat().st_size == 0:
        return False, "/var/log/cleanup.log was not created or is empty"
    return True, "OK"


def verify_5() -> Tuple[bool, str]:
    f = Path("/etc/sudoers.d/deploy-nginx")
    if not f.is_file():
        return False, "/etc/sudoers.d/deploy-nginx missing"
    mode = oct(f.stat().st_mode)[-3:]
    if mode not in ("440", "400"):
        return False, f"Invalid permissions {mode} (expected 440 or 400)"
    rc, _, _ = run_cmd("visudo -cf /etc/sudoers.d/deploy-nginx")
    if rc != 0:
        return False, "visudo check failed"
    # ИЗМЕНЕНО (согласовать с автором): песочница запрещает setuid (no-new-privileges), поэтому sudo от имени
    # deploy не работает вообще. root спрашивает у sudo то же самое: «sudo -l -U deploy [команда]».
    _, slist, _ = run_cmd("sudo -l -U deploy")
    if "/usr/sbin/nginx -t" not in slist or "/usr/sbin/nginx -s reload" not in slist:
        return False, "Required NOPASSWD commands not found in sudo -l"
    rc_bad, _, _ = run_cmd("sudo -l -U deploy /usr/sbin/nginx -V")
    rc_bad2, _, _ = run_cmd("sudo -l -U deploy /usr/sbin/nginx -c /tmp/x.conf")
    if rc_bad == 0 or rc_bad2 == 0:
        return False, "Privilege escalation risk: arbitrary nginx flags allowed"
    return True, "OK"


def verify_6() -> Tuple[bool, str]:
    logf = Path("/var/log/billing/transaction.log")
    pidf = Path("/tmp/billing_worker.pid")
    inof = Path("/tmp/billing_inode.txt")
    if not logf.is_file():
        return False, "Log file missing"
    sz = logf.stat().st_size
    if sz >= 1024 * 1024:
        return False, f"Log file was not truncated (size={sz} bytes, expected < 1MB)"
    if inof.is_file():
        orig_ino = int(inof.read_text().strip())
        if logf.stat().st_ino != orig_ino:
            return False, f"Inode changed ({orig_ino} -> {logf.stat().st_ino}); file was recreated instead of truncated in-place"
    if not pidf.is_file():
        return False, "PID file missing"
    pid = pidf.read_text().strip()
    rc, _, _ = run_cmd(f"kill -0 {pid}")
    if rc != 0:
        return False, "Worker process died or restarted"
    rc_fd, _, _ = run_cmd(f"ls -l /proc/{pid}/fd | grep -q '/var/log/billing/transaction.log$'")
    if rc_fd != 0:
        return False, "Open FD lost or marked (deleted)"
    return True, "OK"


def verify_7() -> Tuple[bool, str]:
    rep = Path("/tmp/duplicates.txt")
    if not rep.is_file():
        return False, "/tmp/duplicates.txt missing"
    lines = [line for line in rep.read_text().splitlines() if line.strip()]
    expected = [
        "/etc/app/nodes/node 1/config main.ini",
        "/etc/app/nodes/node 2/config backup.ini",
    ]
    if lines != expected:
        return False, f"Expected {expected}, got {lines}"
    return True, "OK"


def verify_8() -> Tuple[bool, str]:
    script = Path("/usr/local/bin/backup-site.sh")
    if not script.is_file() or not os.access(script, os.X_OK):
        return False, "Backup script missing or not executable"
    archives = sorted(
        Path("/var/backups/site").glob("site_*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if len(archives) != 3:
        return False, f"Expected 3 backups retained, found {len(archives)}"
    names = {a.name for a in archives}
    # Должны удалиться 01 и 02, а остаться 03, 04 и новый созданный архив
    if "site_2026-01-01_00-00-00.tar.gz" in names or "site_2026-01-02_00-00-00.tar.gz" in names:
        return False, f"Oldest archives were not rotated out; remaining: {sorted(names)}"
    if "site_2026-01-03_00-00-00.tar.gz" not in names or "site_2026-01-04_00-00-00.tar.gz" not in names:
        return False, f"Recent existing archives were wrongly deleted; remaining: {sorted(names)}"

    rc, listing, _ = run_cmd(f"tar -tzf '{archives[0]}'")
    if rc != 0:
        return False, "Failed to read latest tar.gz archive"
    if ".env" not in listing or "public/index.html" not in listing:
        return False, "Missing .env or public/index.html in archive"
    for bad in ("cache/", "tmp/", ".git/"):
        if bad in listing:
            return False, f"Excluded path {bad} found in archive"
    return True, "OK"


def verify_9() -> Tuple[bool, str]:
    rc, _, err = run_cmd("nginx -t")
    if rc != 0:
        return False, f"nginx -t failed: {err}"
    conf = Path("/etc/nginx/sites-enabled/api.conf").read_text()

    # Допускаем оба варианта proxy_pass, сохраняющие префикс /v1/
    if not re.search(r"proxy_pass\s+http://127\.0\.0\.1:9000(/v1/)?\s*;", conf):
        return False, "proxy_pass must be 'http://127.0.0.1:9000;' or 'http://127.0.0.1:9000/v1/;' to preserve /v1/"

    m_status = re.search(r"location\s+/status\s*\{([^}]*)\}", conf, re.DOTALL)
    if not m_status:
        return False, "location /status block missing"
    status_body = m_status.group(1)
    pos_allow = status_body.find("allow 127.0.0.1;")
    pos_deny = status_body.find("deny all;")
    if pos_allow == -1 or pos_deny == -1:
        return False, "location /status must contain both 'allow 127.0.0.1;' and 'deny all;'"
    if pos_allow > pos_deny:
        return False, "In location /status, 'allow 127.0.0.1;' must appear before 'deny all;'"

    return True, "OK"


def verify_10() -> Tuple[bool, str]:
    rep = Path("/tmp/error_report.txt")
    if not rep.is_file():
        return False, "/tmp/error_report.txt missing"
    lines = [line.strip() for line in rep.read_text().splitlines() if line.strip()]
    if len(lines) != 3:
        return False, f"Expected 3 lines, got {len(lines)}"
    if set(lines) != {"2 10.0.0.5", "2 172.16.0.8", "1 192.168.1.10"}:
        return False, f"Unexpected report entries: {lines}"
    if lines[-1] != "1 192.168.1.10":
        return False, f"Not sorted descending: {lines}"
    return True, "OK"


VERIFIERS: Dict[int, Callable[[], Tuple[bool, str]]] = {
    1: verify_1,
    2: verify_2,
    3: verify_3,
    4: verify_4,
    5: verify_5,
    6: verify_6,
    7: verify_7,
    8: verify_8,
    9: verify_9,
    10: verify_10,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sysadmin Benchmark Harness")
    parser.add_argument("action", choices=["setup", "verify", "reset", "prompt"])
    parser.add_argument("target", nargs="?", default="all", help="Task ID (1..10) or 'all'")
    parser.add_argument("--json", action="store_true", help="Output verification results as JSON")
    args = parser.parse_args()

    if args.target == "all":
        tids = list(range(1, 11))
    elif args.target.isdigit() and 1 <= int(args.target) <= 10:
        tids = [int(args.target)]
    else:
        print("Error: target must be 1..10 or 'all'", file=sys.stderr)
        sys.exit(2)

    if args.action == "prompt":
        if args.json:
            print(json.dumps({t: TASKS[t] for t in tids}, ensure_ascii=False, indent=2))
        else:
            for t in tids:
                print(f"=== Task {t} [{TASKS[t]['difficulty']}]: {TASKS[t]['title']} ===")
                print(TASKS[t]["prompt"] + "\n")
        return

    if args.action == "setup":
        for t in tids:
            setup_task(t)
        print(f"Setup completed for task(s): {tids}")
    elif args.action == "reset":
        for t in tids:
            reset_task(t)
        print(f"Reset completed for task(s): {tids}")
    elif args.action == "verify":
        results = []
        passed = 0
        for t in tids:
            ok, msg = VERIFIERS[t]()
            if ok:
                passed += 1
            results.append({
                "task_id": t,
                "title": TASKS[t]["title"],
                "difficulty": TASKS[t]["difficulty"],
                "passed": ok,
                "message": msg,
            })
        if args.json:
            print(json.dumps({"passed": passed, "total": len(tids), "results": results}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                status = "PASS" if r["passed"] else "FAIL"
                print(f"[{status}] Task {r['task_id']} ({r['difficulty']}): {r['message']}")
            print(f"Summary: {passed}/{len(tids)} passed")
        sys.exit(0 if passed == len(tids) else 1)


if __name__ == "__main__":
    main()
GEMINI_BENCH_EOF
python3 "$B" verify 5
rc=$?
rm -f "$B"
exit $rc
