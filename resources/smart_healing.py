#!/usr/bin/env python3
"""ART user command: AI healing with SMART.

Usage: smart_healing.py (--raw | --nonraw) [--smart-cmd CMD] FILE

  --raw     FILE is a raw file: it is exported with ART-cli to a 32-bit float
            linear Rec.2020 TIFF, with only the processing that cannot be done
            on a developed image (highlight recovery, raw preprocessing, lens
            correction, rotation / perspective / distortion / CA / defringe,
            noise reduction, exposure compensation), and that TIFF is opened
            in SMART (https://github.com/artraweditor/SMART) in healing mode.
  --nonraw  FILE is opened directly in SMART.
  --smart-cmd CMD
            command used to run SMART (default: the first SMART executable
            found in $PATH).

In both cases SMART is run with --save-as, to save to a temporary file:
pressing Save there writes it at once. When SMART exits, if the file was
written it is moved next to the original file as FILENAME_healed.EXT (or
FILENAME_healed-1.EXT etc. if that exists), together with a copy of the
sidecar of the original file (for raw files, with the settings that were
already applied by the export reset, so that they are not applied twice). The
sidecar is written before the image is moved, so that it is already there
when the healed image appears in ART.

This script only needs the Python standard library.

The code shared by all the Python user commands is in art_usercommand.py,
next to this file."""

import argparse
import tempfile
from pathlib import Path

from art_usercommand import (
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

# modules that are turned off for the export: everything that is not needed
# to get a good linear image from the raw file (or that can be done after
# healing)
DISABLED_MODULES = [
    "Saturation",
    "ToneCurve",
    "Local Contrast",
    "Channel Mixer",
    "Black & White",
    "HSL Equalizer",
    "Luminance Curve",
    "Sharpening",
    "Dehaze",
    "TextureBoost",
    "DynamicRangeCompression",
    "LogEncoding",
    "ToneEqualizer",
    "Crop",
    "Gradient",
    "PCVignette",
    "Vignetting Correction",
    "Resize",
    "OutputSharpening",
    "SoftLight",
    "Film Simulation",
    "RGB Curves",
    "Grain",
    "Smoothing",
    "ColorCorrection",
    "Film Negative",
    "Spot Removal",
]

# applied on top of the default profile and of the sidecar (if any). White
# balance, the "RAW" and "RAW Bayer/X-Trans" groups, lens correction,
# geometry, CA, defringing and denoising come from there.
EXPORT_PROFILE = (
    "[Version]\nVersion=1040\n\n"
    + "".join("[%s]\nEnabled=false\n\n" % m for m in DISABLED_MODULES)
    + """[Color Management]
OutputProfile=RTv4_Linear_Rec2020
"""
)


def exposure_group(sidecar):
    """The [Exposure] group of the sidecar with the black point reset (it is
    not a raw-only step). It has to be given in full: ART resets the keys
    that are missing from a group it reads (e.g. HLRecovery would go back
    to Off)."""
    lines = []
    keep = False
    for line in sidecar.read_text(encoding="utf-8").splitlines():
        if line.startswith("["):
            keep = line.strip() == "[Exposure]"
        elif keep and line.strip() and not line.startswith("Black="):
            lines.append(line)
    if not lines:
        return ""
    return "\n[Exposure]\n" + "\n".join(lines) + "\nBlack=0\n"

# the healed image already includes the processing above, so the sidecar that
# we give to it (a copy of the one of the raw file) must not apply it again
SIDECAR_EXTRA = """
[Exposure]
Compensation=0
HLRecovery=Off

[White Balance]
Enabled=true
Setting=Camera

[Impulse Denoising]
Enabled=false

[Denoise]
Enabled=false

[Defringing]
Enabled=false

[Rotation]
Enabled=false

[Distortion]
Enabled=false

[Perspective]
Enabled=false

[CACorrection]
Enabled=false

[LensProfile]
LcMode=none

[Coarse Transformation]
Rotate=0
HorizontalFlip=false
VerticalFlip=false
"""


def heal(smart, image, out):
    """Run SMART in healing mode on `image`, saving to `out`, and wait for it
    to exit."""
    run_smart(smart, ["--mode", "heal", "--save-as", out, image])


def main(args):
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--raw", action="store_true")
    mode.add_argument("--nonraw", action="store_true")
    add_smart_cmd_arg(ap)
    ap.add_argument("file")
    opts = ap.parse_args(args)
    smart = smart_command(opts.smart_cmd)
    orig = Path(opts.file).resolve()
    sidecar = Path(str(orig) + ".arp")

    # the extension of the output is the one of the image that SMART opens
    # (a tif for raw files)
    ext = (orig.suffix if opts.nonraw else ".tif") or ".tif"
    extra = "" if opts.nonraw else SIDECAR_EXTRA

    with tempfile.TemporaryDirectory(prefix="art_smart_heal_") as d:
        d = Path(d)
        out = d / ("healed" + ext)
        if opts.nonraw:
            heal(smart, orig, out)
        else:
            profile = d / "p1.arp"
            text = EXPORT_PROFILE
            if sidecar.is_file():
                text += exposure_group(sidecar)
            profile.write_text(text, encoding="utf-8")
            tif = d / (orig.stem + ".tif")
            err = d / "error"
            status = run_with_progress(
                [ART_CLI, "--progress", "-d", "-s", "-p", str(profile)]
                + ["-Y", "-t", "-b32", "-o", str(tif), "-c", str(orig)],
                err,
                "Exporting...",
                width=500,
            )
            if status is None:  # cancelled by the user
                return
            if status != 0 or not tif.is_file():
                show_error(last_lines(err, 5) or "Export error!")
                return
            heal(smart, tif, out)
        if out.is_file():
            save_result(orig, out, "_healed", ext, extra)


if __name__ == "__main__":
    run(main)
