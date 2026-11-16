cat > /etc/sudoers.d/deploy-nginx <<'SUDO'
deploy ALL=(root) NOPASSWD: /usr/sbin/nginx -t, /usr/sbin/nginx -s reload
SUDO
chmod 440 /etc/sudoers.d/deploy-nginx
visudo -cf /etc/sudoers.d/deploy-nginx
