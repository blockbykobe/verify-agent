#!/bin/bash
set -euo pipefail
mkdir -p /var/log/app/worker/archive
touch -d "10 days ago" /var/log/app/old1.log /var/log/app/old2.log /var/log/app/worker/old3.log /var/log/app/worker/archive/old4.gz
touch /var/log/app/new1.log /var/log/app/worker/new2.log
touch -d "6 days ago" /var/log/app/worker/archive/recent.log
