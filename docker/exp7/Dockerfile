# Образ для эксперимента 7 (задачи от Gemini): базовый образ + python3 (проверки Gemini написаны на Python) и sudo (задача 5).
FROM verify-agent-base
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 sudo \
 && rm -rf /var/lib/apt/lists/*
