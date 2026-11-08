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

If several files are given, they are processed one after the other without
the graphical interface: SMART is run with --mode denoise --cli, so it uses the
settings of its configuration file (model, provider, tile size, DNG
bit depth...), and a progress dialog is shown for each image (first for the
conversion to DNG, then for the denoising). Each result is saved next to its
original file as described above. Cancelling any of the dialogs stops the
whole batch (the images that are already done are kept). If some images
fail, the errors are shown together at the end.

Usage: smart_denoise.py [--smart-cmd CMD] FILE [FILE...]

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
    smart_popen_kwargs,
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


BAYER, XTRANS, LINEARDNG, UNKNOWN = range(4)

def get_kind(raw):
    """BAYER if `raw` is a 2x2 RGB Bayer raw file (also if exiftool cannot
    tell: some formats, e.g. CR3, do not report the colour filter array),
    XTRANS for Fuji X-trans files, LINEARDNG for linear dng files,
    and UNKNOWN otherwise."""
    try:
        out = subprocess.run(
            ["exiftool", "-json", "-XTransLayout", "-CFAPattern2",
             "-CFARepeatPatternDim", "-CFAPlaneColor", "-DNGVersion",
             "-PhotometricInterpretation", str(raw)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        tags = json.loads(out)[0]
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        return UNKNOWN
    if "XTransLayout" in tags:
        return XTRANS
    if "DNGVersion" in tags \
       and tags.get("PhotometricInterpretation") == "Linear Raw":
        return LINEARDNG
    dim = str(tags.get("CFARepeatPatternDim", "2 2")).split()
    if dim and dim != ["2", "2"]:
        return UNKNOWN
    # the pattern lists plane indices, the planes default to R, G, B
    pattern = str(tags.get("CFAPattern2", "0 1 1 2")).split()
    planes = str(tags.get("CFAPlaneColor", "Red,Green,Blue")).split(",")
    if len(pattern) != 4 or any(not p.isdigit() for p in pattern):
        return UNKNOWN
    return BAYER if all(int(p) < len(planes) and planes[int(p)].strip() in
                        ("Red", "Green", "Blue") for p in pattern) else UNKNOWN


class Failed(Exception):
    """The processing of one file failed (the message is for the user)."""


class Cancelled(Exception):
    """The user cancelled."""


def convert_to_dng(orig, input_kind, d, label=""):
    """Convert the raw file `orig` with ART-cli to a DNG in the directory `d`
    (a mosaiced DNG for Bayer files, a linear one for the others) and return
    its path; `orig` itself if it already is a linear DNG. `label` is shown in
    the progress dialog."""
    if input_kind == LINEARDNG:
        return orig
    kind = "mosaic" if input_kind == BAYER else "demosaic"
    dng = d / (orig.stem + ".dng")
    err = d / "error"
    status = run_with_progress(
        [ART_CLI, "--progress", "-d", "-s", "--raw-preprocess=" + kind,
         "--dng-lens-opcodes"]
        + (["--dng-wb=neutral", "--dng-levels=original"]
           if kind == "mosaic" else [])
        + ["-Y", "-o", str(dng), "-c", str(orig)],
        err,
        "Converting %sto DNG..." % label,
        width=500,
    )
    if status is None:
        raise Cancelled()
    if status != 0 or not dng.is_file():
        raise Failed(last_lines(err, 5) or "Conversion error!")
    return dng


def save_denoised(orig, out, input_kind):
    kind = "mosaic" if input_kind == BAYER else "demosaic"
    save_result(
        orig,
        out,
        "_denoised",
        ".dng",
        write=lambda src, dst: write_denoise_sidecar(src, dst, kind),
    )


def denoise_interactive(smart, orig):
    """One file: convert it and open it in SMART."""
    input_kind = get_kind(orig)
    if input_kind == UNKNOWN:
        raise Failed("Unknown file kind")
    with tempfile.TemporaryDirectory(prefix="art_smart_denoise_") as d:
        d = Path(d)
        dng = convert_to_dng(orig, input_kind, d)
        out = d / "denoised.dng"
        run_smart(
            smart,
            ["--mode", "denoise", "--format", "dng", "--save-as", out, dng],
        )
        if out.is_file():
            save_denoised(orig, out, input_kind)


def denoise_batch_item(smart, orig, label):
    """One file of a batch: convert it and denoise it with SMART, without its
    interface (with the settings of its configuration file)."""
    input_kind = get_kind(orig)
    if input_kind == UNKNOWN:
        raise Failed("Unknown file kind")
    with tempfile.TemporaryDirectory(prefix="art_smart_denoise_") as d:
        d = Path(d)
        dng = convert_to_dng(orig, input_kind, d, label)
        out = d / "denoised.dng"
        err = d / "smart-error"
        status = run_with_progress(
            list(smart)
            + ["--mode", "denoise", "--cli", "--progress", "--format", "dng",
               "-o", str(out), str(dng)],
            err,
            "Denoising %s..." % label.rstrip(),
            width=500,
            popen_kwargs=smart_popen_kwargs(),
        )
        if status is None:
            raise Cancelled()
        if status != 0 or not out.is_file():
            raise Failed(last_lines(err, 5) or "Denoising error!")
        save_denoised(orig, out, input_kind)


def main(args):
    ap = argparse.ArgumentParser()
    add_smart_cmd_arg(ap)
    ap.add_argument("raw", nargs="+")
    opts = ap.parse_args(args)
    smart = smart_command(opts.smart_cmd)
    files = [Path(f).resolve() for f in opts.raw]

    if len(files) == 1:
        try:
            denoise_interactive(smart, files[0])
        except Cancelled:
            pass
        except Failed as e:
            show_error(str(e))
        return

    failures = []
    for i, orig in enumerate(files, 1):
        label = "%s (%d of %d) " % (orig.name, i, len(files))
        try:
            denoise_batch_item(smart, orig, label)
        except Cancelled:
            return          # the whole batch is cancelled
        except Failed as e:
            failures.append("%s: %s" % (orig.name, e))
    if failures:
        show_error("\n\n".join(failures))


if __name__ == "__main__":
    run(main)
