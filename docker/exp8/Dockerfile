# Образ для эксперимента 8 (ловушки с ложными вводными): базовый образ + инструменты диагностики,
# которые нужны ловушкам (git — конфликт слияния, lsof/psmisc — открытый файл, python3 — сервис на 8080,
# xxd — невидимые символы, iproute2 — ss).
FROM verify-agent-base
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git lsof psmisc xxd iproute2 \
 && rm -rf /var/lib/apt/lists/*
