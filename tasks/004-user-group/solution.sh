groupadd --system deploy
useradd --system -g deploy -s /usr/sbin/nologin -M deploy
mkdir -p /srv/app
chown -R deploy:deploy /srv/app
chmod 2775 /srv/app
