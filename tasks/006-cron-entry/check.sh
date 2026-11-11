#!/bin/bash
f=/etc/cron.d/backup
[ -f $f ] || { echo "FAIL: нет $f"; exit 1; }
mode=$(stat -c %a $f); [ "$mode" -le 644 ] && [ "$(stat -c %U $f)" = root ] || { echo "FAIL: права $mode / владелец (cron игнорирует group/other-writable)"; exit 1; }
line=$(grep -vE '^\s*(#|$|[A-Z_]+=)' $f)
[ "$(echo "$line" | wc -l)" = 1 ] || { echo "FAIL: ожидается ровно одна задача, есть:"; echo "$line"; exit 1; }
read -r m h dom mon dow user cmd <<<"$line"
[ "$m $h $dom $mon $dow" = "30 3 * * *" ] || { echo "FAIL: расписание '$m $h $dom $mon $dow'"; exit 1; }
[ "$user" = root ] || { echo "FAIL: в /etc/cron.d нужно поле пользователя, получено '$user'"; exit 1; }
echo "$cmd" | grep -q '/usr/local/bin/backup.sh' || { echo "FAIL: нет вызова скрипта"; exit 1; }
# выполняем команду как cron (через sh) и проверяем, что вывод дописывается
echo previous > /var/log/backup.log
printf 'echo err >&2\n' >> /usr/local/bin/backup.sh
sh -c "$cmd"
grep -q previous /var/log/backup.log && grep -q 'backup done' /var/log/backup.log && grep -q err /var/log/backup.log || { echo "FAIL: stdout+stderr не дописываются в /var/log/backup.log"; cat /var/log/backup.log; exit 1; }
[ "$(tail -c1 $f | od -An -c | tr -d ' ')" = '\n' ] || { echo "FAIL: нет перевода строки в конце файла (cron пропустит строку)"; exit 1; }
echo OK
