"""Word-level Russian transcription with faster-whisper.
usage: python3 transcribe.py VIDEO OUT.json [model=medium]
Prints segments and a one-line 'word@start' list that you use to time every overlay."""
import sys, json, subprocess, numpy as np
from faster_whisper import WhisperModel

src, out = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else "medium"
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768  # decoded by ffmpeg: avoids PyAV version issues
m = WhisperModel(model, device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio, language="ru", word_timestamps=True, beam_size=5)
data = [{"start": s.start, "end": s.end, "text": s.text,
         "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in s.words]} for s in segs]
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for s in data:
    print(f"{s['start']:6.2f}-{s['end']:6.2f} {s['text']}")
print("\nWORDS:", " ".join(f"{w['w']}@{w['s']:.2f}" for s in data for w in s["words"]))
