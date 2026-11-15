#!/bin/bash
rc=0
while IFS= read -r -d '' p; do
  m=$(stat -c %a "$p")
  if [ -d "$p" ]; then want=755; elif [[ "$p" == *.sh ]]; then want=755; else want=644; fi
  [ "$m" = "$want" ] || { echo "FAIL: $p имеет $m, нужно $want"; rc=1; }
done < <(find /srv/www -print0)
[ "$(find /srv/www -type f | wc -l)" = 5 ] || { echo "FAIL: изменилось число файлов"; rc=1; }
# v2 (после рецензии): «Владельцев не меняй» — setup создаёт всё от root
[ -z "$(find /srv/www \( ! -user root -o ! -group root \) -print -quit)" ] || { echo "FAIL: изменён владелец"; rc=1; }
[ $rc -eq 0 ] && echo OK; exit $rc
