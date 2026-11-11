#!/bin/bash
set -euo pipefail
mkdir -p "/srv/logs/app one/sub dir" "/srv/logs/it's" /srv/logs/two
old=("/srv/logs/old a.log" "/srv/logs/app one/old b.log" "/srv/logs/app one/sub dir/old c.log" "/srv/logs/it's/quote'd.log" '/srv/logs/two/$HOME.log' "/srv/logs/two/-dash.log" "/srv/logs/two/star*.log")
keep=("/srv/logs/app one/keep old.txt" "/srv/logs/two/data.log.gz" "/srv/logs/new a.log" "/srv/logs/app one/sub dir/new b.log")
for f in "${old[@]}"; do touch -d "10 days ago" -- "$f"; done
touch -d "10 days ago" -- "${keep[0]}" "${keep[1]}"
touch -- "${keep[2]}" "${keep[3]}"
