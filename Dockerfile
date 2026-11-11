# Базовый образ песочницы verify-agent. Сеть нужна только при сборке;
# во время прогонов контейнеры запускаются с network_mode=none.
# Базовый образ закреплён по дайджесту (тот же, на котором получены результаты).
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nginx cron logrotate coreutils findutils gawk curl ca-certificates \
      tar gzip procps file \
 && rm -rf /var/lib/apt/lists/*
# Пользователи для эксперимента с ложным признанием (этап 3)
RUN groupadd shared \
 && useradd -m -s /bin/bash -G shared agent \
 && useradd -m -s /bin/bash -G shared human
