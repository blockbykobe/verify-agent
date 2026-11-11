#!/bin/bash
set -euo pipefail
rm -f /etc/nginx/sites-enabled/default
mkdir -p /srv/www; echo "verify-agent ok" > /srv/www/index.html
cat > /etc/nginx/sites-enabled/app <<'CONF'
server {
    listen 8080
    server_name _;
    root /srv/www;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
CONF
