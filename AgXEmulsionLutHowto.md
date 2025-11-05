# Spectral film simulations in ART with *agx-emulsion*

*(contributed by Leopoldo Saggin and Sébastien Guyader)*

Recently [*arctic*](https://discuss.pixls.us/u/arctic/summary) released [***agx-emulsion***](https://github.com/andreavolpato/agx-emulsion), a physics-based simulation of color film photography processing.

[Alberto Griggio](https://discuss.pixls.us/u/agriggio) decided to extend [**ART**](https://artraweditor.github.io/) and make possible to integrate *agx-emulsion* as an additional type of **3dLUT**, similarly in concept to what is already possible with *CTL scripts*.

Here, we describe the *installation of agx-emulsion* and its *integration in ART* using **Microsoft Windows, MacOS** and **Linux** so you can play with it, in case you are interested.

## 1. Installing *pipx* and *virtualenv* {#virtualenv-install}

Since *agx-emulsion* relies on Python, the use of a virtual environment for Python is recommended. Here we will describe how to install and use `virtualenv` which is a fast, cross-platform tool for managing isolated Python environments which allow installing and running different versions of Python.

In case you don't have Python installed already, install a recent version (from <https://www.python.org/> for example). If your Python version is \< 3.8, please update.

**Note for Windows users:** it seems like the current version of Python at the time of writing (version 3.14) prevents installing Python 3.11 from the `virtualenv`. It is suggested to directly install Python 3.11 as the main Python version on your system.

Now you can install `pipx` for your OS from here: <https://pipx.pypa.io/stable/installation/>.

To install *virtualenv*, run the following commands in a terminal (for Windows, **cmd.exe** or **PowerShell**):

```         
pipx install virtualenv
pipx ensurepath
```

Now close your terminal window, open a new terminal and create the virtual environment for *agx-emulsion*.

For Windows:

```         
virtualenv --python 3.11 c:\users\<username>\envs\agx-emulsion
```

For MacOS/Linux:

```         
virtualenv --python 3.11 ~\envs\agx-emulsion
```

This will create a new `envs` folder in your home user directory, of course you can change it to the path/forlder name you like but don't forget to update the following commands.

## 2. Installing and preparing *agx-emulsion* {#agx-emulsion-install}

### **Activating the *agx-emulsion*** environment

For **Windows**:

-    if you use **cmd.exe** type:

```         
c:\users\<username>\envs\Scripts\activate.bat
```

-   if you use **PowerShell**:

```         
c:\users\<username>\envs\Scripts\Activate.ps1
```

For **MacOS/Linux**:

```         
source ~/envs/agx-emulsion/bin/activate
```

Once the agx-emulsion environment is activated, you will see `(agx-emulsion)` displayed in the command prompt.

### **Dowloading the *agx-emulsion*** **code**

If *Git* is installed on your operating system, clone the *agx-emulsion* repository:

``` bash
git clone https://github.com/andreavolpato/agx-emulsion.git /path/to/local/agx-emulsion
```

Otherwise you can manually download a zip/tarball snapshot of *agx-emulsion* from its [github repository](https://github.com/andreavolpato/agx-emulsion/), and extract its content to `/path/to/local/agx-emulsion`.

### Installing *agx-emulsion*

With the `(agx-emusion)` environment active in your terminal, type:

``` bash
cd /path/to/local/agx-emulsion
pip install -e .
```

And launch the GUI:

``` bash
agx-emulsion
```

If everything went well, a window should pop up which will let you experiment with *agx-emulsion*. For instance, you can load the provided test image (located in `/path/to/local/agx-emulsion/img/test`) or any image of your choice and play with the film and print emulsions to ensure the module works.

![*agx-emulsion* native GUI](resources/agx-emulsion-napari-GUI.png)

## 3. *agx-emulsion* integration in ART {#agx-emusion-art-integration}

Integration of *agx-emulsion* in ART has started since [commit 22fe47d](https://github.com/artpixls/ART/commit/22fe47d2a4b5f72c7895ddd0cf7cfddaaabf3cfe) and is available since [release 1.25.3](https://github.com/artpixls/ART/releases/tag/1.25.3).

In order to use the module in ART, download the support scripts:

[ART_agx_film.json](https://github.com/artpixls/ART/raw/refs/heads/master/tools/extlut/ART_agx_film.json)

[agx_emulsion_mklut.py](https://github.com/artpixls/ART/raw/refs/heads/master/tools/extlut/agx_emulsion_mklut.py)

and save them *both in the same directory* of your choice. **It is crucial that both files reside in the same directory**.

***Note:*** the most convenient place to save both files is the 3D LUT directory declared in ART's **Preferences \> Image Processing \> Directories \> CLUT directory**.

***ART_agx_film.json*** is a configuration file which sets the Python command to run the script ***agx_emulsion_mklut.py***. By default the command is:

``` json
    "command" : "python3 agx_emulsion_mklut.py --server",
```

Since the actual command depends on your operating system and Python install environment, you need to open it with a text editor and edit **line 12** to point to the *Python interpreter* you used to install *agx-emulsion*.

If you followed the instructions above to install *virtualenv* and Python 3.11, you will need to update this command with:

(for Windows)

``` json
    "command" : "C:\\users\\<username>\\envs\\agx-emulsion\\bin\\python agx_emulsion_mklut.py --server",
```

(for Linux and MacOS)

``` json
    "command" : "/home/<username>/envs/agx-emulsion/bin/python agx_emulsion_mklut.py --server",
```

and save the file. Please also note the presence of a "**comma**" at the end of the line!

Now when you restart ART you should be able to load ***ART_agx_film.json*** as a **LUT** from the "*Color/Tone Correction*" tool in the "Local editing" tab, or from the "Film Simulation" tool in the "Special Effects" tab.

At this point you can test if everything works:

1.  Open an image in ART
2.  Activate the "*Color/Tone Correction*" tool and, from its "*Mode"* dropdown menu select **LUT** (note that default mode is generally *Standard* or *Perceptual*)
3.  The program will ask for a *LUT file*
4.  Select ***ART_agx_film.json***
5.  At this point a large set of parameters appears, as reported in the image below, and you can play and choose the film simulation you wish to simulate etc...

![*agx-emulsion* module in ART](resources/agx-emulsion-lut.png)

## 4. Updating *agx-emulsion* {#agx-emulsion-updating}

In order to keep both the ***agx-emulsion*** Python code base and its support in ART up to date:

1.  update your local agx-emulsion repo (though *git* or by extracting a zip/tarball) and refer to the second command in the [agx-emulsion section](#agx-emulsion-installation) above
2.  download the ***agx_emulsion_mklut.py*** and ***ART_agx_film.json*** files from <https://github.com/artpixls/ART/tree/master/tools/extlut> again, and replace the existing files in ART's **CLUT directory** with the new ones.

**Disclaimer**

All the information provided on this document is provided on an "*as-is*" basis and you agree that you use such information entirely at *your own risk*. We give *no warranty* and accept *no responsibility or liability for the accuracy or the completeness of the information contained in this document*. Under no circumstances will we be held responsible or liable in any way for any claims, damages, losses, expenses, costs or liabilities whatsoever (including, without limitation, any direct or indirect damages for loss of profits, business interruption or loss of information) resulting or arising directly or indirectly from your use of or inability to use this document.

Leopoldo Saggin aka **Topoldo** [leopoldo.saggin\@yahoo.com](mailto:leopoldo.saggin@yahoo.com)

[Sébastien Guyader](https://discuss.pixls.us/u/sguyader)

Version 0.3 **2025/04/28**
