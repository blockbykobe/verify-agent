#!/usr/bin/env python3
"""Синтез фраз голосом Coqui XTTS-v2 с автоматической проверкой разборчивости.

Каждая фраза озвучивается, затем распознаётся офлайн-моделью Whisper и сравнивается с исходным текстом
(доля ошибок по символам, CER, и средняя уверенность распознавания). Если фраза разобрана плохо,
она переозвучивается с другим зерном генерации; сохраняется лучший вариант. Отчёт — <wav>.qc.json.
Вход: JSON {speaker, items:[{text,path}], tries?, temperature?, judge?}. Пишет 16-битные моно WAV.
Модель хранится внутри проекта (.tts-models), лицензию CPML пользователь принял сам (13.11.2026)."""
import json
import os
import re
import sys
import wave
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / ".tts-models/hf"))
os.environ.setdefault("TTS_HOME", str(ROOT / ".tts-models"))
os.environ.setdefault("COQUI_TOS_AGREED", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torchaudio  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402
from num2words import num2words  # noqa: E402
from TTS.api import TTS  # noqa: E402


def norm(s):
    s = s.lower().replace("ё", "е").replace("%", " процентов")
    s = re.sub(r"\d+", lambda m: " " + num2words(int(m.group()), lang="ru") + " ", s)
    s = re.sub(r"[^a-zа-я ]+", " ", s)
    return " ".join(s.split())


def cer(ref, hyp):
    return 1 - SequenceMatcher(None, norm(ref), norm(hyp)).ratio()


def judge(model, wav, sr, text):
    a = torchaudio.functional.resample(torch.from_numpy(wav), sr, 16000).numpy()
    segs, _ = model.transcribe(a, language="ru", beam_size=5, temperature=0.0)
    segs = list(segs)
    hyp = " ".join(s.text.strip() for s in segs)
    lp = float(np.mean([s.avg_logprob for s in segs])) if segs else -9.0
    c = cer(text, hyp)
    return {"cer": round(c, 3), "logprob": round(lp, 3), "hyp": hyp, "score": c - 0.1 * lp}  # меньше — лучше


def main():
    job = json.load(open(sys.argv[1]))
    tries, temp = job.get("tries", 8), job.get("temperature", 0.5)
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    sr = tts.synthesizer.output_sample_rate
    wm = WhisperModel(job.get("judge", "base"), device="cpu", compute_type="int8", cpu_threads=os.cpu_count())
    for n, it in enumerate(job["items"], 1):
        best = None
        for k in range(tries):
            torch.manual_seed(1000 + k)
            wav = np.asarray(tts.tts(text=it["text"], speaker=job["speaker"], language="ru", temperature=temp,
                                     top_p=0.8, repetition_penalty=5.0), dtype=np.float32)
            q = judge(wm, wav, sr, it["text"]) | {"try": k}
            if best is None or q["score"] < best[1]["score"]:
                best = (wav, q)
            if q["cer"] <= 0.06 and q["logprob"] > -0.35:  # достаточно разборчиво — дальше не пробуем
                break
        wav, q = best
        with wave.open(it["path"], "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.clip(wav, -1, 1) * 32767).astype("<i2").tobytes())
        Path(it["path"] + ".qc.json").write_text(json.dumps(q | {"text": it["text"]}, ensure_ascii=False))
        print(f"xtts {n}/{len(job['items'])} cer={q['cer']} lp={q['logprob']} try={q['try']}", flush=True)


if __name__ == "__main__":
    main()
