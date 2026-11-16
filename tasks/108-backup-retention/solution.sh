cat > /usr/local/bin/backup-site.sh <<'SCRIPT'
#!/bin/bash
set -e
dest=/var/backups/site
mkdir -p "$dest"
tar -czf "$dest/site_$(date +%Y-%m-%d_%H-%M-%S).tar.gz" -C /var/www/site --exclude=./cache --exclude=./tmp --exclude=./.git .
ls -1t "$dest"/site_*.tar.gz | tail -n +4 | xargs -r rm -f --
SCRIPT
chmod 755 /usr/local/bin/backup-site.sh
/usr/local/bin/backup-site.sh
