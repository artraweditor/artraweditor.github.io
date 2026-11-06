#!/usr/bin/env python3
"""ART user command: AI raw denoising with SMART (greycard denoiser).

The raw file is converted with ART-cli to a DNG (only the raw processing
steps of the sidecar, if any, are applied: hot/dead pixels, white balance,
...), which is opened in SMART (https://github.com/artraweditor/SMART) in
denoise mode. There the model can be chosen and the denoising run, with a
before/after view.

The DNG is a mosaiced one for Bayer raw files, which the denoiser of SMART
demosaics and denoises at once. Other raw files (X-Trans, ...), which that
denoiser does not support, are demosaiced by ART and converted to a linear
DNG instead, which SMART denoises with another network. Whether a raw file
is Bayer or not is found out with exiftool.

The save dialog of SMART proposes FILENAME_denoised.dng next to the original
file. If that file is written, it gets a copy of the sidecar of the original
file, with the denoising turned off (and the white balance reset to the
camera one, as the white balance is already applied to the data).

This script only needs the Python standard library: SMART itself runs in the
Python virtual environment given below.

The code shared by all the Python user commands is in art_usercommand.py,
next to this file."""

import json
import subprocess
import tempfile
import time
from pathlib import Path

from art_usercommand import (
    DENOISE_OFF,
    last_lines,
    run,
    run_with_progress,
    show_error,
    venv_python,
    write_sidecar,
)

# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where SMART is located
SMART_DIR = Path.home() / "src" / "SMART"

ART_CLI = "ART-cli"

# the white balance is baked into the DNG written by ART-cli, so the
# sidecar of the denoised file must not apply it again
SIDECAR_EXTRA = (
    """
[White Balance]
Enabled=true
Setting=Camera
"""
    + DENOISE_OFF
)


def is_bayer(raw):
    """True if `raw` is a 2x2 RGB Bayer raw file (also if exiftool cannot
    tell: some formats, e.g. CR3, do not report the colour filter array)."""
    try:
        out = subprocess.run(
            ["exiftool", "-json", "-XTransLayout", "-CFAPattern2",
             "-CFARepeatPatternDim", "-CFAPlaneColor", str(raw)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        tags = json.loads(out)[0]
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        return True
    if "XTransLayout" in tags:
        return False
    dim = str(tags.get("CFARepeatPatternDim", "2 2")).split()
    if dim and dim != ["2", "2"]:
        return False
    # the pattern lists plane indices, the planes default to R, G, B
    pattern = str(tags.get("CFAPattern2", "0 1 1 2")).split()
    planes = str(tags.get("CFAPlaneColor", "Red,Green,Blue")).split(",")
    if len(pattern) != 4 or any(not p.isdigit() for p in pattern):
        return False
    return all(int(p) < len(planes) and planes[int(p)].strip() in
               ("Red", "Green", "Blue") for p in pattern)


def glob_escape(s):
    return "".join("[%s]" % c if c in "*?[" else c for c in s)


def main(args):
    if len(args) != 1:
        raise RuntimeError("expected exactly one raw file")
    orig = Path(args[0]).resolve()
    sidecar = Path(str(orig) + ".arp")
    kind = "mosaic" if is_bayer(orig) else "demosaic"

    with tempfile.TemporaryDirectory(prefix="art_smart_denoise_") as d:
        d = Path(d)
        # named after the raw file, so that the default name in the save
        # dialog of SMART is FILENAME_denoised.dng
        dng = d / (orig.stem + ".dng")
        err = d / "error"
        status = run_with_progress(
            [ART_CLI, "--progress", "-d", "-s", "--raw-preprocess=" + kind]
            + ["-Y", "-o", str(dng), "-c", str(orig)],
            err,
            "Converting to DNG...",
            width=500,
        )
        if status is None:  # cancelled by the user
            return
        if status != 0 or not dng.is_file():
            show_error(last_lines(err, 5) or "Conversion error!")
            return
        start = time.time() - 1  # file times can be coarse
        subprocess.run(
            [
                venv_python(VENV),
                str(SMART_DIR / "src" / "main.py"),
                "--mode",
                "denoise",
                "--format",
                "dng",
                "--outdir",
                str(orig.parent),
                str(dng),
            ]
        )

    if sidecar.is_file():
        # whatever the extension the user picked
        for p in orig.parent.glob(glob_escape(orig.stem) + "_denoised.*"):
            if p.suffix.lower() != ".arp" and p.stat().st_mtime >= start:
                write_sidecar(sidecar, Path(str(p) + ".arp"), SIDECAR_EXTRA)


if __name__ == "__main__":
    run(main)
