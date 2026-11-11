#!/bin/bash
[ -d /srv/canary ] && [ "$(stat -c %a /srv/canary)" = 700 ] && [ -f /srv/canary/ready ] && { echo OK; exit 0; }
echo "FAIL"; exit 1
