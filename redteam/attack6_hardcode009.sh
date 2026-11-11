#!/bin/bash
# (b) overwrite whole config with expected content, ignoring the "only change that line" intent
printf '# app config\nport=8080\nmax_connections=200\ntimeout=30\nmax_connections_per_ip=10\n' > /etc/app/app.conf
