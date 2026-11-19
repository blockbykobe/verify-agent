#!/bin/bash
# Бережный прогон 8b на видеокарте основного ПК: модели по одной, пачки по 20 эпизодов (один прогон),
# пауза на остывание после каждой пачки, выгрузка модели (keep_alive 0) после каждой модели и при ошибке.
# При любой ошибке — стоп всего (без повторов).
cd ~/verify-agent || exit 1
URL=http://192.168.50.22:11434
LOG=results/exp8b/gpu.log
BATCH_PAUSE=180      # 3 мин после каждой пачки
MODEL_PAUSE=600      # 10 мин между моделями
declare -A TAG=([qwen14b]=qwen2.5-coder:14b [llama8b]=llama3.1:8b [gemma9b]=gemma2:9b)
unload() { curl -s -m 30 "$URL/api/generate" -d "{\"model\":\"$1\",\"keep_alive\":0}" >/dev/null; echo "$(date -u +%FT%TZ) unload $1" >> $LOG; }
first=1
for m in qwen14b llama8b gemma9b; do
  [ $first = 1 ] || { echo "$(date -u +%FT%TZ) cool-down ${MODEL_PAUSE}s before $m" >> $LOG; sleep $MODEL_PAUSE; }
  first=0
  for r in 1 2 3 4 5; do
    if ! curl -s -m 10 "$URL/api/tags" >/dev/null; then
      echo "$(date -u +%FT%TZ) STOP: Ollama on main PC not answering before $m run$r" >> $LOG; exit 3; fi
    echo "$(date -u +%FT%TZ) start $m run$r" >> $LOG
    if ! .venv/bin/python experiments/exp8b_traps.py --model $m --cond P V --runs $r --url $URL >> $LOG 2>&1; then
      echo "$(date -u +%FT%TZ) STOP: error in $m run$r" >> $LOG; unload ${TAG[$m]}; exit 4; fi
    echo "$(date -u +%FT%TZ) done $m run$r; pause ${BATCH_PAUSE}s" >> $LOG
    [ $r = 5 ] || sleep $BATCH_PAUSE
  done
  unload ${TAG[$m]}
done
echo "$(date -u +%FT%TZ) ALL GPU DONE" >> $LOG
