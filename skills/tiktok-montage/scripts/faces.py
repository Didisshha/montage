"""Track faces over time with MediaPipe's face detector (BlazeFace).
usage: python3 faces.py VIDEO MODEL.tflite OUT.json [step_s=0.25]
Model: https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite
OUT.json: [[t, [[cx, cy, w, h, score], ...]], ...] in 1080x1920 output coordinates, faces sorted left->right."""
import sys, json, subprocess, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

src, model, out = sys.argv[1], sys.argv[2], sys.argv[3]
step = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
W, H = 1080, 1920
det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
    base_options=mpt.BaseOptions(model_asset_path=model), min_detection_confidence=0.4))
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-map", "0:v:0", "-vf", f"fps={1 / step},scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
res, n = [], 0
while True:
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    fr = np.frombuffer(b, np.uint8).reshape(H, W, 3)
    faces = []
    T = 320  # tiles where a typical face is 60-120 px -> well inside the short-range model's range
    for y0 in range(300, 1500 - T + 1, 160):
        for x0 in range(0, W - T + 1, 152):
            crop = np.ascontiguousarray(fr[y0:y0 + T, x0:x0 + T])
            r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
            for d in r.detections:
                bb = d.bounding_box
                if d.categories[0].score >= 0.6 and 30 < bb.width < 200:
                    faces.append([x0 + bb.origin_x + bb.width / 2, y0 + bb.origin_y + bb.height / 2,
                                  bb.width, bb.height, d.categories[0].score])
    uniq = []
    for f in sorted(faces, key=lambda f: -f[4]):  # de-duplicate overlapping windows
        if all(abs(f[0] - u[0]) > 60 or abs(f[1] - u[1]) > 60 for u in uniq):
            uniq.append(f)
    res.append([round(n * step, 2), [[round(v, 1) for v in f] for f in sorted(uniq, key=lambda f: f[0])]])
    n += 1
json.dump(res, open(out, "w"))
print(f"{n} samples; faces found in {sum(1 for r in res if r[1])}")
