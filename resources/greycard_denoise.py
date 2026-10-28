#!/usr/bin/env python3
"""ART user command: denoise + demosaic a raw file with the AI denoiser of
greycard (via greycard-denoise-raw), producing a linear DNG that ART opens as
a raw file (camera matrix, DCP lookup and sidecar settings keep working).

This script only needs the Python standard library: the denoiser itself runs
in the virtual environment of greycard-denoise-raw."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# directory of the greycard-denoise-raw project (its own virtualenv, in the
# `.venv` subdirectory, is used)
GREYCARD_DENOISE_RAW_DIR = Path.home() / "src" / "greycard-denoise-raw"

# network size: fast, balanced or best
MODEL = "balanced"

# onnxruntime provider: auto, cpu, coreml, cuda, directml, ...
PROVIDER = "auto"

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


SIDECAR_EXTRA = """
[Impulse Denoising]
Enabled=false

[Denoise]
Enabled=false
"""


def main(args):
    if len(args) != 1:
        raise RuntimeError("expected exactly one raw file")
    raw = Path(args[0])
    python = venv_python(GREYCARD_DENOISE_RAW_DIR / ".venv")
    script = GREYCARD_DENOISE_RAW_DIR / "greycard_denoise_raw.py"

    with tempfile.TemporaryDirectory(prefix="art_greycard_") as d:
        out = Path(d) / "out.dng"
        err = Path(d) / "error"
        status = run_with_progress(
            [
                python,
                str(script),
                str(raw),
                "-o",
                str(out),
                "--model",
                MODEL,
                "--provider",
                PROVIDER,
                "--progress",
            ],
            err,
            "Denoising...",
        )
        if status is None:  # cancelled by the user
            return
        if status != 0 or not out.is_file():
            # the last line is the error message (earlier ones may be a
            # traceback or harmless runtime warnings)
            show_error(last_lines(err) or "Denoising error!")
            return
        dest = unique_path(str(raw.with_suffix("")) + "-denoised", ".dng")
        shutil.move(str(out), str(dest))
        # use the same sidecar for the denoised image as for the original
        # image, except that we override the denoising settings
        sidecar = Path(str(raw) + ".arp")
        if sidecar.is_file():
            write_sidecar(sidecar, Path(str(dest) + ".arp"), SIDECAR_EXTRA)


if __name__ == "__main__":
    run(main)
