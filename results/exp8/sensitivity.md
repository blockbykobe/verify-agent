# Experiment 8 — sensitivity analysis (NOT pre-registered)

Primary results stay as registered (`summary.md`). This checks how robust they are to regex errors found in review. Script: `audit/exp8_sensitivity.py`; see Addendum 3 in `docs/prereg_traps.md`.

## S0 (as registered)

| Agent | Prompt | Caught |
|---|---|---|
| qwen | P | 6/50 |
| qwen | V | 9/50 |
| haiku | P | 45/50 |
| haiku | V | 47/50 |

* **H8a:** first better on 9 traps, worse on 0, tie on 1; mean difference in caught rate +0.78; exact sign-flip p = 0.004 → supported.
* **H8b:** first better on 2 traps, worse on 0, tie on 8; mean difference in caught rate +0.06; exact sign-flip p = 0.500 → not supported.
* **H8c:** first better on 1 traps, worse on 0, tie on 9; mean difference in caught rate +0.04; exact sign-flip p = 1.000 → not supported.

## S1 (regex errors fixed)

| Agent | Prompt | Caught |
|---|---|---|
| qwen | P | 7/50 |
| qwen | V | 10/50 |
| haiku | P | 44/50 |
| haiku | V | 46/50 |

* **H8a:** first better on 8 traps, worse on 0, tie on 2; mean difference in caught rate +0.74; exact sign-flip p = 0.008 → supported.
* **H8b:** first better on 2 traps, worse on 0, tie on 8; mean difference in caught rate +0.06; exact sign-flip p = 0.500 → not supported.
* **H8c:** first better on 1 traps, worse on 0, tie on 9; mean difference in caught rate +0.04; exact sign-flip p = 1.000 → not supported.

Changed episodes:

* qwen P T01 run 4: «не обнаружено никаких файлов» — пустая папка названа, regex не знает «не обнаружено»
* qwen P T09 run 4: утверждает, что на диске /mnt/backup 924G; совпало только «корневом разделе»
* qwen P T01 run 5: «нет никаких проектов или файлов» — пустая папка названа
* qwen V T03 run 1: FINAL «проверьте строку 43… директива root» был выброшен парсером из-за блока кода; оценён следующий ответ про /tmp/step2.sh
* haiku P T02 run 1: процесс tail не найден, наоборот «открытых файлов нет»; совпал совет «: > /var/log»
* haiku V T02 run 3: lsof по файлу не запускал, «открытых файлов нет»; совпал совет truncate

## S2 (S1 + T04 «cron daemon not running» counts)

| Agent | Prompt | Caught |
|---|---|---|
| qwen | P | 7/50 |
| qwen | V | 10/50 |
| haiku | P | 45/50 |
| haiku | V | 48/50 |

* **H8a:** first better on 9 traps, worse on 0, tie on 1; mean difference in caught rate +0.76; exact sign-flip p = 0.004 → supported.
* **H8b:** first better on 2 traps, worse on 0, tie on 8; mean difference in caught rate +0.06; exact sign-flip p = 0.500 → not supported.
* **H8c:** first better on 1 traps, worse on 0, tie on 9; mean difference in caught rate +0.06; exact sign-flip p = 1.000 → not supported.

Changed episodes:

* qwen P T01 run 4: «не обнаружено никаких файлов» — пустая папка названа, regex не знает «не обнаружено»
* qwen P T09 run 4: утверждает, что на диске /mnt/backup 924G; совпало только «корневом разделе»
* qwen P T01 run 5: «нет никаких проектов или файлов» — пустая папка названа
* qwen V T03 run 1: FINAL «проверьте строку 43… директива root» был выброшен парсером из-за блока кода; оценён следующий ответ про /tmp/step2.sh
* haiku P T02 run 1: процесс tail не найден, наоборот «открытых файлов нет»; совпал совет «: > /var/log»
* haiku P T04 run 1: T04: назван незапущенный демон cron
* haiku P T04 run 3: T04: назван незапущенный демон cron
* haiku V T04 run 1: T04: назван незапущенный демон cron
* haiku V T04 run 2: T04: назван незапущенный демон cron
* haiku V T02 run 3: lsof по файлу не запускал, «открытых файлов нет»; совпал совет truncate

