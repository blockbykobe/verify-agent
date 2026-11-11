awk '$9 == 500 {print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -5 | awk '{print $2}' > /tmp/top_ips.txt
