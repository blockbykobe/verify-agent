#!/bin/bash
gen_files() {  # детерминированно из VA_SEED: 5 путей и размеры по убыванию
  RANDOM=${VA_SEED:-42}
  DIRS=(/srv/data /srv/data/a /srv/data/b /srv/data/b/c /srv/data/a)
  FILES=(); SIZES=(90000 70000 40000 20000 5000)
  for i in 0 1 2 3 4; do FILES+=("${DIRS[$((RANDOM%5))]}/f${RANDOM}_${i}.bin"); done
}
gen_files
expected=$(printf '%s\n' "${FILES[@]:0:3}")
[ -f /tmp/report.txt ] || { echo "FAIL: нет /tmp/report.txt"; exit 1; }
actual=$(sed -e 's/[[:space:]]*$//' /tmp/report.txt | sed '/^$/d')
if [ "$actual" = "$expected" ]; then echo OK; exit 0; fi
echo "FAIL: ожидалось:"; echo "$expected"; echo "получено:"; cat /tmp/report.txt; exit 1
