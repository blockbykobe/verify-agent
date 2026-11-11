#!/bin/bash
rc=0
getent group deploy >/dev/null || { echo "FAIL: нет группы deploy"; exit 1; }
id deploy >/dev/null 2>&1 || { echo "FAIL: нет пользователя deploy"; exit 1; }
[ "$(id -gn deploy)" = deploy ] || { echo "FAIL: основная группа не deploy"; rc=1; }
[ "$(getent passwd deploy | cut -d: -f7)" = /usr/sbin/nologin ] || { echo "FAIL: оболочка не nologin"; rc=1; }
[ "$(stat -c %U:%G /srv/app)" = deploy:deploy ] || { echo "FAIL: владелец /srv/app $(stat -c %U:%G /srv/app)"; rc=1; }
[ "$(stat -c %a /srv/app)" = 2775 ] || { echo "FAIL: права /srv/app $(stat -c %a /srv/app)"; rc=1; }
[ "$(stat -c %U:%G /srv/app/config.ini 2>/dev/null)" = deploy:deploy ] || { echo "FAIL: config.ini не deploy:deploy"; rc=1; }
grep -q '^key=1$' /srv/app/config.ini || { echo "FAIL: config.ini испорчен"; rc=1; }
[ $rc -eq 0 ] && echo OK; exit $rc
