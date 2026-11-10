# ART and AI-based tools

Some people asked about integration of AI-based tools in ART.
While a full integration won't likely happen in the fureseeable future
(I would recommend to people who consider this critical to take a look at [RapidRAW](https://github.com/CyberTimon/RapidRAW)),
some level of integration of both AI-based masking and AI-based denoising is already possible,
thanks to the use of some open source projects to do the heavy work,
and some glue code in the form of [ART user commands](https://artraweditor.github.io/Usercommands).
In this article,
I'd like to show how to do that for Unix-based systems
(and possibly also on windows using msys2 or WSL2).

## AI-based denoising

We can use [nind-denoise](https://github.com/trougnouf/nind-denoise) or
[RawForge](https://github.com/rymuelle/RawForge)
to perform advanced noise reduction with neural networks.
In order to integrate them with ART, we can use the attached user commands and companion scripts:

- [nind_denoise.txt](resources/nind_denoise.txt) and [nind_denoise_raw.py](resources/nind_denoise_raw.py) for "nind-denoise"; or
- [rawforge_denoise.txt](resources/rawforge_denoise.txt) and [rawforge_denoise.py](resources/rawforge_denoise.py) for "RawForge"; or

The scripts show progress bars and error messages with
[`ART-dialogs`](Usercommands#showing-dialogs-art-dialogs),
which is included with ART (since version 1.26.11)
and is found automatically when the scripts are run as ART user commands.

The companion scripts are written in Python, so that they are not tied to a specific platform.
They only use the Python standard library, so any Python 3 (3.8 or later) will do to run them:
the AI tools themselves run in their own virtual environments, as explained below.
The `.txt` files start the scripts with the `python3` command:
if your Python interpreter is called differently (e.g. `python` on Windows),
edit the `Command` line accordingly.
(I could only test the scripts on macOS, but nothing in them should be specific to it.)

All the files should be placed in `$HOME/.config/ART/usercommands`
(`%LOCALAPPDATA%\ART\usercommands` on Windows).
The settings at the beginning of the scripts need to be modified to point to the installation directory of 
the respective denoiser.
Some installation instructions appear below.


### nind-denoise configuration

#### Installation

1. clone the repository (I'm using my fork of the original code, whose only change is to allow more devices to be selected, other than NVida-based GPUs or CPU as the original):

   ```text
   $ git clone --depth 1 https://github.com/agriggio/nind-denoise
   ```

2. create a Python virtual env, activate it, and install the required dependencies:

   ```text
   $ python -m venv ART-AI-venv
   $ . ./ART-ai-venv/bin/activate
   $ pip install torch torchvision ConfigArgParse opencv-python pyyaml piqa 
   ```

#### ART user command configuration

Open `nind_denoise_raw.py` and edit the settings at the beginning of the file to adapt to your environment:

```python
# select the device to use for denoising (cuda, mps, cpu, ...)
DEVICE = "mps"

# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where nind-denoise is located
NIND_DENOISE_DIR = Path.home() / "src" / "nind-denoise"
```

#### Testing that it works

You should have a new user command called "AI denoise (nind-denoise)". If everything is configured properly, activating it should result in an image `FILENAME-denoised.tif` generated in the current directory (when invoked on a file called `FILENAME.raw`).

### RawForge configuration

#### Installation

Follow the instructions on the [https://github.com/rymuelle/RawForge](GitHub RawForge page), 
creating a suitable Python virtual env (below, I will assume 
it is called `rawforge-venv`, and is installed in `$HOME/src`;
 if your setup is different, adjust accordingly).
The `rawforge_denoise.py` requires also [ExifTool](http://exiftool.org), 
so make sure it is available on your `$PATH`.

#### ART user command configuration

Open `rawforge_denoise.py` and edit the settings at the beginning of the file to adapt to your environment:

```python
# Python virtual environment where RawForge is installed
VENV = Path.home() / "src" / "rawforge-venv"

# RawForge model to use
MODEL = "TreeNetDenoiseLight"

# select the device to use for denoising (cuda, mps, cpu, ...); by default,
# RawForge picks the best one
DEVICE = None
```

The script runs itself with the Python interpreter of this virtual environment
(with the `--worker` option) to perform the actual denoising.

#### Testing that it works

You should have a new user command called "AI denoise (RawForge)". 
If everything is configured properly, activating it should result in an image 
`FILENAME-denoised.dng` generated in the current directory
 (when invoked on a file called `FILENAME.raw`).


## AI masking (Unix-like environments)

We can use [SAM2](https://github.com/facebookresearch/sam2)
through its [SMART](https://github.com/artraweditor/SMART) GUI frontend
to quickly generate masks of various subjects in the scene.

Similarly to nind-denoise, we will integrate it with ART via the attached
`smart_masking.txt` user command and `smart_masking.py` companion script
(see above for how these are started and where to put them).
The script needs to be modified to point to the installation directory of SMART,
which can be installed as explained below.

- [smart_masking.txt](resources/smart_masking.txt)
- [smart_masking.py](resources/smart_masking.py)


### SMART installation

1. clone the repository:

   ```text
   $ git clone --depth 1 https://github.com/artraweditor/SMART
   ```

2. Activate the previously-created Python virtual env, and install the required dependencies:

   ```text
   $ . ./ART-ai-venv/bin/activate
   $ pip install -r SMART/requirements.txt 
   ```

3. Download one of the SAM 2 model checkpoints from [https://github.com/facebookresearch/sam2?tab=readme-ov-file#download-checkpoints](https://github.com/facebookresearch/sam2?tab=readme-ov-file#download-checkpoints), and put it in the `models/` directory of SMART.

4. Run `python src/main.py --init-config` from a terminal
to create an initial configuration file.
The path to the file will be printed in output.
Edit the file with a text editor, and adapt the `model` and `device` parameters to your setup,
where `model` should be the name of the SAM2 checkpoint to use,
and `device` the device to use for computations:
`"cuda"` for a CUDA-capable GPU,
`"mps"` for the GPU on an ARM Apple machine,
or `"cpu"` otherwise (this might be slow though).

### ART user command configuration

Open `smart_masking.py` and edit the settings at the beginning of the file
to adapt to your environment:

```python
# Python virtual environment to use
VENV = Path.home() / "src" / "ART-AI-venv"

# directory where SMART is located
SMART_DIR = Path.home() / "src" / "SMART"
```

The user command passes two options to the script (see the `Command` line in `smart_masking.txt`):
`-f` makes ART export a downscaled image, which is faster
(remove it to work on the full-resolution image, which is slower but keeps the mask edge artifacts to a minimum),
and `--keep` leaves the exported JPEG file next to the original and does not wait for SMART to exit
(without it, SMART runs in the foreground and the JPEG file is deleted when SMART exits).

### Testing that it works

You should have a new user command called "AI masking (SMART)".
If everything is configured properly, activating it should result in an image
`FILENAME_SMART.jpg` generated in the current directory
(when invoked on a file called `FILENAME.ext`) and opened in the SMART gui.
You can then quickly create masks by adding included (with shift + left-click)
and excluded (with shift + right-click) points,
and then save it as a png file.
The file can be then loaded in ART as an external mask.


## AI masking (Windows environment)

*Contributed by Alexander Patrakov*

SMART has pre-built portable releases for Windows (x64). Download [release v0.2](https://github.com/artraweditor/SMART/releases/download/0.2/SMART-0.2-win64-portable.7z), which, at the time of this writing, is the latest version.


Extract it under `%LOCALAPPDATA%`. That is, press Win+R, type `"%LOCALAPPDATA%"` in the address bar (with the surrounding quotes), press Enter, and then extract the archive into the folder that opens.

Navigate to the resulting `SMART-0.2-win64-portable` folder. Download one of the [SAM 2 model checkpoints](https://github.com/facebookresearch/sam2?tab=readme-ov-file#download-checkpoints) and put it in the `models` subdirectory.

Then run the `SMART.exe` program. It will create a configuration file, `artpixls-SMART.json`, in `%LOCALAPPDATA%`. Edit it using Notepad and adjust the `"model"` value to match the model you downloaded. For example:

```
  "model": "sam2.1_hiera_base_plus.pt",
```

Check that the `"device"` value is set to `"cpu"`.

Then go to the `"%LOCALAPPDATA%\ART"` folder. Create the `usercommands` subfolder if it doesn't exist. Then, place two files there:

- [`smart_masking.ps1`](resources/smart_masking.ps1)
- [`smart_masking_windows.txt`](resources/smart_masking_windows.txt)

