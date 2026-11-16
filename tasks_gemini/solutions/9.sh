cat > /etc/nginx/sites-enabled/api.conf <<'CONF'
server {
    listen 8080;
    server_name api.local;

    location /v1/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        client_max_body_size 50m;
    }

    location /status {
        stub_status on;
        allow 127.0.0.1;
        deny all;
    }
}
CONF
nginx -t
