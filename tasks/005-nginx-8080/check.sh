#!/bin/bash
nginx -t >/dev/null 2>&1 || { echo "FAIL: nginx -t не проходит"; nginx -t; exit 1; }
body=$(curl -s --max-time 5 http://localhost:8080/)
[ "$body" = "verify-agent ok" ] || { echo "FAIL: на 8080 отдаётся: '$body'"; exit 1; }
echo OK
