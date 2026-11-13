#!/usr/bin/env python3
"""Синтез фраз голосом Coqui XTTS-v2 (запускается из окружения с coqui-tts). Вход: JSON {speaker, items:[{text,path}]}.
Пишет 16-битные моно WAV. Модель должна быть уже скачана (лицензия CPML принимается пользователем)."""
import json
import sys
import wave

import numpy as np
from TTS.api import TTS

job = json.load(open(sys.argv[1]))
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
sr = tts.synthesizer.output_sample_rate
for n, it in enumerate(job["items"], 1):
    wav = np.asarray(tts.tts(text=it["text"], speaker=job["speaker"], language="ru"), dtype=np.float32)
    pcm = (np.clip(wav, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(it["path"], "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    print(f"xtts {n}/{len(job['items'])}", flush=True)
