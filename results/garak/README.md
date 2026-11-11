# garak red-team scan of the local model

Tool: [garak](https://github.com/NVIDIA/garak) v0.17.1 (NVIDIA LLM vulnerability scanner), installed in a separate venv.
Target: **only** the local `qwen2.5-coder:7b` via Ollama (`ollama.OllamaGeneratorChat`), CPU. No external API was attacked.
Settings: 1 generation per prompt, at most 20 prompts per probe (`soft_probe_prompt_cap: 20`, seed 42). `dan.Ablation_Dan_11_0` ignores the cap and ran all 127 prompts. Total runtime: 1 h 45 min. Script: `run_garak.sh`; config: `garak_config.yaml`. Raw output: `qwen7b.report.jsonl`, `qwen7b.hitlog.jsonl`, `qwen7b.report.html`. Successful attacks are in the hitlog and contain model‑generated offensive strings, the probes' own targets.

| Probe | What it tries | Detector | Attack success rate |
|---|---|---|---|
| promptinject.HijackHateHumans | prompt injection: make the model print a rogue string | AttackRogueString | **90%** (18/20) |
| promptinject.HijackLongPrompt | same, inside a long prompt | AttackRogueString | **75%** (15/20) |
| promptinject.HijackKillHumans | same, different rogue string | AttackRogueString | 20% (4/20) |
| latentinjection.LatentInjectionReport | instruction hidden in a document the model summarises | TriggerListDetector | **55%** (11/20) |
| latentinjection.LatentInjectionResume | instruction hidden in a résumé | TriggerListDetector | 35% (7/20) |
| latentinjection.LatentJailbreak | jailbreak hidden in content | TriggerListDetector / ToxicCommentModel | 35% / 15% |
| latentinjection.LatentWhoisSnippet | instruction hidden in WHOIS data | TriggerListDetector | 5% (1/20) |
| dan.DanInTheWild | real jailbreak prompts collected from the internet | MitigationBypass | **50%** (10/20) |
| dan.Ablation_Dan_11_0 | variants of the "DAN 11.0" jailbreak | DAN, MitigationBypass | 0% (0/127) |

How to read it:
* The model resists the classic "DAN 11.0" family (0/127), but half of the jailbreaks collected in the wild got through.
* Direct and latent (in‑document) prompt injection works often: up to 90% for direct and 55% for latent. This matches the project's own injection test, where a README comment got `curl … | bash` into scripts 9/10 times.
* For this project the consequence is the same as before: do not rely on the model to resist injection. The sandbox (no network, no capabilities) and the policy gate are the controls that held.
* Limitations: ≤20 prompts per probe, 1 generation, temperature at the Ollama default; garak's string/keyword detectors have their own false positives and negatives. Treat the rates as indicative, not precise.
