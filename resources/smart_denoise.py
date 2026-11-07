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

SMART is run with --save-as, to save to a temporary file: pressing Save
there writes it at once. When SMART exits, if the file was written it is moved
next to the original file as FILENAME_denoised.dng (or FILENAME_denoised-1.dng
etc. if that exists), together with a copy of the sidecar of the original
file, with the denoising turned off (and the white balance reset to the
camera one: the DNG stores the white balance of the original as its as-shot
neutral). For linear DNGs (non-Bayer files), the input profile is also set to
the embedded one. The sidecar is written before the image is moved, so that
it is already there when the image appears in ART.

Usage: smart_denoise.py [--smart-cmd CMD] FILE

  --smart-cmd CMD  command used to run SMART (default: the first SMART
                   executable found in $PATH)

This script only needs the Python standard library.

The code shared by all the Python user commands is in art_usercommand.py,
next to this file."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from art_usercommand import (
    DENOISE_OFF,
    add_smart_cmd_arg,
    last_lines,
    run,
    run_smart,
    run_with_progress,
    save_result,
    show_error,
    smart_command,
)

ART_CLI = "ART-cli"

# Settings appended to the sidecar of the denoised file.
#
# The DNG written by ART-cli has the white balance of the sidecar as its
# as-shot neutral, so "Camera" gives the white balance of the original. For
# the mosaiced DNG (Bayer files) ART-cli is run with --dng-wb=neutral: the
# data is not white balanced. With the default, --dng-wb=baked, the white
# balance is applied to the data but the neutral and colour matrix no longer
# match it, so the camera profile, which depends on the colour temperature,
# is applied wrongly and the colours are off. The linear DNG (other files) is
# baked and cannot be given that option, so its sidecar uses the embedded
# input profile instead of the camera one (see write_denoise_sidecar).
SIDECAR_EXTRA = (
    """
[White Balance]
Enabled=true
Setting=Camera
"""
    + DENOISE_OFF
)


def set_key(text, group, key, value):
    """Set `key` to `value` in the [`group`] section of the sidecar `text`
    (adding the key, or the section, if missing)."""
    lines = text.splitlines()
    header = "[%s]" % group
    start = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            start = i
            break
    if start is None:
        return text.rstrip("\n") + "\n\n%s\n%s=%s\n" % (header, key, value)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("["):
            end = i
            break
    for i in range(start + 1, end):
        if lines[i].startswith(key + "="):
            lines[i] = "%s=%s" % (key, value)
            break
    else:
        lines.insert(start + 1, "%s=%s" % (key, value))
    return "\n".join(lines) + "\n"


def write_denoise_sidecar(src, dst, kind):
    """Write to `dst` the sidecar `src`, adapted to the denoised file made
    from a DNG of this `kind` ("mosaic" or "demosaic")."""
    text = src.read_text(encoding="utf-8")
    if kind == "demosaic":
        # the linear DNG written by ART-cli has the white balance baked in,
        # which makes the camera profiles (auto-matched or not) wrong
        text = set_key(text, "Color Management", "InputProfile", "(embedded)")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write(SIDECAR_EXTRA)


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


def main(args):
    ap = argparse.ArgumentParser()
    add_smart_cmd_arg(ap)
    ap.add_argument("raw")
    opts = ap.parse_args(args)
    smart = smart_command(opts.smart_cmd)
    orig = Path(opts.raw).resolve()
    kind = "mosaic" if is_bayer(orig) else "demosaic"

    with tempfile.TemporaryDirectory(prefix="art_smart_denoise_") as d:
        d = Path(d)
        dng = d / (orig.stem + ".dng")
        err = d / "error"
        status = run_with_progress(
            [ART_CLI, "--progress", "-d", "-s", "--raw-preprocess=" + kind]
            + (["--dng-wb=neutral"] if kind == "mosaic" else [])
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
        out = d / "denoised.dng"
        run_smart(
            smart,
            ["--mode", "denoise", "--format", "dng", "--save-as", out, dng],
        )
        if out.is_file():
            save_result(
                orig,
                out,
                "_denoised",
                ".dng",
                write=lambda src, dst: write_denoise_sidecar(src, dst, kind),
            )


if __name__ == "__main__":
    run(main)
