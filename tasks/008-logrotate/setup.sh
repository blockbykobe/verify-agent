#!/bin/bash
set -euo pipefail
mkdir -p /var/log/app; echo "hello" > /var/log/app/app.log; : > /var/log/app/empty.log
