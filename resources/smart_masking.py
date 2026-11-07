#!/usr/bin/env python3
"""ART user command: AI masking with SMART.

The raw file is exported to a JPEG with ART-cli, which is opened in the SMART
GUI (https://github.com/artraweditor/SMART): masks can be created there and
saved as png files, to be loaded in ART as external masks.

SMART is run with --save-as, to save to a temporary file: pressing Save there
writes it at once. When SMART exits, if the mask was written it is moved next
to the raw file as FILENAME_mask.png (or FILENAME_mask-1.png etc. if that
exists). (With --keep, SMART is not waited for, so the save dialog is used.)

Usage: smart_masking.py [-f] [--keep] FILE

  -f, --fast  export a downscaled image (faster, but less precise masks)
  --keep      leave the JPEG file (FILENAME_SMART.jpg) next to the original,
              and do not wait for SMART to exit

This script only needs the Python standard library: SMART itself runs in the
Python virtual environment given below.

The code shared by all the Python user commands is in art_usercommand.py,
next to this file."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from art_usercommand import (
    last_lines,
    run,
    run_with_progress,
    save_result,
    show_error,
    venv_python,
)

# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where SMART is located
SMART_DIR = Path.home() / "src" / "SMART"

ART_CLI = "ART-cli"

# turn off cropping and modules coming later in the pipeline
PROFILE = """[Version]
Version=1037

[Crop]
Enabled=false
"""


def start_detached(cmd):
    """Start a program and do not wait for it."""
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--fast", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("raw")
    opts = ap.parse_args(args)
    raw = Path(opts.raw)
    python = venv_python(VENV)

    with tempfile.TemporaryDirectory(prefix="art_smart_") as d:
        d = Path(d)
        profile = d / "p1.arp"
        profile.write_text(PROFILE, encoding="utf-8")
        jpg = d / "out.jpg"
        err = d / "error"

        # process the raw file with ART-cli, adding a progress dialog for user
        # notification
        cmd = [ART_CLI, "--progress"]
        if opts.fast:
            cmd.append("-f")
        cmd += ["-d", "-s", "-p", str(profile), "-Y", "-j"]
        cmd += ["-o", str(jpg), "-c", str(raw)]
        status = run_with_progress(cmd, err, "Exporting...", width=500)
        if status is None:  # cancelled by the user
            return
        if not jpg.is_file():
            show_error(
                last_lines(err, 5) or "ART-cli did not produce any output"
            )
            return
        smart = [python, str(SMART_DIR / "src" / "main.py")]
        if opts.keep:
            dest = save_result(raw, jpg, "_SMART", ".jpg")
            start_detached(smart + [str(dest)])
            return
        mask = d / "mask.png"
        subprocess.run(smart + ["--save-as", str(mask), str(jpg)])
        if mask.is_file():
            save_result(raw, mask, "_mask", ".png")


if __name__ == "__main__":
    run(main)
