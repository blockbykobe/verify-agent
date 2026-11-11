#!/bin/bash
# Ограниченный red-team прогон garak против ЛОКАЛЬНОЙ qwen2.5-coder:7b. Внешние API не атакуются.
# Все каталоги garak (данные, кэш, конфиг) перенаправлены внутрь проекта.
cd "$(dirname "$0")/../.."
mkdir -p .pip-tmp && CFG=.pip-tmp/garak_config.run.yaml
sed "s|<REPO>|$PWD|" results/garak/garak_config.yaml > "$CFG"
export XDG_DATA_HOME=$PWD/.pip-tmp/garak-home/data XDG_CACHE_HOME=$PWD/.pip-tmp/garak-home/cache XDG_CONFIG_HOME=$PWD/.pip-tmp/garak-home/config
.venv-garak/bin/garak --model_type ollama.OllamaGeneratorChat --model_name qwen2.5-coder:7b \
  --probes promptinject.HijackHateHumans,promptinject.HijackKillHumans,promptinject.HijackLongPrompt,latentinjection.LatentInjectionReport,latentinjection.LatentInjectionResume,latentinjection.LatentWhoisSnippet,latentinjection.LatentJailbreak,dan.DanInTheWild,dan.Ablation_Dan_11_0 \
  --config "$CFG" --report_prefix qwen7b
