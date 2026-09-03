# Photoreal talking-head teacher (optional)

Adds a lip-synced human teacher to the lesson video, composited into the
teacher panel. Everything else keeps working if you never set this up: with no
configuration the drawn avatar is used and no code path changes.

Target hardware: **6 GB VRAM (RTX 4050)**.

---

## 0. Read this first: whose face

**Use a face you have the right to use.** One of:

* a **synthetic portrait** you generated (Tensor.art, CivitAI, SDXL) - free, no
  rights problem, and indistinguishable in the final video;
* a **licensed stock portrait** whose licence covers synthetic media;
* a **real person who has consented** on the record - a teammate, say.

Do not point this at a photograph of a public figure or of anyone who has not
agreed. A lip-synced video of an identifiable person saying words they never
said is a deepfake whatever the intent, and putting one in front of judges as
your product's teacher is a reputational and legal problem, not a shortcut.

A synthetic portrait costs nothing and removes the question entirely. The API
returns this notice in `/health` under `video.talkingHead.portraitRights` so it
stays visible to whoever wires this up.

---

## 1. Model choice

| Model | VRAM | Verdict |
| --- | --- | --- |
| **MuseTalk 1.5** | ~4-6 GB | **Use this.** Inpaints a 256x256 mouth region on an existing video |
| LivePortrait | <1 GB | Good for making the *idle* clip from a still |
| SadTalker | ~8 GB | Higher quality single-shot, slower; viable if you have headroom |
| EchoMimic V2 / Hallo 2 | 12-24 GB | Out of reach on 6 GB |

MuseTalk only moves the mouth, so head motion has to come from the input video.
That is why an idle clip is required rather than a still image.

---

## 2. Assets

### Portrait
Generate a front-facing teacher portrait, neutral expression, mouth closed,
even lighting, face filling a good part of the frame. Front-facing matters:
MuseTalk's face alignment degrades badly on three-quarter angles.

### Idle video (this is the input MuseTalk drives)
Animate the still into a 10-second loop with small movements - blinking,
breathing, slight nods. **LivePortrait runs locally in well under 1 GB VRAM**,
so it will not disturb your budget. Kling AI's free tier also works.

Keep it seamless: the clip is looped under longer scenes.

```
Portrait (still) --LivePortrait--> idle_teacher.mp4 --MuseTalk + narration--> talking head
```

### Audio
Already handled. `services/voice` produces narration in the female neural voice
(`hi-IN-SwaraNeural` / `en-IN-NeerjaNeural`), and GuruFlow converts it to the
16 kHz mono WAV Whisper needs - **you do not need to do this by hand.**

---

## 3. Install MuseTalk

In its **own** environment. MuseTalk pins torch, mmcv and mmpose versions that
will fight with the API's dependencies if installed together.

```bash
git clone https://github.com/TMElyralab/MuseTalk.git
cd MuseTalk
conda create -n musetalk python=3.10 -y
conda activate musetalk
```

**Install torch first, with the CUDA build.** `pip install -r requirements.txt`
alone pulls a CPU-only torch and MuseTalk then fails at runtime:

```bash
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

DWPose needs the OpenMMLab stack, which does not install cleanly from plain
pip:

```bash
pip install --no-cache-dir -U openmim
mim install mmengine "mmcv==2.0.1" "mmdet==3.1.0" "mmpose==1.1.0"
```

### ffmpeg
The winget package is **`Gyan.FFmpeg`**; a bare `winget install ffmpeg` is
ambiguous and may pick the wrong package:

```bash
winget install Gyan.FFmpeg
```

GuruFlow itself does not need this - it uses the `imageio-ffmpeg` binary - but
MuseTalk calls `ffmpeg` from PATH.

### Weights

```bash
# Windows
download_weights.bat
# Linux/macOS
sh ./download_weights.sh
```

Expected layout:

```
./models/
├── musetalk
├── musetalkV15
├── dwpose
├── face-parse-bisent
├── resnet18
├── sd-vae-ft-mse
└── whisper
```

`musetalkV15` is the 1.5 weights directory; older guides list only `musetalk`.
If the scripts fail behind a proxy, download from the Hugging Face repos listed
in MuseTalk's README and place them by hand.

### Verify before wiring it up

```bash
python -m scripts.inference --inference_config configs/inference/test.yaml --version v15
```

Get that working standalone first. Debugging MuseTalk through GuruFlow's
subprocess layer is far more painful.

---

## 4. Point GuruFlow at it

```bash
set GURUFLOW_TALKING_HEAD=1
set GURUFLOW_MUSETALK_DIR=C:\path\to\MuseTalk
set GURUFLOW_MUSETALK_PYTHON=C:\Users\you\miniconda3\envs\musetalk\python.exe
set GURUFLOW_TEACHER_IDLE_VIDEO=C:\path\to\idle_teacher.mp4
set GURUFLOW_MUSETALK_BBOX_SHIFT=0
```

`GURUFLOW_MUSETALK_PYTHON` must be the **musetalk env's** interpreter - that is
the whole point of the separate environment.

Check it took:

```bash
curl http://127.0.0.1:8077/health
```

`video.talkingHead.usable` should be `true`. If not, `problems` names exactly
what is missing.

### bbox_shift - the quality knob

MuseTalk's single most important parameter. It shifts the detected mouth box:

* mouth looks under-opened / mumbling -> try `-5`, `-9`
* jaw looks unnaturally wide -> try `+5`

It is portrait-specific. Expect to try three or four values. MuseTalk prints a
suggested range for your input on first run.

---

## 5. How it fits together

```
Scene ─┬─ visual  ──> Manim ──> lesson frame, teacher panel left empty
       ├─ narration ─> edge-tts (female) ──> mp3 ──> 16 kHz mono wav
       │                                  │
       │                                  └──> MuseTalk(idle video, wav) ──> head.mp4
       │                                                                       │
       └───────────────> ffmpeg overlay head into the panel rect <─────────────┘
                                    │
                                    └──> ffmpeg mux narration ──> cached scene.mp4
```

`services/video/scenes.py::teacher_panel_rect()` is the single source of truth
for the panel rectangle, so the Manim scene and the compositor cannot disagree.

Everything is cached on a content hash, and the talking-head setting is part of
that hash, so switching it on does not serve stale drawn-avatar videos.

**Failure is never fatal.** If MuseTalk is missing, times out, or errors, the
scene falls back to the drawn avatar and the lesson plays normally.

---

## 6. Performance on a 4050

MuseTalk runs roughly real-time-ish on a desktop 30-series and slower on a
6 GB mobile card. A 15-second scene may take 30-90 seconds the first time.

**Pre-render before demonstrating.** The web client already calls
`POST /lessons/{id}/video/prerender` when a lesson starts, which warms every
scene plus both repair scenes. Give it a few minutes, then present from a warm
cache. Do not generate live in front of judges.

To iterate faster while tuning `bbox_shift`:

```bash
set GURUFLOW_VIDEO_QUALITY=low
```

---

## 7. Honest limitations

* MuseTalk moves the mouth only. Head motion, blinks and expression all come
  from the idle clip, so a stiff idle clip produces a stiff teacher.
* Lip-sync quality on romanised Hinglish is weaker than on English, because
  Whisper's phoneme features are trained on natural language, not
  transliteration.
* The composited head is 248x292 px inside a 1280x720 frame. Detail beyond
  that is wasted, so do not spend GPU time on a 4K portrait.
* Adding this makes the demo depend on a GPU. Keep the drawn-avatar path
  working, and demo from it if the machine is not yours.
