echo '30 3 * * * root /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1' > /etc/cron.d/backup
chmod 644 /etc/cron.d/backup
