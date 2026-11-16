cat > /etc/cron.d/app-cleanup <<'CRON'
*/15 9-18 * * 1-5 root find /var/log/app -type f -mtime +7 -delete; date >> /var/log/cleanup.log
CRON
chown root:root /etc/cron.d/app-cleanup
chmod 644 /etc/cron.d/app-cleanup
