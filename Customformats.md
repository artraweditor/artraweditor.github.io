# Adding Support for Custom Image Formats

Since version 1.6, ART provides the ability to add reading and writing support
for additional image formats via a simple plugin mechanism.

Similarly to [User Commands](Usercommands), the mechanism is based on interacting with external programs defined using configuration files,
where an external handler is a program that converts to/from files in one of the supported formats.

Until version 1.25.8, only non-raw image formats could be added.
Starting from version 1.25.9, it is now possible to add also support
for external raw decoders.

## How to define custom image handlers

Image handlers are simple text files in the same syntax used by the `arp` sidecar files (but with `.txt` extension), 
placed in the `imageio` subdirectory directory of ART config folder (typically `$HOME/.config/ART` on Linux and `%LOCALAPPDATA%\ART` on Windows),
that must comply with the specifications below.

### Non-raw formats

- They must contain a single group of options, called `[ART ImageIO]`

- They must include the following mandatory definitions:

    * `Extension`: the (case-insensitive) file extension of the image type handled.

- and at least one of the following definitions:

    * `ReadCommand`: the command used for loading images of the given type. The path can be either absolute or relative to the current directory; the command can also contain extra arguments (the input files will be appended to the list of arguments); The command will be called with the following arguments:

        - `input_file`: path to the image to read
        - `output_file`: path to the file to generate.
        - `width_hint`: (optional), a *hint* about the desired image width. This can be used to optimize the reading, assuming that the image will be resized to be at most `width_hint` pixels wide. If absent or zero, then the image is needed at its maximum resolution. The command is free to ignore the hint and always return the fullsize image.
        - `height_hint`: (optional), analogous to `width_hint` above.

    * `WriteCommand`: the command used for saving images of the given type. It will be called with the following arguments:

        - `input_file`: path to a 32-bit float tiff representation of the image to generate.
        - `output_file`: path to the file to generate.

- Furthermore, they can also include the following optional definitions:

    * `Format`: the format to use for the intermediate files used to communicate with ART. Possible values are:

        - `jpg`: JPEG
        - `png`: 8-bit PNG
        - `png16`: 16-bit PNG
        - `tiff`: 16-bit integer TIFF
        - `float`: 32-bit floating-point TIFF (default)

    * `Label`: A short description of the image format to be used in the GUI for selecting the given output type. If absent, the uppercase version of `Extension` will be used.

    * `SaveFormat`: an alphanumeric unique identifier for the command used for save operations. By default, this is the same as `Extension`. Having a separate `SaveFormat` allows to define multiple savers for the same file extension, e.g. to support different saving modes.

    * `SaveProfile`: path to a (partial) `.arp` profile to be applied automatically before saving in the format being defined. This can be used e.g. to force a specific output profile when saving in the format being defined. If not absolute, the path will be interpreted relative to the directory containing the `.txt` file.

### Raw formats

- They must contain a single group of options, called `[ART RAWImageIO]`

