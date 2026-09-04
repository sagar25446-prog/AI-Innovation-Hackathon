"""Check a teacher portrait before spending a render on it.

A full GuruFlow scene takes about two minutes, and a portrait SadTalker cannot
align fails at the very first step - so finding out in a few seconds is worth
it. This runs SadTalker's *own* detection and cropping, the same code
`inference.py` runs first, so a pass here means the portrait will be accepted.

Run it with the SadTalker venv, not GuruFlow's:

    C:\\SadTalker\\.venv\\Scripts\\python.exe tools\\check_portrait.py C:\\path\\to\\teacher.png

Exit code 0 when the portrait is usable, 1 when it is not.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import tempfile
from pathlib import Path

# Face crop SadTalker hands the renderer. Below this it gets upscaled and looks
# soft in the panel.
MIN_FACE_PIXELS = 200
RECOMMENDED_MIN_SIDE = 512


@contextlib.contextmanager
def _working_dir(path: Path):
    """Run inside SadTalker's directory.

    facexlib resolves its weight files relative to the *current* directory, so
    without this it re-downloads ~290 MB into whatever directory you happened
    to be in - including the GuruFlow repo, if that is where you ran it.
    """
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _fail(message: str) -> None:
    print(f"  FAIL  {message}")


def _ok(message: str) -> None:
    print(f"  ok    {message}")


def _warn(message: str) -> None:
    print(f"  warn  {message}")


def _no_face_hint() -> None:
    print(
        "\n  Usually one of:\n"
        "    - not front-facing (three-quarter angles break alignment)\n"
        "    - the face is too small a part of the frame\n"
        "    - heavy shadow across the face\n"
        "    - an illustration or stylised render rather than a photographic face"
    )


def _cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a SadTalker portrait.")
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--sadtalker-dir",
        type=Path,
        default=Path(r"C:\SadTalker"),
        help="SadTalker checkout (default: C:\\SadTalker)",
    )
    args = parser.parse_args()

    if not args.image.exists():
        _fail(f"no such file: {args.image}")
        return 1

    image_path = args.image.resolve()
    print(f"\nChecking {image_path.name}\n")

    # Cheap checks first, so obvious problems do not wait on a model load.
    try:
        import cv2
    except ImportError:
        _fail(
            "cv2 not importable - run this with SadTalker's interpreter:\n"
            "        C:\\SadTalker\\.venv\\Scripts\\python.exe "
            "tools\\check_portrait.py ..."
        )
        return 1

    image = cv2.imread(str(image_path))
    if image is None:
        _fail("not a readable image (PNG or JPG expected)")
        return 1

    height, width = image.shape[:2]
    if min(width, height) < RECOMMENDED_MIN_SIDE:
        _warn(
            f"{width}x{height} is small; {RECOMMENDED_MIN_SIDE}px+ on the short "
            "side gives the cropper room"
        )
    else:
        _ok(f"resolution {width}x{height}")

    aspect = width / height
    if not 0.6 <= aspect <= 1.7:
        _warn(
            f"unusual aspect ratio {aspect:.2f}; head-and-shoulders framing crops best"
        )

    sadtalker = args.sadtalker_dir
    if not (sadtalker / "inference.py").exists():
        _fail(f"no SadTalker checkout at {sadtalker} (pass --sadtalker-dir)")
        return 1

    sys.path.insert(0, str(sadtalker))
    try:
        from src.utils.init_path import init_path
        from src.utils.preprocess import CropAndExtract
    except Exception as exc:  # noqa: BLE001 - any import problem is fatal here
        _fail(f"could not load SadTalker: {type(exc).__name__}: {exc}")
        return 1

    with _working_dir(sadtalker):
        try:
            paths = init_path(
                str(sadtalker / "checkpoints"),
                str(sadtalker / "src" / "config"),
                256,
                False,
                "crop",
            )
            cropper = CropAndExtract(paths, "cuda" if _cuda() else "cpu")
        except Exception as exc:  # noqa: BLE001
            _fail(f"could not initialise the cropper: {type(exc).__name__}: {exc}")
            print("\n  Are the checkpoints downloaded? See docs/TALKING_HEAD_SETUP.md.")
            return 1

        with tempfile.TemporaryDirectory(prefix="portrait_check_") as work:
            try:
                coeff_path, crop_path, crop_info = cropper.generate(
                    str(image_path), work, "crop", source_image_flag=True, pic_size=256
                )
            except TypeError as exc:
                # SadTalker's preprocess does `raise "can not detect the
                # landmark..."` - a bare string - so Python reports "exceptions
                # must derive from BaseException" instead of the real problem.
                # Translate it rather than passing the confusion on.
                if "must derive from BaseException" in str(exc):
                    _fail("no face detected")
                    _no_face_hint()
                    return 1
                _fail(f"face processing raised TypeError: {exc}")
                return 1
            except Exception as exc:  # noqa: BLE001
                _fail(f"face processing raised {type(exc).__name__}: {exc}")
                return 1

            if coeff_path is None:
                _fail("no face found, or the face could not be aligned")
                _no_face_hint()
                return 1

            _ok("face detected and aligned")

            if crop_info and crop_info[0]:
                crop_w, crop_h = crop_info[0]
                if min(crop_w, crop_h) < MIN_FACE_PIXELS:
                    _warn(
                        f"detected face is {crop_w}x{crop_h}px; under "
                        f"{MIN_FACE_PIXELS}px it will be upscaled and look soft"
                    )
                else:
                    _ok(f"face region {crop_w}x{crop_h}px")

            if crop_path and Path(crop_path).exists():
                preview = image_path.with_name(image_path.stem + "_sadtalker_crop.png")
                cv2.imwrite(str(preview), cv2.imread(crop_path))
                _ok(f"crop preview written to {preview.name}")
                print("\n  Open that preview - it is what the panel will show.")
                print("  If the face is cut off or off-centre, reframe the portrait.")

    print("\nUSABLE - point GURUFLOW_TEACHER_PORTRAIT at this file.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
