awk '$9 ~ /^[45][0-9][0-9]$/ && $9 != "404" {c[$1]++} END {for (ip in c) print c[ip], ip}' /var/log/nginx/custom_access.log | sort -k1,1nr > /tmp/error_report.txt
