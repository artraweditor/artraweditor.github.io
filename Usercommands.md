# User Commands

Since version 1.4, ART supports a simple form of plugins, called *user commands*.
These are simply external programs that are accessible from the contextual menu in the file browser or the folders panel, which are executed on the currently selected files or folder.

![User commands menu](resources/usercommands.png)

A useful feature of user commands is that they allow to define some *matching criteria*, which will determine when the commands are available: if the currently selected list of files doesn't match the user command criteria, such command will not be available in the menu. This effectively provides a (simple, but still useful) form of input validation.

## How to define user commands

User commands are simple text files in the same syntax used by the `arp` sidecar files (but with `.txt` extension), 
placed in the `usercommands` subdirectory directory of ART config folder (typically `$HOME/.config/ART` on Linux and `%LOCALAPPDATA%\ART` on Windows),
that must comply with the following specifications:

- They must contain a single group of options, called `[ART UserCommand]`

- They must include the following mandatory definitions:

    * `Label`: the text displayed in the context menu
    * `Command`: the command to execute. The path can be either absolute or relative to the current directory; the command can also contain extra arguments (the input files will be appended to the list of arguments);

- They can include the following optional definitions, for specifying the command matching criteria:

    * `Camera`: a regular expression for restricting the command to specific cameras, specified as `MAKE Model`; if not present, the command will match any camera (the matching is case insensitive);
    * `Extension`: a list of supported file extensions (by default any extension will match);
    * `FileType`: `raw`, `nonraw`, `any` (default) or `directory`;
    * `MinArgs`: minimum number of arguments to provide (default `1`);
    * `MaxArgs`: maximum number of arguments to provide (default unbounded);
    * `NumArgs`: exact number of arguments to provide;
    * `MatchCamera`: if `true`, the command is available only if all the selected files come from the same camera (default `false`);
    * `MatchLens`: as above, but match on the lens;
    * `MatchShutter`: match on the shutter speed;
    * `MatchISO`: match on the ISO value;
    * `MatchAperture`: match on the aperture value;
    * `MatchFocalLen`: match on the focal length;
    * `MatchDimensions`: match on the image dimensions.

### Controlling which commands are loaded and their order

