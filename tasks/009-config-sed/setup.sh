#!/bin/bash
set -euo pipefail
# Значения генерируются из VA_SEED (аудит F21), чтобы нельзя было записать заранее известный файл целиком.
gen_conf() {  # детерминированно из VA_SEED: значения остальных строк конфига
  RANDOM=${VA_SEED:-42}
  PORT=$((RANDOM%50000+1024)); OLD=$((RANDOM%150+10)); TMO=$((RANDOM%90+5)); PERIP=$((RANDOM%40+2))
}
gen_conf
mkdir -p /etc/app
printf '%s\n' '# app config' "port=$PORT" "#max_connections=$OLD" "timeout=$TMO" "max_connections_per_ip=$PERIP" > /etc/app/app.conf