- They must include the following mandatory definitions:

    * `Extension`: the (case-insensitive) file extension of the image type handled.

    * `ReadCommand`: the command used for decoding raw images of the given type. The path can be either absolute or relative to the current directory; the command can also contain extra arguments (the input files will be appended to the list of arguments); The command will be called with the following arguments:

        - `input_file`: path to the image to read
        - `output_file`: path to the file to generate.

      The command is expected to produce an `output_file` in [DNG](https://helpx.adobe.com/camera-raw/digital-negative.html) format.

- Furthermore, they can also include the following optional definitions:

    * `Make`: the name of the camera manufacturer producing the images that should be decoded with this handler, as stored in the exif metadata (case insensitive).

    * `Model`: the name of the camera model producing the images that should be decoded with this handler, as stored in the exif metadata (case insensitive).

### Controlling which handlers are loaded and their order

By default, all the `.txt` files in the `imageio` directory are loaded, sorted by file name.
Since ART version 1.26.11, this can be customized by putting in the same directory a text file called `ARTlist.txt`
(the name is matched case-insensitively), in the same way as for [LUTs and CTL scripts](Luts#artlist) and [user commands](Usercommands).
If present, the file determines which handler files are loaded, and in which order.

The file contains one file name per line (relative to the `imageio` directory, or an absolute path).
Anything starting with a `#` and up to the end of the line is ignored, and so are blank lines. For example:

```
# my handlers
heic.txt
webp.txt     # trailing comments are fine
```

Handler files not listed are ignored. Duplicates and entries that do not exist are skipped.
If several handlers are defined for the same extension, the one loaded last wins, so the order in `ARTlist.txt` also decides which one is used.
The `ARTlist.txt` file is looked for separately in the `imageio` directory shipped with ART and in the one in the ART config folder.

**NOTE**: you should also add the appropriate extension to the preferences (in Preferences -> File Browser -> Parsed Extensions) in order for ART to show the pictures in the file browser.

## Example

Here is a complete example of a handler for [HEIC](https://en.wikipedia.org/wiki/High_Efficiency_Image_File_Format#HEIC:_HEVC_in_HEIF) images that exploits [libheif](http://www.libheif.org/) and Exiftool. The script works on Linux, and assumes that `heif-thumbnailer`, `heif-convert`, `heif-enc` and `exiftool` installed and in the `$PATH`.

First, we define the following handler `heic.txt`, putting in in `$HOME/.config/ART/imageio` (create the directory if it doesn't exist):

```txt
[ART ImageIO]

# the file extension of the type handled
Extension=heic

# communicate via 16-bit PNG files
Format=png16

# the command for loading
ReadCommand=./heif-io.sh load

# the command for saving
WriteCommand=./heif-io.sh save

# the label for the GUI
Label=HEIC (via libheif)
```

The bulk of the work is performed by the companion `heif-io.sh` script, which will be put in the same directory (`$HOME/.config/ART/imageio`):


```bash
#!/bin/sh

mode=$1
shift

if [ "$mode" = "load" ]; then
    # loading: convert from the input to a png
    # resize if hints are given
    if [ "$4" != "" -a "$3" != "0" -a "$4" != "0" ]; then
        heif-thumbnailer -s "$3x$4" "$1" "$2"
    else
        heif-convert -q 100 "$1" "$2"
    fi
    test -f "$2"
elif [ "$mode" = "save" ]; then
    # saving: convert from 16-bit png to the output
    heif-enc -o "$2" "$1"
    if [ -f "$2" ]; then
        # copy also the metadata with exiftool
        exiftool -tagsFromFile "$1" -overwrite_original "$2"
    fi
    test -f "$2"
else 
    # unknown operating mode, exit with error
    echo "Unknown operating mode \"$mode\"!"
    exit 1
fi
```

### Python Version

Here is the same example handler above written in Python, which might be more suitable for Windows users. It assumes that all the applications (Python, the libheif tools and exiftool) are in the `%PATH%` (Windows binaries for libheif tools can be downloaded from [here](https://github.com/pphh77/libheif-Windowsbinary)):

```txt
[ART ImageIO]

# the file extension of the type handled
Extension=heic

# communicate via 16-bit PNG files
Format=png16

# the command for loading
ReadCommand=python ./heif-io.py load

# the command for saving
WriteCommand=python ./heif-io.py save

# the label for the GUI
Label=HEIC (via libheif)
```

```python
import os, subprocess, argparse

def getopts():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["load", "save"])
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("maxwidth", type=int, nargs='?', default=0)
    p.add_argument("maxheight", type=int, nargs='?', default=0)
    return p.parse_args()


def main():
    opts = getopts()

    if opts.mode == "load":
        if opts.maxwidth > 0 and opts.maxheight > 0:
            subprocess.run([
                "heif-thumbnailer",
                "-s", "%sx%s" % (opts.maxwidth, opts.maxheight),
                opts.input, opts.output], check=True)
        else:
            subprocess.run([
                "heif-convert",
                "-q", "100",
                opts.input, opts.output], check=True)            
    else: # opts.mode == "save"
        subprocess.run(["heif-enc", "-o", opts.output, opts.input], check=True)
        subprocess.run(["exiftool", "-tagsFromFile", opts.input,
                        "-overwrite_original", opts.output])


if __name__ == "__main__":
    main()
```

## Another Example

Here is another example, using [ImageMagick](https://imagemagick.org/) to perform the conversion. In this case, we can handle multiple custom formats with the same script, simply by defining multiple `.txt` files with the proper parameter. 
For example, here is one for WebP (let's call it `webp.txt`, and put it in `$HOME/.config/imageio`):

```txt
[ART ImageIO]
Extension=webp
ReadCommand=./magick-io.sh load
WriteCommand=./magick-io.sh save
Label=WebP (via ImageMagick)
```

And here is another one for [EXR](https://www.openexr.com/) (let's call it `exr.txt`):

```txt
[ART ImageIO]
Extension=exr
ReadCommand=./magick-io.sh load
WriteCommand=./magick-io.sh save
Label=EXR (via ImageMagick)
```

In both cases, we call the same `magick-io.sh` script:

```bash
#!/bin/bash

mode=$1
shift

if [ "$mode" = "load" ]; then
    # loading: convert from the input to a floating-point tiff file
    # resize if hints are given
    sz=""
    if [ "$4" != "" -a "$3" != "0" -a "$4" != "0" ]; then
        sz="-thumbnail $3x$4"
    fi
    
    magick convert "$1" $sz -colorspace sRGB -define quantum:format=floating-point -depth 32 -compress none "$2"
    test -f "$2"
elif [ "$mode" = "save" ]; then
    # saving: convert from floating-point tiff to the output
    magick convert "$1" "$2"
    if [ -f "$2" ]; then
        # copy also the metadata with exiftool
        exiftool -tagsFromFile "$1" -overwrite_original "$2"
    fi
    test -f "$2"
else 
    # unknown operating mode, exit with error
    echo "Unknown operating mode \"$mode\"!"
    exit 1
fi
```

(**NOTE:** this assumes that you have a version of ImageMagick that is properly configured to handle WebP and EXR, of course.)

## Raw decoder example

Here is an example using the free [GPR tools](https://github.com/gopro/gpr) to decode GPR files of recent GoPro cameras.
We first define the handler (let's call it `raw-gpr.txt`) and put it in `$HOME/.config/imageio`:

```txt
[ART RAWImageIO]
Extension=gpr
ReadCommand=python3 ./load_gpr_raw.py
```

The handler uses the following `load_gpr_raw.py` Python script, which in turn calls `gpr_tools` from the link above to perform the conversion to DNG (the script assumes that the `gpr_tools` executable is in the path:

```python
import subprocess, sys

subprocess.run(['gpr_tools', '-i', sys.argv[1], '-o', sys.argv[2]], check=True)
```


## A repository for custom image handlers

A collection of cross-platform image handlers is available [in this repository](https://github.com/artraweditor/ART-imageio/).
