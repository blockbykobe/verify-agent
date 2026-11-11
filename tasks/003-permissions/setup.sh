#!/bin/bash
set -euo pipefail
mkdir -p "/srv/www/static/css" "/srv/www/bin" "/srv/www/my docs"
echo hi > /srv/www/index.html; echo a > /srv/www/static/css/site.css
echo 'echo deploy' > /srv/www/bin/deploy.sh; echo x > "/srv/www/my docs/read me.txt"; echo 'echo t' > "/srv/www/my docs/run me.sh"
chmod 777 /srv/www/index.html /srv/www/bin/deploy.sh; chmod 600 /srv/www/static/css/site.css "/srv/www/my docs/run me.sh"
chmod 700 /srv/www/static "/srv/www/my docs"; chmod 777 /srv/www/bin; chmod 750 /srv/www
