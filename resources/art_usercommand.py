"""Common code of the ART user commands written in Python.

ART runs a user command with its own directory (with ART-cli and ART-dialogs)
in the $PATH, and with the directory containing the command as the working
directory (and, for a Python script, as the first entry of `sys.path`: this
is why this module can be imported by the scripts that are next to it).

Only the Python standard library is needed."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

# settings to add to the sidecar of a denoised image, so that the denoising
# is not applied again
DENOISE_OFF = """
[Impulse Denoising]
Enabled=false

[Denoise]
Enabled=false
"""


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


def run_with_progress(cmd, errfile, text, width=None, pulsate=False,
                      popen_kwargs=None):
    """Run `cmd`, showing a progress dialog driven by its standard output
    (percentages, one per line), and saving its standard error to `errfile`.
    `popen_kwargs`: extra arguments for subprocess.Popen (e.g.
    smart_popen_kwargs()).
    Returns the exit status of `cmd`, or None if the user cancelled."""
    dialog = ["ART-dialogs"]
    if width:
        dialog.append("--width=%d" % width)
    dialog += ["--progress", "--auto-close", "--text=" + text]
    if pulsate:
        dialog.append("--pulsate")
    with open(errfile, "wb") as err:
        worker = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err,
                                  **(popen_kwargs or {}))
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


def add_smart_cmd_arg(parser):
    """Add the --smart-cmd option to an argparse parser."""
    parser.add_argument(
        "--smart-cmd",
        metavar="CMD",
        help="command to run SMART (default: the first SMART executable "
        "found in $PATH)",
    )


def smart_command(cmd=None):
    """The command (as a list of arguments) that runs SMART: `cmd`, if given
    (a command line, e.g. the path of the executable), otherwise the first
    "SMART" executable found in $PATH."""
    if cmd:
        if os.name == "nt":
            # keep the backslashes of Windows paths
            parts = [a.strip('"') for a in shlex.split(cmd, posix=False)]
        else:
            parts = shlex.split(cmd)
        if parts:
            return parts
    exe = shutil.which("SMART")
    if exe is None:
        raise RuntimeError(
            "SMART executable not found in $PATH: add its directory to "
            "$PATH, or give its location with --smart-cmd in the Command "
            "line of the user command"
        )
    return [exe]


def smart_popen_kwargs():
    """Extra arguments to run SMART from ART on Windows without opening a
    console window (SMART may be the console version of the program)."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def run_smart(smart, args):
    """Run SMART (the command `smart`, see smart_command) with the arguments
    `args` and wait for it to exit."""
    return subprocess.run(list(smart) + [str(a) for a in args],
                          **smart_popen_kwargs())


def write_sidecar(src, dst, extra):
    """Copy the sidecar `src` to `dst`, appending the settings in `extra`."""
    shutil.copyfile(src, dst)
    with open(dst, "a", encoding="utf-8", newline="\n") as f:
        f.write(extra)


def save_result(raw, result, tag, suffix, sidecar_extra=None, write=None):
    """Move the file `result` next to the raw file `raw`, as RAW<tag><suffix>
    (adding a number if that already exists), and return its path.

    If `raw` has a sidecar, the new file gets one too: the same as the
    original, with `sidecar_extra` appended to override some of the settings
    (if given), or written by `write(src, dst)` (if given). The sidecar is
    written BEFORE the file is moved, so that it is already there when ART
    sees the new file (otherwise ART may create a default one, replacing
    ours)."""
    dest = unique_path(str(Path(raw).with_suffix("")) + tag, suffix)
    sidecar = Path(str(raw) + ".arp")
    if sidecar.is_file():
        if write is not None:
            write(sidecar, Path(str(dest) + ".arp"))
        elif sidecar_extra is not None:
            write_sidecar(sidecar, Path(str(dest) + ".arp"), sidecar_extra)
    shutil.move(str(result), str(dest))
    return dest


def run(main):
    """Run the `main` function of a script on its command line arguments,
    showing in a dialog any exception that it raises."""
    add_to_path()
    try:
        main(sys.argv[1:])
    except Exception as e:
        show_error("%s: %s" % (type(e).__name__, e))
        sys.exit(1)
