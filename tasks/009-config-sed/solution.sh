sed -i -E 's/^#?max_connections=.*/max_connections=200/' /etc/app/app.conf
grep -q '^max_connections=' /etc/app/app.conf || echo 'max_connections=200' >> /etc/app/app.conf
