find /srv/data -type f -printf "%s %p\n" | sort -rn | head -3 | cut -d" " -f2- > /tmp/report.txt
