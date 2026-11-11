cat > /etc/logrotate.d/app <<'CONF'
/var/log/app/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 root root
}
CONF
chmod 644 /etc/logrotate.d/app
