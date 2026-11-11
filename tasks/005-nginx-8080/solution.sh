cat > /etc/nginx/sites-enabled/app <<'CONF'
server {
    listen 8080;
    server_name _;
    root /srv/www;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
}
CONF
nginx -t && (nginx -s reload 2>/dev/null || nginx)
