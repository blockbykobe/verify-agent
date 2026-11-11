find /srv/www -type d -exec chmod 755 {} +
find /srv/www -type f -exec chmod 644 {} +
find /srv/www -type f -name '*.sh' -exec chmod 755 {} +
