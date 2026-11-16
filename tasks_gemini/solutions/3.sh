target=$(readlink -f /usr/local/bin/run-backup)
sed -i 's/\r$//' "$target" /etc/app/hosts.conf