By default, all the `.txt` files in the `usercommands` directory are loaded, and the commands are listed sorted by file name.
Since ART version 1.26.11, this can be customized by putting in the same directory a text file called `ARTlist.txt`
(the name is matched case-insensitively), in the same way as for [LUTs and CTL scripts](Luts#artlist).
If present, the file determines which user command files are loaded, and in which order they appear in the menu.

The file contains one file name per line (relative to the `usercommands` directory, or an absolute path).
Anything starting with a `#` and up to the end of the line is ignored, and so are blank lines. For example:

```
# my commands
stitch.txt
resize.txt     # trailing comments are fine
```

Entries that do not exist are skipped, as are duplicates. Files in the directory that are not listed are not loaded.
Listed files can have any name (they do not need the `.txt` extension).

## Environment

User commands are run with the directory containing the ART executables added to the `$PATH`, so `ART-cli` and `ART-dialogs` (see below) can be invoked by name, without specifying their location. Any other program that the command needs (e.g. `hugin` in the example below) must be reachable through the `$PATH` that ART inherited from the environment it was started from; this can be a problem on macOS when ART is started from the Finder, where the `$PATH` is very short. In that case, a script can set it explicitly (e.g. `export PATH=/opt/homebrew/bin:$PATH`).

## Showing dialogs: `ART-dialogs`

User commands often need to interact with the user, e.g. for reporting errors, showing the progress of a long operation, or asking for a file name. For this, since version 1.26.11 ART includes the `ART-dialogs` tool, installed next to `ART` and `ART-cli`. It is a small program with the same look as the ART main window, and with a command line that follows the one of the well-known [`zenity`](https://help.gnome.org/users/zenity/stable/) tool (of which it implements a subset), so it can be used in scripts in the same way.

The kind of dialog is chosen with one of the following options:

| Option | Dialog |
|---|---|
| `--info`, `--warning`, `--error`, `--question` | a message dialog, showing the text given with `--text` |
| `--progress` | a progress bar, driven by the standard input (see below) |
| `--file-selection` | a file chooser; the selected path is printed to the standard output |
| `--entry` | a text entry; the entered text is printed to the standard output |
| `--list` | a list of choices; the selected rows are printed to the standard output |
| `--scale` | a slider; the chosen value is printed to the standard output |

Options common to all the dialogs:

* `--title=TEXT`, `--text=TEXT`: window title and message (the text can contain Pango markup, e.g. `<b>bold</b>`, unless `--no-markup` is given; `\n` and `\t` are interpreted as newline and tab);
* `--width=N`, `--height=N`: window size;
* `--ok-label=TEXT`, `--cancel-label=TEXT`: button labels;
* `--timeout=SECONDS`: close the dialog after the given time;
* `--no-wrap`: do not wrap the message text.

The result is communicated through the exit status: `0` if the user confirmed (OK, Yes or Save), `1` if the user cancelled or closed the window (or answered No to a `--question`), `5` if the timeout expired, and `255` for a command line error. Scripts should therefore check `$?` to detect cancellation.

### Progress dialogs

`ART-dialogs --progress` reads its standard input line by line:

* a line with just a number (`0`-`100`) sets the progress percentage;
* a line starting with `#` sets the message text to the rest of the line;
* any other line is ignored.

Options: `--percentage=N` (initial value), `--pulsate` (an animated bar, for operations of unknown length, ignoring the percentages), `--auto-close` (close the dialog when `100` is reached or when the input ends, with exit status `0`), `--no-cancel` (hide the cancel button) and `--auto-kill` (terminate the parent process, i.e. the script, if the user cancels). Without `--auto-close`, the dialog stays open at the end of the input, until the user presses OK.

When the user cancels, `ART-dialogs` exits with status `1` and stops reading, so the program writing to the pipe (typically `ART-cli --progress`) is terminated by `SIGPIPE`. This is how the example below handles cancellation.

### File selection dialogs

`ART-dialogs --file-selection` accepts `--save` (choose a file name to save to), `--directory` (select a folder), `--multiple` (select more than one file; the paths are separated by the `--separator` string, `|` by default), `--filename=PATH` (initial file or folder), `--confirm-overwrite` and one or more `--file-filter="Name | *.ext *.ext2"`. For example:

```bash
out=$(ART-dialogs --file-selection --save --confirm-overwrite \
        --file-filter="TIFF files | *.tif *.tiff" --file-filter="All files | *")
if [ "$out" != "" ]; then
    # the user picked a file name
    ...
fi
```

### Other dialogs

* `--entry` accepts `--entry-text=TEXT` (initial value) and `--hide-text` (for passwords).
* `--list` requires one `--column=NAME` per column, and takes the cell values as additional arguments, row by row. It also accepts `--checklist` or `--radiolist` (the first column then holds `TRUE` or `FALSE` and is displayed as check boxes or radio buttons), `--multiple`, `--print-column=N|ALL` (which column to print, `1` by default), `--hide-column=N`, `--hide-header` and `--separator=STRING`.
* `--scale` accepts `--value=N`, `--min-value=N`, `--max-value=N` and `--step=N`.

## Example

Here is a complete example of a user command that invokes Hugin on the currently selected raw files, after converting them to tiff. The script works on Linux, and assumes that `hugin` is installed and in the `$PATH`. `ART-cli` and `ART-dialogs` are provided by ART itself.

First, we define the following user command `hugin-raw.txt`, putting in in `$HOME/.config/ART/usercommands` (create the directory if it doesn't exist):

```txt
[ART UserCommand]

# the command label
Label=Hugin

# the actual command to execute (which we define below)
Command=./hugin_raw.sh

# we want at least 2 files to stitch
MinArgs=2

# restrict to raw files
FileType=raw

# make sure that all shots come from the same camera/session
MatchCamera=true
MatchLens=true
MatchShutter=true
MatchAperture=true
MatchFocalLen=true
# we could also consider adding additional criteria, like
# MatchISO=true
# MatchDimensions=true
```

The user command definition is quite simple. The bulk of the work is performed by the companion `hugin_raw.sh` script, which will be put in the same directory (`$HOME/.config/ART/usercommands`):


```bash
#!/bin/bash

# create a temporary dir for storing a default processing profile
# and error information
#
# here, we want to make sure we have a suitably large output color space,
# because we want to continue editing after stitching
d=$(mktemp -d)
t=$d/p1.arp
cat <<EOF > $t
[Version]
Version=1015

[Color Management]
OutputProfile=RTv4_ACES-AP1
EOF

if [ -f "$1.arp" ]; then
    # if the first selected file has a sidecar, we are going to use that
    # (except that we override the output profile, see above)
    cp "$1.arp" $d/p2.arp
    sidecar=("-p" "$d/p2.arp")
else
    # if the first selected file has no sidecar, we create a default one 
    sidecar=()
    cat <<EOF >> $t
[Exposure]
HLRecovery=Blend

[ToneCurve]
Enabled=false

[LensProfile]
LcMode=lfauto
LCPFile=
UseDistortion=true
UseVignette=true
UseCA=false

[RAW]
CAEnabled=true
CA=true
CAAvoidColourshift=true
CAAutoIterations=2
EOF
fi

# process the raw files with ART-cli, adding a progress dialog 
# for user notification
ART-cli --progress $fast "${sidecar[@]}" -p $t -Y -t -b16 -c "$@" 2>"$d/error" \
    | ART-dialogs --width=500 --progress --auto-close --text="Converting to TIFF..."

# a non-zero exit status means the user cancelled the operation
if [ $? -ne 0 ]; then
    # if so, we just exit gracefully
    exit 0
fi

# check if there was an error
err=
if [ -f "$d/error" ]; then
    err=$(cat "$d/error")
fi

# remove the temporary dir
rm -rf $d

if [ "$err" != "" ]; then
    # show the error message if something went wrong
    ART-dialogs --error --text="$err"
else
    # otherwise, prepare the list of arguments to provide to hugin. 
    # Note: we are using bash arrays here to be robust wrt. file names
    # with spaces and/or other funny characters
    i=0
    for fn in "$@"; do
        tiffs[$i]="${fn%.*}.tif"
        i=$(expr $i + 1)
    done

    # finally, we can run hugin
    hugin "${tiffs[@]}" || ART-dialogs --error --text="Something went wrong..."
fi
```

## Example for folders

This example adds a *Slideshow* item to the folder tree view context menu. It starts the Gwenview picture viewer in slideshow mode with the selected folder as an argument.

```txt
[ART UserCommand]
Label=Slideshow
Command=gwenview -s
FileType=directory
```
