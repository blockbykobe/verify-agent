#!/bin/bash
# Пробы изоляции. Запускается ВНУТРИ песочницы (те же флаги, что в экспериментах). Ничего не ломает на хосте.
r() { printf '%-44s %s\n' "$1" "$2"; }
try() { local name=$1; shift; if out=$("$@" 2>&1); then r "$name" "ALLOWED ${out:0:60}"; else r "$name" "blocked (${out:0:70})"; fi; }
echo "== identity / privileges"
r "id" "$(id)"
r "uid_map (0 0 4294967295 = no userns)" "$(cat /proc/self/uid_map | tr -s ' ')"
r "CapEff" "$(grep CapEff /proc/self/status | awk '{print $2}')"
r "CapBnd" "$(grep CapBnd /proc/self/status | awk '{print $2}')"
r "NoNewPrivs" "$(grep NoNewPrivs /proc/self/status | awk '{print $2}')"
r "Seccomp (2 = filter active)" "$(grep '^Seccomp:' /proc/self/status | awk '{print $2}')"
r "AppArmor profile" "$(cat /proc/self/attr/current 2>/dev/null || echo n/a)"
echo "== docker socket / host paths"
r "docker.sock present" "$(find / -xdev -name 'docker.sock' 2>/dev/null | head -1 || true)"
r "mounts (non-overlay)" "$(grep -v -E '^overlay|proc|sysfs|tmpfs|devpts|mqueue|cgroup|shm' /proc/mounts | awk '{print $2}' | tr '\n' ' ')"
echo "== kernel interfaces"
try "write /proc/sys/kernel/hostname" sh -c 'echo x > /proc/sys/kernel/hostname'
try "write /proc/sysrq-trigger" sh -c 'echo h > /proc/sysrq-trigger'
try "write /sys/kernel/uevent_helper" sh -c 'echo /x > /sys/kernel/uevent_helper'
try "mount tmpfs" mount -t tmpfs none /mnt
try "mount cgroup (CVE-2022-0492 path)" mount -t cgroup -o rdma cgroup /mnt
try "unshare user+mount ns" unshare -Urm true
try "mknod block device" mknod /tmp/sda b 8 0
try "read /dev/mem" head -c1 /dev/mem
r "devices in /dev" "$(ls /dev | tr '\n' ' ')"
try "date -s (CAP_SYS_TIME)" date -s '2001-01-01'
try "chown file to other uid" sh -c 'touch /tmp/o && chown 1000 /tmp/o'
try "setuid binary via chmod u+s" sh -c 'cp /bin/true /tmp/t && chmod u+s /tmp/t && stat -c %A /tmp/t'
try "ptrace (strace absent) /proc/1/mem read" head -c1 /proc/1/mem
echo "== cgroup limits"
r "memory.max" "$(cat /sys/fs/cgroup/memory.max 2>/dev/null)"
r "pids.max" "$(cat /sys/fs/cgroup/pids.max 2>/dev/null)"
r "cpu.max" "$(cat /sys/fs/cgroup/cpu.max 2>/dev/null)"
try "write cgroup memory.max" sh -c 'echo max > /sys/fs/cgroup/memory.max'
echo "== network"
r "interfaces" "$(tail -n +3 /proc/net/dev | cut -d: -f1 | tr -d ' ' | tr '\n' ' ')"
r "IPv6 addrs" "$(cat /proc/net/if_inet6 2>/dev/null | awk '{print $6": "$1}' | tr '\n' ' ')"
r "unix sockets visible" "$(tail -n +2 /proc/net/unix | wc -l)"
try "curl IPv6 [2606:4700:4700::1111]" curl -sS -m 3 -g 'http://[2606:4700:4700::1111]/'
try "curl host gateway 172.17.0.1" curl -sS -m 3 http://172.17.0.1/
try "curl ollama via host.docker.internal" curl -sS -m 3 http://host.docker.internal:11434/
echo "== disk"
r "rootfs size" "$(df -h / | tail -1 | awk '{print $2" total, "$4" free"}')"
try "write 300 MB file" sh -c 'dd if=/dev/zero of=/tmp/big bs=1M count=300 status=none && du -h /tmp/big | cut -f1'
rm -f /tmp/big
r "ulimit -f (file size)" "$(ulimit -f)"
r "kernel" "$(uname -r)"
