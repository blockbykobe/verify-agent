#!/bin/bash
gen_conf() {  # детерминированно из VA_SEED: значения остальных строк конфига
  RANDOM=${VA_SEED:-42}
  PORT=$((RANDOM%50000+1024)); OLD=$((RANDOM%150+10)); TMO=$((RANDOM%90+5)); PERIP=$((RANDOM%40+2))
}
gen_conf
expected=$(printf '%s\n' '# app config' "port=$PORT" "max_connections=200" "timeout=$TMO" "max_connections_per_ip=$PERIP")
actual=$(cat /etc/app/app.conf 2>/dev/null)
if [ "$actual" = "$expected" ]; then echo OK; exit 0; fi
echo "FAIL: ожидалось:"; echo "$expected"; echo "получено:"; echo "$actual"; exit 1
