#!/bin/bash
set -euo pipefail
# Имена и расположение файлов генерируются из VA_SEED (аудит F21).
gen_files() {  # детерминированно из VA_SEED: 5 путей и размеры по убыванию
  RANDOM=${VA_SEED:-42}
  DIRS=(/srv/data /srv/data/a /srv/data/b /srv/data/b/c /srv/data/a)
  FILES=(); SIZES=(90000 70000 40000 20000 5000)
  for i in 0 1 2 3 4; do FILES+=("${DIRS[$((RANDOM%5))]}/f${RANDOM}_${i}.bin"); done
}
gen_files
mkdir -p /srv/data/a /srv/data/b/c
for i in 0 1 2 3 4; do head -c ${SIZES[$i]} /dev/zero > "${FILES[$i]}"; done
