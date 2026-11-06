# ART and AI-based tools

*A previous version of this page can be found [here](OLDAItools).*

ART does not include AI-based tools, but some of them can be used together with it,
thanks to [SMART](https://github.com/artraweditor/SMART),
a small companion application that provides three AI tools with a graphical interface
(and, for denoising, also a command line),
and to [ART user commands](Usercommands), which make SMART available from the
context menu of the file browser.

## What SMART does

SMART runs open-source neural networks on an image, and saves the result in
a file that ART can then load. It has three modes:

| Mode | What it does | Network | Input |
|---|---|---|---|
| **Masking** (`--mode mask`) | Click on a subject (*shift + left click* to include points, *shift + right click* to exclude them) to get a mask of it, saved as a PNG file that can be loaded in ART as an external mask | [SAM 2.1](https://github.com/facebookresearch/sam2) | an image exported from ART |
| **Healing** (`--mode heal`) | Paint over what you want to remove (dust, objects, blemishes): the area is filled with plausible content ("generative fill") | LaMa inpainting, ported from [greycard](https://github.com/jessolmstead/greycard) | a linear image exported from ART, or any non-raw image |
| **Denoising** (`--mode denoise`) | Removes noise from the raw data, with a before/after view to compare the results | greycard's raw denoiser (Bayer sensors) or the TreeNet models of [RawForge](https://github.com/rymuelle/RawForge) (other sensors), each at three quality levels: *fast*, *balanced*, *best* | a DNG written by `ART-cli` |

The denoiser works on the raw data, before any colour processing.
The result is saved as a linear DNG (or as a linear float TIFF) that ART opens like a raw file,
with its camera matrix, white balance and your usual sidecar settings.
In the before/after view the image is shown with only the display transform applied
(white balance, camera matrix, sRGB encoding): no tone curve and no exposure change.

The denoiser can also be used without the GUI, e.g. in scripts:
see `SMART --mode denoise --cli` and the [SMART documentation](https://github.com/artraweditor/SMART).

## Installing SMART

You can use the pre-built binaries from the [releases page](https://github.com/artraweditor/SMART/releases)
of SMART on GitHub, or install it from the source code as explained below.

The instructions below are for Unix-like systems (Linux, macOS), and I could only test them on macOS.
The integration with ART is done with Python scripts, so nothing should be specific to those systems,
but the details (paths, name of the interpreter) may differ on Windows.

1. Clone the repository:

   ```text
   $ git clone --depth 1 https://github.com/artraweditor/SMART
   ```

2. Create a Python virtual environment, activate it, and install the dependencies
   (the same environment can be shared with other AI tools):

   ```text
   $ python -m venv ART-AI-venv
   $ . ./ART-AI-venv/bin/activate
   $ pip install -r SMART/requirements.txt
   ```

3. Run `python SMART/src/main.py --init-config` from a terminal
   to create an initial configuration file.
   The path to the file will be printed in output.
   Edit it with a text editor, and set the `device` parameter to the device to use for computations:
   `"cuda"` for a CUDA-capable GPU,
   `"mps"` for the GPU on an ARM Apple machine,
   or `"cpu"` otherwise (this might be slow though).

4. Download the models for the tools that you want to use. They are put in the `models/` directory of SMART:

   ```text
   $ python SMART/src/main.py --download-mask-model base_plus    # masking: tiny, small, base_plus or large
   $ python SMART/src/main.py --download-heal-model              # healing
   $ python SMART/src/main.py --download-denoise-model all       # denoising: fast, balanced, best, or all
   ```

   For masking, set also the `model` parameter in the configuration file to the name of the SAM 2 checkpoint
   (`sam2.1_hiera_base_plus.pt` for the example above).
   If a model is missing when SMART starts (or, for denoising, when you press the *Denoise* button),
   SMART offers to download it.

   The masking models are the largest ones (from about 150 MB to 900 MB; larger is better but slower),
   the healing model is about 200 MB, and the denoising models range from a few MB to about 20 MB each.

## Using SMART from ART

The following user commands start SMART on the selected file from the context menu of the file browser
(see [User Commands](Usercommands) for the general mechanism).
They first call `ART-cli` to prepare the image in the right form,
and then open it in SMART, so that you work on what ART would produce.
Progress bars and error messages are shown with [`ART-dialogs`](Usercommands#showing-dialogs-art-dialogs),
which is included with ART (since version 1.26.11).

| Menu entry | User command | Works on | Result |
|---|---|---|---|
| **AI masking (SMART)** | [10_smart_masking.txt](resources/10_smart_masking.txt) | any file | an exported (downscaled) JPEG is opened in SMART; you save the mask as a PNG |
| **AI masking (SMART, full size)** | [11_smart_masking_full.txt](resources/11_smart_masking_full.txt) | any file | as above, at full resolution: slower, but with more precise edges |
| **AI healing (SMART)** | [15_smart_healing_raw.txt](resources/15_smart_healing_raw.txt) | raw files | `FILENAME_healed.tif` |
| **AI healing (SMART)** | [16_smart_healing_nonraw.txt](resources/16_smart_healing_nonraw.txt) | non-raw files | `FILENAME_healed.EXT` |
| **AI denoise (SMART)** | [21_smart_denoise.txt](resources/21_smart_denoise.txt) | raw files | `FILENAME_denoised.dng` |

### Installing the user commands

Each user command is a small text file that starts a companion Python script. Download:

- the user command files in the table above (only those you need);
- the companion scripts [smart_masking.py](resources/smart_masking.py), [smart_healing.py](resources/smart_healing.py)
  and [smart_denoise.py](resources/smart_denoise.py) (again, only the ones you need);
- [art_usercommand.py](resources/art_usercommand.py), with the code shared by all the scripts (always needed),

and put them all in the same directory,
`$HOME/.config/ART/usercommands` (`%LOCALAPPDATA%\ART\usercommands` on Windows).
The numbers at the beginning of the file names only set the order of the entries in the menu.

Then open each script and edit the settings at the beginning of the file to adapt to your environment
(the same two lines are in all of them):

```python
# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where SMART is located
SMART_DIR = Path.home() / "src" / "SMART"
```

The scripts only use the Python standard library, so any Python 3 (3.8 or later) is enough to run them:
SMART itself runs in the virtual environment given by `VENV`.
The `.txt` files start the scripts with the `python3` command:
if your Python interpreter is called differently (e.g. `python` on Windows), edit the `Command` line accordingly.
The denoising command also needs [ExifTool](http://exiftool.org), which must be reachable through the `$PATH`
(it is used to find out what kind of sensor the camera has, and by SMART to copy the metadata to the denoised file).

You should now see the new entries in the context menu of the file browser.

### AI masking

Select an image and choose **AI masking (SMART)**.
ART exports a JPEG (`FILENAME_SMART.jpg`, in the same folder), which is opened in SMART.
Add included points with *shift + left click* and excluded points with *shift + right click*;
then save the mask as a PNG file and load it in ART as an external mask.
The JPEG file is deleted when you quit SMART.
Here's a demo:

- [AI masking demo](demos/ART-AI-masking.mp4)

The "full size" variant exports the image at full resolution:
it is slower, but the edges of the masks are more precise.
The difference between the two commands is the options in the `Command` line of the `.txt` file:
`-f` exports a downscaled image; `--keep` (not used by default) leaves the JPEG file in place
and does not wait for SMART to exit.

### AI healing

For a raw file, ART exports a linear 32-bit TIFF (in the Rec.2020 colour space)
with only the processing that cannot be done on a developed image
(raw preprocessing, highlight recovery, lens correction, geometry, noise reduction, exposure compensation),
and without tone curves or anything else that would clip the image.
This is opened in SMART in healing mode:
paint over what you want to remove with *shift + left drag* (*shift + right drag* erases the paint,
the mouse wheel changes the brush size and *shift + wheel* the feather),
press *Cmd/Ctrl + Enter* to fill the area, repeat as needed (steps can be undone), and save.
The proposed file name is `FILENAME_healed.tif`, in the folder of the original file.
If you save it there, it gets a copy of the sidecar of the original file,
with the settings that were already applied by the export reset,
so that you can continue editing it in ART without applying them twice.
The linear TIFF keeps the full dynamic range, so the rest of the editing can be done on the healed file as usual.

For other kinds of files (JPEG, TIFF, ...), use the non-raw entry: the file is opened directly in SMART,
and the result is saved as `FILENAME_healed.EXT`.

### AI denoising

Select a raw file and choose **AI denoise (SMART)**.
ART converts the file to a DNG, applying only the raw processing steps (hot and dead pixels,
white balance, ...) set in the sidecar of the file.
The DNG is opened in SMART in denoising mode:
choose the model (*fast*, *balanced* or *best*; larger is better but slower) in the toolbar,
and press *Denoise* (or *Cmd/Ctrl + Enter*) to start;
a progress dialog is shown, and the operation can be cancelled.
When it is done, drag the divider of the view to compare the image before and after denoising
(the *View* selector shows either of them alone), and save the result.
The proposed file name is `FILENAME_denoised.dng`, in the folder of the original file;
if you save it there, it gets a copy of the sidecar of the original file,
with the white balance reset to the camera one (it is already applied to the data)
and with the noise reduction of ART turned off.
The file contains linear data, so all the usual processing of ART (tone curves, colour, sharpening, ...)
can be applied on it.

There are two kinds of DNG, depending on the raw file, and the user command chooses automatically
(using ExifTool to find out what kind of sensor the camera has):

- for Bayer raw files (the large majority), ART writes the mosaiced raw data
  (`--raw-preprocess=mosaic`), which are denoised by the *greycard* network,
  that demosaics and denoises at the same time;
- for other raw files (e.g. Fujifilm X-Trans), which that network does not support,
  ART demosaics the image with the method set in the sidecar (`--raw-preprocess=demosaic`),
  and SMART denoises the resulting linear DNG with the *TreeNet* models of RawForge.
  They are conditioned on the ISO of the image, which is read from the file.

The three model choices are the same in both cases.

## Notes

- Everything runs locally: nothing is sent to external services.
  (The only network access is the download of the models.)
- Other AI tools can be integrated in ART in the same way, through user commands:
  see the [previous version of this page](OLDAItools) for denoising with *nind-denoise* and *RawForge*.
