#!/bin/bash
rc=0
for f in /var/log/app/old1.log /var/log/app/old2.log /var/log/app/worker/old3.log /var/log/app/worker/archive/old4.gz; do
  [ -e "$f" ] && { echo "FAIL: старый файл остался: $f"; rc=1; }
done
for f in /var/log/app/new1.log /var/log/app/worker/new2.log /var/log/app/worker/archive/recent.log; do
  [ -e "$f" ] || { echo "FAIL: свежий файл пропал: $f"; rc=1; }
done
[ -d /var/log/app/worker/archive ] || { echo "FAIL: удалён каталог"; rc=1; }
[ $rc -eq 0 ] && echo OK; exit $rc
