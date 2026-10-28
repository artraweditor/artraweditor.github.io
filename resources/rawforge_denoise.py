#!/usr/bin/env python3
"""ART user command: AI denoising of a raw file with RawForge.

The denoised image is saved next to the original as FILENAME-denoised.dng
(with a copy of the sidecar, if any).

This script only needs the Python standard library to run as a user command.
The actual denoising is done by running this same file with the `--worker`
option in the Python virtual environment where RawForge is installed."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Python virtual environment where RawForge is installed
VENV = Path.home() / "src" / "rawforge-venv"

# RawForge model to use
MODEL = "TreeNetDenoiseLight"

# select the device to use for denoising (cuda, mps, cpu, ...); by default,
# RawForge picks the best one
DEVICE = None

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


def worker(argv):
    """Run RawForge (this must be run in the virtual environment where it is
    installed). Progress is reported on the standard output as percentages."""
    import argparse
    import json

    import numpy
    from RawForge.application.ModelHandler import ModelHandler
    from RawForge.application.MODEL_REGISTRY import MODEL_REGISTRY
    import RawForge.application.InferenceWorker as iw
    from RawHandler.RawHandler import CoreRawMetadata

    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--model", choices=sorted(MODEL_REGISTRY), required=True)
    p.add_argument("--device")
    p.add_argument("--exiftool")

    def get_iso(s):
        s = s.lower()
        return int(s) if s != "auto" else s

    p.add_argument("--iso", type=get_iso)

    def get_strength(s):
        v = int(s)
        if not (0 < v <= 50):
            raise ValueError("invalid strength value")
        return v / 10.0

    p.add_argument("--strength", type=get_strength, default="10")
    opts = p.parse_args(argv)

    handler = ModelHandler()
    if opts.device:
        handler.set_device(opts.device)
    handler.load_model(opts.model)
    print("1", flush=True)

    handler.colorspace = "camera"

    iso = handler.load_rh(opts.input)
    print("2", flush=True)

    if opts.iso is not None:
        if opts.iso == "auto":
            if opts.exiftool:
                res = subprocess.run(
                    [opts.exiftool, "-json", opts.input],
                    stdout=subprocess.PIPE,
                    check=True,
                    universal_newlines=True,
                )
                data = json.loads(res.stdout)[0]
                try:
                    v = data["ISO"]
                    if isinstance(v, str) and v.startswith("Hi "):
                        v = v[3:]
                    iso = int(v)
                except (KeyError, ValueError):
                    pass
                iso = int(round(iso * float(data.get("ScaleFactor35efl", 1))))
            print("auto iso set to: %s" % iso, flush=True)
        else:
            iso = opts.iso
    iso *= opts.strength

    handler.rh.colorspace = "camera"
    md = handler.rh.core_metadata
    handler.rh.core_metadata = CoreRawMetadata(
        md.black_level_per_channel,
        md.white_level,
        numpy.eye(3),
        md.raw_pattern,
        md.camera_white_balance,
        md.iheight,
        md.iwidth,
    )

    def rgb_colorspace_transform(*args, **kwds):
        return numpy.eye(3)

    handler.rh.rgb_colorspace_transform = rgb_colorspace_transform

    conditioning = [iso, 0]

    def tqdm(iterable, *args, **kwds):
        items = list(iterable)
        n = len(items)
        last = 2
        for i, r in enumerate(items):
            yield r
            c = 2 + int(98 * i / n)
            if c > last:
                print(str(c), flush=True)
                last = c

    iw.tqdm = tqdm

    w = iw.InferenceWorker(
        handler.model,
        handler.model_params,
        handler.device,
        handler.rh,
        conditioning,
        None,
    )
    try:
        img, denoised = w.run()
        handler.handle_full_image(denoised, opts.output, True)
    except Exception as e:
        for line in str(e).splitlines():
            sys.stderr.write("ERROR: %s\n" % line)
        sys.stderr.flush()
        sys.exit(1)

    if opts.exiftool and os.path.exists(opts.output):
        subprocess.run(
            [
                opts.exiftool,
                "-TagsFromFile",
                opts.input,
                opts.output,
                "-all",
                "-icc_profile",
                "-overwrite_original",
            ]
        )


def error_message(errfile):
    """The error message of the worker: the "ERROR:" lines if there are any,
    otherwise the last line of its error output."""
    try:
        with open(errfile, errors="replace") as f:
            lines = [line.rstrip() for line in f if line.strip()]
    except OSError:
        lines = []
    msgs = [
        line[len("ERROR:") :].strip()
        for line in lines
        if line.startswith("ERROR:")
    ]
    if msgs:
        return "\n".join(msgs)
    return lines[-1] if lines else "Denoising error!"


def main(args):
    if len(args) != 1:
        raise RuntimeError("expected exactly one raw file")
    raw = Path(args[0])
    python = venv_python(VENV)

    with tempfile.TemporaryDirectory(prefix="art_rawforge_") as d:
        out = Path(d) / "out.dng"
        err = Path(d) / "error"
        cmd = [
            python,
            os.path.abspath(__file__),
            "--worker",
            str(raw),
            str(out),
        ]
        cmd += ["--exiftool", "exiftool", "--iso", "auto", "--model", MODEL]
        if DEVICE:
            cmd += ["--device", DEVICE]
        status = run_with_progress(cmd, err, "Denoising...")
        if status is None:  # cancelled by the user
            return
        if status != 0 or not out.is_file():
            show_error(error_message(err))
            return
        dest = unique_path(str(raw.with_suffix("")) + "-denoised", ".dng")
        shutil.move(str(out), str(dest))
        # finally, use the same sidecar for the denoised image as for the
        # original image, except that we override the denoising settings
        sidecar = Path(str(raw) + ".arp")
        if sidecar.is_file():
            write_sidecar(sidecar, Path(str(dest) + ".arp"), SIDECAR_EXTRA)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker(sys.argv[2:])
    else:
        run(main)
