#!/bin/bash
# Pre-commit: сканирует подготовленные к коммиту изменения на секреты (ключи API и т.п.) через gitleaks в Docker.
# Устанавливается в .git/hooks/pre-commit с разрешения владельца репозитория:
#   cp tools/precommit-gitleaks.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
set -e
repo=$(git rev-parse --show-toplevel)
docker run --rm -v "$repo":/repo:ro -w /repo zricethezav/gitleaks:v8.30.1 git --pre-commit --staged --no-banner /repo
