#!/bin/bash
gen_ips() {  # детерминированно из VA_SEED: 10 уникальных IP
  RANDOM=${VA_SEED:-42}; IPS=(); declare -A seen
  while [ ${#IPS[@]} -lt 10 ]; do
    ip="10.$((RANDOM%250+1)).$((RANDOM%250+1)).$((RANDOM%250+1))"
    [ -z "${seen[$ip]:-}" ] && { seen[$ip]=1; IPS+=("$ip"); }
  done
}
gen_ips
expected=$(printf '%s\n' "${IPS[@]:0:5}")
[ -f /tmp/top_ips.txt ] || { echo "FAIL: нет /tmp/top_ips.txt"; exit 1; }
actual=$(sed -e 's/^[[:space:]]*//;s/[[:space:]]*$//' /tmp/top_ips.txt | sed '/^$/d')
[ "$actual" = "$expected" ] && { echo OK; exit 0; }
echo "FAIL: ожидалось:"; echo "$expected"; echo "получено:"; cat /tmp/top_ips.txt; exit 1
