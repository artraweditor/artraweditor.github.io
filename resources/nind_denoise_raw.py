#!/usr/bin/env python3
"""ART user command: AI denoising of a raw file with nind-denoise.

The file is converted to a 16-bit linear TIFF with ART-cli, denoised with
nind-denoise, and saved next to the original as FILENAME-denoised.tif (with a
copy of the sidecar, if any).

This script only needs the Python standard library: nind-denoise itself runs
in the Python virtual environment given below."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# select the device to use for denoising (cuda, mps, cpu, ...)
DEVICE = "mps"

# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where nind-denoise is located
NIND_DENOISE_DIR = Path.home() / "src" / "nind-denoise"

# model to use
DENOISE_MODEL = (
    NIND_DENOISE_DIR
    / "models"
    / "nind_denoise"
    / "2019-02-18T20:10_run_nn.py_--time_limit_259200_--batch_size_94_"
    "--test_reserve_ursulines-red_stefantiek_ursulines-building_MuseeL-Bobo_"
    "CourtineDeVillersDebris_MuseeL-Bobo-C500D_--skip_sizecheck_--lr_3e-4"
    / "model_257.pth"
)

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


# an .arp sidecar with a custom output profile and settings suitable for
# denoising
PROFILE = """[Version]
Version=1037

[Color Management]
OutputProfile=RTv4_Rec2100_PQ

[ToneCurve]
Enabled=false

[Sharpening]
Enabled=false

[OutputSharpening]
Enabled=false

[SoftLight]
Enabled=false

[Film Simulation]
Enabled=false

[Smoothing]
Enabled=false

[TextureBoost]
Enabled=false

[Denoise]
Enabled=false

[Resize]
Enabled=false

[RAW Bayer]
Method=lmmse

[RAW X-Trans]
Method=3-pass (best)
"""

# used if the selected file has no sidecar
PROFILE_NO_SIDECAR = """[Exposure]
HLRecovery=Balanced

[ToneCurve]
Enabled=false

[RAW]
CAEnabled=true
CA=true
CAAvoidColourshift=true
CAAutoIterations=2
HotDeadPixelEnabled=true
HotPixelFilter=true
DeadPixelFilter=true
HotDeadPixelThresh=100
"""

# the denoised image uses the same sidecar as the original image, except that
# we override some of the settings
SIDECAR_EXTRA = """
[Exposure]
Enabled=false

[White Balance]
Enabled=true
Setting=Camera

[Impulse Denoising]
Enabled=false

[Denoise]
Enabled=false
"""


def sidecar_subset(sidecar):
    """The groups of a sidecar that we want to keep: the white balance, the
    raw processing and the exposure."""
    keep = False
    lines = []
    for line in sidecar.read_text(encoding="utf-8").splitlines():
        if re.search(r"\[(White Balance|RAW|Exposure)", line):
            keep = True
            lines.append(line)
        elif "[" in line:
            keep = False
        elif keep:
            lines.append(line)
    return "\n".join(lines) + "\n"


def main(args):
    if len(args) != 1:
        raise RuntimeError("expected exactly one raw file")
    raw = Path(args[0])
    python = venv_python(VENV)
    denoise = NIND_DENOISE_DIR / "src" / "nind_denoise" / "denoise_image.py"

    with tempfile.TemporaryDirectory(prefix="art_nind_") as d:
        d = Path(d)
        profile = d / "p1.arp"
        sidecar = Path(str(raw) + ".arp")
        sidecar_args = []
        if sidecar.is_file():
            # if the selected file has a sidecar, we are going to use (some
            # parameters of) that (except that we override some of the
            # settings, see above)
            (d / "p2.arp").write_text(sidecar_subset(sidecar), encoding="utf-8")
            sidecar_args = ["-p", str(d / "p2.arp")]
            profile.write_text(PROFILE, encoding="utf-8")
        else:
            profile.write_text(PROFILE + PROFILE_NO_SIDECAR, encoding="utf-8")

        # process the raw file with ART-cli, adding a progress dialog for user
        # notification
        tif = d / "out.tif"
        err = d / "error"
        status = run_with_progress(
            [ART_CLI, "--progress"]
            + sidecar_args
            + ["-p", str(profile), "-Y", "-t", "-b16"]
            + ["-o", str(tif), "-c", str(raw)],
            err,
            "Converting to TIFF...",
            width=500,
        )
        if status is None:  # cancelled by the user
            return
        if status != 0 or not tif.is_file():
            show_error(last_lines(err, 5) or "Conversion error!")
            return

        # now let's denoise
        out = d / "denoised.tif"
        status = run_with_progress(
            [
                python,
                str(denoise),
                "--network",
                "UNet",
                "--model_path",
                str(DENOISE_MODEL),
                "--device",
                DEVICE,
                "--cs",
                "512",
                "--ucs",
                "400",
                "--input",
                str(tif),
                "-o",
                str(out),
            ],
            err,
            "Denoising...",
            pulsate=True,
        )
        if status is None:  # cancelled by the user
            return
        if status != 0 or not out.is_file():
            show_error(last_lines(err) or "Denoising error!")
            return
        dest = unique_path(str(raw.with_suffix("")) + "-denoised", ".tif")
        shutil.move(str(out), str(dest))
        # finally, use the same sidecar for the denoised image as for the
        # original image, except that we override WB and denoising settings
        if sidecar.is_file():
            write_sidecar(sidecar, Path(str(dest) + ".arp"), SIDECAR_EXTRA)


if __name__ == "__main__":
    run(main)
