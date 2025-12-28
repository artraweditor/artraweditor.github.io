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

## Example

Here is a complete example of a user command that invokes Hugin on the currently selected raw files, after converting them to tiff. The script works on Linux, and assumes that `hugin`, `ART-cli` and `zenity` are installed an in the `$PATH`.

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
    | zenity --width=500 --progress --auto-close --text="Converting to TIFF..."

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
    zenity --error --text="$err"
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
    hugin "${tiffs[@]}" || zenity --error --text="Something went wrong..."
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
