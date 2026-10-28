#!/usr/bin/env python3
"""ART user command: AI masking with SMART.

The raw file is exported to a JPEG with ART-cli, which is opened in the SMART
GUI (https://github.com/artraweditor/SMART): masks can be created there and
saved as png files, to be loaded in ART as external masks.

Usage: smart_masking.py [-f] [--keep] FILE

  -f, --fast  export a downscaled image (faster, but less precise masks)
  --keep      leave the JPEG file (FILENAME_SMART.jpg) next to the original,
              and do not wait for SMART to exit

This script only needs the Python standard library: SMART itself runs in the
Python virtual environment given below."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where SMART is located
SMART_DIR = Path.home() / "src" / "SMART"

ART_CLI = "ART-cli"

##############################################################################
# Helpers (the same in all the ART user commands written in Python)


def add_to_path():
    """Make it easier to find tools that ART does not provide (exiftool...),
    e.g. when ART is started from the macOS Finder, where $PATH is very short.
    ART itself puts its own directory (ART-cli, ART-dialogs) at the front."""
    extra = [
        Path.home() / ".local" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/opt/local/bin"),
        Path("/usr/local/bin"),
    ]
    parts = [os.environ["PATH"]] if os.environ.get("PATH") else []
    parts += [str(d) for d in extra if d.is_dir()]
    os.environ["PATH"] = os.pathsep.join(parts)


def show_error(text):
    text = text.strip() or "Unknown error"
    try:
        subprocess.run(
            ["ART-dialogs", "--error", "--no-markup", "--text=" + text]
        )
    except OSError:
        print(text, file=sys.stderr)


def last_lines(path, count=1):
    """The last non-empty lines of a text file (e.g. the error output)."""
    try:
        with open(path, errors="replace") as f:
            lines = [line.rstrip() for line in f if line.strip()]
    except OSError:
        return ""
    return "\n".join(lines[-count:])


def run_with_progress(cmd, errfile, text, width=None, pulsate=False):
    """Run `cmd`, showing a progress dialog driven by its standard output
    (percentages, one per line), and saving its standard error to `errfile`.
    Returns the exit status of `cmd`, or None if the user cancelled."""
    dialog = ["ART-dialogs"]
    if width:
        dialog.append("--width=%d" % width)
    dialog += ["--progress", "--auto-close", "--text=" + text]
    if pulsate:
        dialog.append("--pulsate")
    with open(errfile, "wb") as err:
        worker = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err)
        try:
            dlg = subprocess.Popen(dialog, stdin=worker.stdout)
        except OSError:
            worker.kill()
            worker.wait()
            raise
        worker.stdout.close()
        if dlg.wait() != 0:
            # the dialog exits with a non-zero status if the user cancelled
            worker.terminate()
            worker.wait()
            return None
        return worker.wait()


def unique_path(stem, suffix):
    """`stem+suffix`, or `stem-1+suffix`, `stem-2+suffix`... if it exists."""
    path = Path(stem + suffix)
    i = 1
    while path.exists():
        path = Path("%s-%d%s" % (stem, i, suffix))
        i += 1
    return path


def venv_python(venv):
    """The Python interpreter of a virtual environment (Unix or Windows)."""
    for rel in ("bin/python", "Scripts/python.exe"):
        python = Path(venv) / rel
        if python.exists():
            return str(python)
    raise RuntimeError(
        "Python interpreter not found in %s: please check the settings at "
        "the beginning of %s" % (venv, Path(__file__).name)
    )


def write_sidecar(src, dst, extra):
    """Copy the sidecar `src` to `dst`, appending the settings in `extra`."""
    shutil.copyfile(src, dst)
    with open(dst, "a", encoding="utf-8", newline="\n") as f:
        f.write(extra)


def run(main):
    add_to_path()
    try:
        main(sys.argv[1:])
    except Exception as e:
        show_error("%s: %s" % (type(e).__name__, e))
        sys.exit(1)


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
        dest = unique_path(str(raw.with_suffix("")) + "_SMART", ".jpg")
        shutil.move(str(jpg), str(dest))

    smart = [python, str(SMART_DIR / "src" / "main.py"), str(dest)]
    if opts.keep:
        start_detached(smart)
    else:
        try:
            subprocess.run(smart)
        finally:
            try:
                dest.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    run(main)
