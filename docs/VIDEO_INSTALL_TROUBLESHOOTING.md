# Video generation: install troubleshooting

The teaching-video renderer needs **Manim**, which draws through Cairo and
Pango. On Windows these arrive as prebuilt wheels and need nothing extra. On
Linux and macOS the Python packages compile against *system* libraries, and a
missing one produces the error below.

> **Status on this repo's build machine (Windows 11, Python 3.12):** this does
> **not** reproduce. `pip install -r apps/api/requirements.txt` completes with
> exit code 0, `pycairo` and `manimpango` install from wheels, and a real scene
> renders. This page exists for teammates and judges on other platforms.

---

## Symptom

```
manim._config.utils.RequiredDependencyException: pangocairo >= 1.30.0 is required
```

or, during `pip install`:

```
Package 'cairo' not found / Package 'pangocairo' not found
error: command 'gcc' failed / Failed building wheel for pycairo
```

The API still starts and lessons still work - `/health` reports
`video.available: false` and the client keeps using the interactive view. Only
the MP4 rendering is lost.

---

## Fix by platform

### Windows

Should not be needed. If `pycairo` does try to build from source, you are most
likely on an unusual Python version with no matching wheel - install Python
3.10-3.12 (64-bit) and recreate the virtual environment.

### macOS (Homebrew)

```bash
brew install cairo pango pkg-config
```

Then reinstall the Python packages so they pick the libraries up:

```bash
pip install --no-cache-dir --force-reinstall pycairo manimpango
```

On Apple Silicon, Homebrew installs to `/opt/homebrew`. If the build still
cannot find the libraries:

```bash
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
```

### Debian / Ubuntu

```bash
sudo apt-get update && sudo apt-get install -y build-essential python3-dev libcairo2-dev libpango1.0-dev pkg-config
```

```bash
pip install --no-cache-dir --force-reinstall pycairo manimpango
```

### Fedora / RHEL

```bash
sudo dnf install -y gcc python3-devel cairo-devel pango-devel pkgconf-pkg-config
```

### Arch

```bash
sudo pacman -S --needed base-devel cairo pango pkgconf
```

---

## ffmpeg

**No system ffmpeg is required.** `imageio-ffmpeg` ships a static binary and
`services/ffmpeg_util.py` prefers a system `ffmpeg` on PATH only if one exists.

If you want a system build anyway:

| Platform | Command |
| --- | --- |
| Windows | `winget install Gyan.FFmpeg` |
| macOS | `brew install ffmpeg` |
| Debian/Ubuntu | `sudo apt-get install -y ffmpeg` |

---

## Verify the fix

```bash
python -c "import manim, imageio_ffmpeg; print('manim', manim.__version__); print(imageio_ffmpeg.get_ffmpeg_exe())"
```

Then confirm the service agrees:

```bash
curl -s http://127.0.0.1:8077/health
```

`video.available` should be `true`. If it is `false`, either manim failed to
import or no ffmpeg was found - `services/video/video_generation_available()`
requires both.

Finally, render for real:

```bash
GURUFLOW_RUN_SLOW_TESTS=1 GURUFLOW_VIDEO_QUALITY=low python -m pytest apps/api/tests/test_video_voice_qa.py -q
```

---

## If you cannot fix it

Nothing else breaks. Lesson planning, the misconception-repair loop, RAG
citations, multilingual switching, narration and the report all work without
Manim; the client keeps the animated interactive view and the **Watch video**
button simply stays disabled. Do not block a demo on this.
