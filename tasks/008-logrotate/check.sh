#!/bin/bash
f=/etc/logrotate.d/app
[ -f $f ] || { echo "FAIL: нет $f"; exit 1; }
logrotate -d $f > /tmp/lr-debug 2>&1 || { echo "FAIL: logrotate -d ругается:"; tail -5 /tmp/lr-debug; exit 1; }
grep -qi 'error' /tmp/lr-debug && { echo "FAIL: ошибки в конфиге:"; grep -i error /tmp/lr-debug; exit 1; }
for kw in daily 'rotate[[:space:]]+7' compress missingok notifempty 'create[[:space:]]+0?640[[:space:]]+root[[:space:]]+root'; do
  grep -Eq "^[[:space:]]*$kw\b" $f || { echo "FAIL: нет директивы $kw"; exit 1; }
done
grep -Eq '^[[:space:]]*delaycompress' $f && { echo "FAIL: delaycompress запрещён"; exit 1; }
logrotate -f -s /tmp/lr-state $f >/dev/null 2>&1 || { echo "FAIL: принудительная ротация упала"; exit 1; }
[ -f /var/log/app/app.log.1.gz ] || { echo "FAIL: нет app.log.1.gz после ротации"; ls -l /var/log/app; exit 1; }
[ "$(stat -c '%a %U %G' /var/log/app/app.log)" = "640 root root" ] || { echo "FAIL: новый app.log: $(stat -c '%a %U %G' /var/log/app/app.log)"; exit 1; }
ls /var/log/app | grep -q 'empty.log.1' && { echo "FAIL: пустой файл ротирован"; exit 1; }
echo OK
