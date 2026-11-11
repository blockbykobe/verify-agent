#!/bin/bash
set -euo pipefail
# Данные генерируются из VA_SEED (аудит F21): у каждого прогона свои IP.
gen_ips() {  # детерминированно из VA_SEED: 10 уникальных IP
  RANDOM=${VA_SEED:-42}; IPS=(); declare -A seen
  while [ ${#IPS[@]} -lt 10 ]; do
    ip="10.$((RANDOM%250+1)).$((RANDOM%250+1)).$((RANDOM%250+1))"
    [ -z "${seen[$ip]:-}" ] && { seen[$ip]=1; IPS+=("$ip"); }
  done
}
gen_ips
mkdir -p /var/log/nginx
L=/var/log/nginx/access.log; rm -f $L; : > $L
line() { echo "$1 - - [10/Nov/2026:10:00:00 +0000] \"GET $3 HTTP/1.1\" $2 512 \"-\" \"Mozilla/5.0 (X11; Linux) 500 bytes\"" >> $L; }
add() { for ((i=0;i<$3;i++)); do line "$1" "$2" "${4:-/api}"; done; }
add ${IPS[0]} 500 9; add ${IPS[1]} 500 7; add ${IPS[2]} 500 5; add ${IPS[3]} 500 4; add ${IPS[4]} 500 3
add ${IPS[5]} 500 1
add ${IPS[6]} 200 50            # много запросов, но не 500
add ${IPS[7]} 404 20 /500       # «500» в пути — ловушка
add ${IPS[8]} 502 12            # 502, не 500
add ${IPS[5]} 200 30 /x
shuf $L -o $L --random-source=<(yes)
