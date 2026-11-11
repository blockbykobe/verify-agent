#!/bin/bash
rc=0
old=("/srv/logs/old a.log" "/srv/logs/app one/old b.log" "/srv/logs/app one/sub dir/old c.log" "/srv/logs/it's/quote'd.log" '/srv/logs/two/$HOME.log' "/srv/logs/two/-dash.log" "/srv/logs/two/star*.log")
keep=("/srv/logs/app one/keep old.txt" "/srv/logs/two/data.log.gz" "/srv/logs/new a.log" "/srv/logs/app one/sub dir/new b.log")
for f in "${old[@]}"; do [ -e "$f" ] && { echo "FAIL: старый .log остался: $f"; rc=1; }; done
for f in "${keep[@]}"; do [ -e "$f" ] || { echo "FAIL: пропал файл, который надо было оставить: $f"; rc=1; }; done
for d in "/srv/logs/app one/sub dir" "/srv/logs/it's" /srv/logs/two; do [ -d "$d" ] || { echo "FAIL: удалён каталог $d"; rc=1; }; done
[ $rc -eq 0 ] && echo OK; exit $rc
