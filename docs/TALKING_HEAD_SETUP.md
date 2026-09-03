# Photoreal talking-head teacher (optional)

Adds a lip-synced human teacher to the lesson video, composited into the
teacher panel. Everything else keeps working if you never set this up: with no
configuration the drawn avatar is used and no code path changes.

Engine: **SadTalker**. Target hardware: **RTX 4050, 6 GB VRAM**.

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

The API returns this notice at `/health` under
`video.talkingHead.portraitRights` so it stays visible to whoever wires it up.

---

## 1. Why SadTalker here

| Model | VRAM | Verdict |
| --- | --- | --- |
| **SadTalker** | ~4-6 GB at `crop`/256 | **In use.** Still image in, animated talking head out |
| MuseTalk | ~4-6 GB | Cheaper, but mouth-only inpainting and weak sync on Hinglish audio |
| EchoMimic V2 / AniPortrait / LatentSync | 12-24 GB | Better, but out of reach on 6 GB |

**SadTalker takes a still image, not a video.** It synthesises head motion,
blinks and lip movement itself, so the LivePortrait "idle clip" step an
inpainting model needs is gone. One asset instead of two.

The trade-off: SadTalker *generates* instead of *inpainting*, so it is slower -
**minutes per scene, not seconds**. Pre-render; never generate live in a demo.

---

## 2. The portrait

One still image. That is the whole asset list.

* front-facing, both eyes visible - three-quarter angles break face alignment
* neutral expression, mouth closed
* even lighting, no hard shadow across the mouth
* face filling a good part of the frame
* 512x512 or larger, PNG or JPG

**Do not bother with a 4K portrait.** The teacher panel is ~248x292 px inside a
720p frame, and SadTalker runs at 256x256 in the low-VRAM configuration, so
extra resolution is thrown away.

---

## 3. Install SadTalker

In its **own** environment - SadTalker pins torch and face-detection versions
that will fight with the API's dependencies.

```bash
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker
conda create -n sadtalker python=3.10 -y
conda activate sadtalker
```

**Install CUDA torch first.** `pip install -r requirements.txt` on its own
pulls a CPU-only build and SadTalker then runs at a crawl:

```bash
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

### ffmpeg

```bash
winget install Gyan.FFmpeg
```

The winget package id is `Gyan.FFmpeg`; a bare `winget install ffmpeg` is
ambiguous. GuruFlow itself does not need this - it uses the `imageio-ffmpeg`
binary - but SadTalker calls `ffmpeg` from PATH.

### Checkpoints

```bash
# Windows
download_models.bat
# Linux/macOS
bash scripts/download_models.sh
```

Expected layout:

```
./checkpoints/
├── mapping_00109-model.pth.tar
├── mapping_00229-model.pth.tar
├── SadTalker_V0.0.2_256.safetensors
└── SadTalker_V0.0.2_512.safetensors
./gfpgan/weights/          <- only needed if you enable the enhancer
```

If the scripts fail behind a proxy, the same files are on the SadTalker
Hugging Face repo; place them by hand.

### Verify standalone before wiring it up

```bash
python inference.py --driven_audio examples/driven_audio/bus_chinese.wav --source_image examples/source_image/full_body_1.png --result_dir ./results --preprocess crop --size 256 --still
```

Get this working **first**. Debugging SadTalker through GuruFlow's subprocess
layer is far more painful than debugging it directly.

---

## 4. Point GuruFlow at it

```bash
set GURUFLOW_TALKING_HEAD=1
set GURUFLOW_SADTALKER_DIR=C:\path\to\SadTalker
set GURUFLOW_SADTALKER_PYTHON=C:\Users\you\miniconda3\envs\sadtalker\python.exe
set GURUFLOW_TEACHER_PORTRAIT=C:\path\to\teacher.png
```

`GURUFLOW_SADTALKER_PYTHON` must be the **sadtalker env's** interpreter - that
is the entire point of the separate environment.

Check it took:

```bash
curl http://127.0.0.1:8077/health
```

`video.talkingHead.usable` should be `true`. If not, `problems` names exactly
what is missing.

### Tuning

| Variable | Default | Use |
| --- | --- | --- |
| `GURUFLOW_SADTALKER_EXPRESSION` | `1.0` | Mouth openness. Raise toward `1.3` if lips look under-articulated; above ~1.5 it over-acts |
| `GURUFLOW_SADTALKER_STILL` | `1` | Suppresses head sway. Keep on: motion drifts the face inside a small panel |
| `GURUFLOW_SADTALKER_PREPROCESS` | `crop` | `crop` is the low-VRAM path. `full` needs more VRAM and pastes back into the whole image, which the panel crops off anyway |
| `GURUFLOW_SADTALKER_SIZE` | `256` | `512` doubles VRAM and time for detail the panel cannot display |
| `GURUFLOW_SADTALKER_ENHANCER` | *(off)* | `gfpgan` sharpens faces but roughly doubles VRAM and runtime. Leave off on 6 GB |
| `GURUFLOW_TALKING_HEAD_TIMEOUT` | `1800` | Raise if long scenes are being killed mid-render |

**If you hit CUDA out-of-memory:** confirm `preprocess=crop` and `size=256`,
turn the enhancer off, close other GPU applications, and set
`GURUFLOW_VIDEO_QUALITY=low` so scenes are shorter to encode.

---

## 5. How it fits together

```
Scene ─┬─ visual  ──> Manim ──> lesson frame, teacher panel left empty
       ├─ narration ─> edge-tts (female) ──> mp3 ──> 16 kHz mono wav
       │                                  │
       │                                  └──> SadTalker(portrait, wav) ──> head.mp4
       │                                                                      │
       └───────────────> ffmpeg overlay head into the panel rect <────────────┘
                                    │
                                    └──> ffmpeg mux narration ──> cached scene.mp4
```

`services/video/scenes.py::teacher_panel_rect()` is the single source of truth
for the panel rectangle, so the Manim scene and the compositor cannot disagree.

Everything is cached on a content hash, and the talking-head setting is part of
that hash, so switching engines does not serve stale videos.

**Failure is never fatal.** Missing checkout, CUDA OOM, timeout, or a failed
overlay all fall back to the drawn avatar and the lesson plays normally.

---

## 6. Performance on a 4050

SadTalker generates every frame, so budget **1-4 minutes per scene** at
`crop`/256 on a 6 GB mobile card. A 7-scene lesson plus two repair scenes is a
coffee break, not a demo-time operation.

Warm the cache before presenting - the web client already fires this when a
lesson starts:

```bash
curl -X POST http://127.0.0.1:8077/lessons/<LESSON_ID>/video/prerender
```

While tuning `expression_scale`, iterate on one scene with
`GURUFLOW_VIDEO_QUALITY=low` rather than re-rendering the whole lesson.

---

## 7. Honest limitations

* SadTalker at 256 is soft. Fine inside a 248 px panel, poor if you ever scale
  the teacher up to fill the frame.
* Lip-sync on romanised Hinglish is weaker than on English, because the audio
  features are trained on natural language rather than transliteration. This
  affects every model in this class, SadTalker included - it is not a reason to
  keep switching engines.
* `--still` trades liveliness for stability. Without it the head drifts inside
  the panel; with it the teacher is calm but slightly static.
* Adding this makes the demo depend on your GPU. Keep the drawn-avatar path
  working and demo from it if the machine is not yours.
