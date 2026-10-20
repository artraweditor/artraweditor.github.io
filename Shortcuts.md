# Keyboard Shortcuts in ART

Almost all the keyboard shortcuts of ART can be changed or disabled, and the
modifier key that they use (Ctrl by default) can be switched to the Cmd key on
macOS or the Windows key on other systems. The [first part](#customising-the-shortcuts)
of this page explains how; the [second part](#default-shortcuts) lists the
shortcuts that ART uses out of the box.

## Customising the shortcuts

### The Keyboard Shortcuts tab of the Preferences

Open *Preferences* and select the **Keyboard Shortcuts** tab. It shows all the
actions that have a shortcut, as a tree grouped by area (*Editor*, *File
Browser*, *Queue*, ...), with the current shortcut of each action. Select an
action and use the buttons below the tree:

- **Change...** (or double-click the action) asks you to press the new shortcut,
  which *replaces* the current one(s). Press **Esc** to give up.
- **Add key...** does the same, but adds the new shortcut to the existing ones:
  an action can have more than one.
- **Disable** removes all the shortcuts of the action.
- **Reset** goes back to the standard shortcut(s) of the action, and **Reset
  all** does that for every action (and for the modifiers described below).

The shortcuts that you changed are shown in **bold**. The search box above the
tree finds actions by name or by shortcut (for instance type `zoom` to see all
the zoom actions); press **Esc** in the box to clear the search. Clearing it keeps the
action that you had selected, and shows it in the tree.

Nothing is saved until you press **OK**, and the new shortcuts are used the
next time ART is started.

### The primary modifier and the mouse modifier

Two choices below the tree control the modifier keys:

- **Primary modifier of the shortcuts.** Most shortcuts use the "primary"
  modifier, which is **Ctrl** by default (Ctrl-s to save, Ctrl-z to undo, ...).
  You can change it to **Cmd** on macOS, or to the **Windows key** on other
  systems: all the shortcuts that use it follow, so Ctrl-s becomes Cmd-s,
  Ctrl-z becomes Cmd-z, and so on. A shortcut that you assigned explicitly with
  Ctrl (while the primary modifier is the Cmd or Windows key) stays on Ctrl.
- **Modifier of the mouse actions.** The actions that combine a key with the
  mouse (Ctrl-click to reset a slider, Ctrl-click on the save and queue buttons
  for a fast export, Ctrl-click to extend a selection in the file browser,
  Ctrl-drag in the crop, curve, mask and spot tools, ...) have their own setting,
  which is Ctrl by default and can be changed to the Cmd or Windows key
  independently of the primary modifier. This is useful on macOS, where
  Ctrl-click is also a right click. The tooltips of ART follow your choice.

While the primary modifier is Ctrl, a key pressed together with Cmd or the
Windows key never triggers a shortcut (Cmd-z is not taken for a plain *z*).

### Conflicts and shortcuts reserved by the system

When you assign a shortcut that is already in use, ART asks what you want to
do:

- if the other action is in the same place (for instance two actions of the
  editor), you can **reassign** the shortcut, taking it away from the other
  action, or cancel;
- if the other action is not in the same place but can be active at the same
  time (a window-wide shortcut such as *quit* or *close tab*, or an action of
  the same tab), you can also choose **Keep both**: only one of the two will
  react to the key;
- on macOS, ART also warns you if the shortcut is one that the system uses
  (Mission Control, Spotlight, screenshots, `Cmd-,` for the preferences, ...),
  since the system may take the key before ART can see it. You can still
  **Assign anyway**: the check depends on your system settings (see *System
  Settings > Keyboard > Keyboard Shortcuts*).

When you switch the primary modifier to Cmd on macOS, ART checks all the
shortcuts that use it, and asks, one by one, what to do with the ones that the
system reserves: **Keep it**, **Choose another key...**, **Disable** it, or **Go
back to Ctrl**, which cancels the change.

### Editing the shortcuts file

Everything that the Preferences tab does is stored in a text file called
`shortcuts.json` in the ART configuration folder (the one that contains the
`options` file; typically `$HOME/.config/ART` on Linux and macOS and
`%LOCALAPPDATA%\ART` on Windows), which you can also edit by hand. Each time
ART starts, it writes the file `shortcuts_reference.json` in the same folder,
which lists *all* the actions with their standard shortcuts and describes the
syntax: copy the entries that you want to change into `shortcuts.json` (the file
is created if it doesn't exist) and restart ART. For example:

```
{
    "version": 1,

    // "Ctrl" (the default), or the OS key: "Cmd" on macOS, "Super" (the Windows key) elsewhere
    "primary_modifier": "Ctrl",
    "mouse_primary_modifier": "Ctrl",

    "bindings": {
        // replace the shortcut of an action
        "editor.undo": ["Primary+Alt+Z"],
        // more than one shortcut is fine
        "editor.redo": ["Primary+Shift+Z", "Primary+Y"],
        // an empty list disables the shortcut
        "filebrowser.rename": []
    }
}
```

- Only the actions listed in the file change: all the others keep their
  standard shortcuts. An action that is listed *replaces* all of its standard
  shortcuts.
- A shortcut is written `[Primary+][Ctrl+][Alt+][Shift+]<key>`, where `<key>` is
  the name of the key: a letter or digit (`z`, `5`), `F3`, `Delete`, `Return`,
  `space`, `Left`, `Page_Down`, ... Characters that are hard to type are spelled
  out: `plus`, `minus`, `equal`, `less`, `greater`, `comma`, `period`, `slash`,
  `asterisk`, `underscore`, `bracketleft`, `bracketright`. Write the Shift
  explicitly for letters and digits (`Shift+R`). The modifiers must match
  exactly: `Primary+S` does not fire for `Primary+Shift+S`.
- `Primary` is whichever key you chose as the primary modifier (Ctrl by
  default). `Ctrl` is always the physical Control key, which is the same as
  `Primary` as long as the primary modifier is Ctrl.
- Comments (`// ...`) are allowed. Saving from the Preferences rewrites the
  file and does not keep them: the previous version is saved once as
  `shortcuts.json.bak`.
- Problems in the file (an unknown action, a key that cannot be read, a key that
  another action of the same place already uses) are reported on the standard
  error and the entry is ignored: ART always starts. If you start ART from a
  terminal with the environment variable `ART_SHORTCUTS_DEBUG=1`, it also prints
  which action each key press triggers.

## Default shortcuts

These are the shortcuts that ART uses unless you change them. **Ctrl** stands
for the primary modifier: it is Ctrl by default, or the Cmd or Windows key if you
chose it as described above. The shortcuts of the same area that use the same
key are valid in different situations (for instance **l** shows the left panel in
both the editor and the file browser).

Some shortcuts are only valid in some contexts, which are given in the
*Where* column.

### Anywhere

| Where    | Shortcut          | Action                                              |
|----------|-------------------|-----------------------------------------------------|
| Anywhere | **F11**           | Toggle full screen.                                 |
| Anywhere | **Ctrl-w**        | Close the current editor tab.                       |
| Anywhere | **Ctrl-q**        | Quit ART.                                           |
| Anywhere | **Ctrl-F2**       | File browser.                                       |
| Anywhere | **Ctrl-F3**       | Processing queue.                                   |
| Anywhere | **Ctrl-F4**       | Editor.                                             |

### Editor

| Where  | Shortcut                                     | Action |
|--------|----------------------------------------------|--------|
| Editor | **m**                                        | Show/hide all side panels. |
| Editor | **Shift-m**                                  | Show/hide all side panels and fit the image to the screen. |
| Editor | **l**                                        | Show/hide the left panel (including the history). |
| Editor | **Ctrl-l**                                   | Show/hide the right panel. |
| Editor | **Alt-l**                                    | Show/hide the left and right panels. |
| Editor | **Shift-l**                                  | Show/hide the top panel. |
| Editor | **9**                                        | Cycle the background color of the preview: theme-based, black, white, middle grey. |
| Editor | **Shift-i**                                  | Quick info on the image. |
| Editor | **Shift-a**                                  | Toggle the **Before**/**After** view. |
| Editor | **Ctrl-z**                                   | Undo. |
| Editor | **Ctrl-Shift-z**, **Ctrl-y**                 | Redo. |
| Editor | **Alt-s**                                    | Create a new snapshot. |
| Editor | **Ctrl-,**, **Ctrl-.**                       | Show the previous / next snapshot. |
| Editor | **Ctrl-g**                                   | Show/hide the grid. |
| Editor | **Ctrl-s** (**Ctrl-Shift-s** for fast export) | Save the current image (Ctrl-click the button for fast export). |
| Editor | **Ctrl-b** (**Ctrl-Shift-b** for fast export) | Put the current image in the processing queue (Ctrl-click the button for fast export). |
| Editor | **Ctrl-e** (**Ctrl-Shift-e** for fast export) | Edit the current image in an external editor (Ctrl-click the button for fast export). |
| Editor | **Shift-F3**, **Shift-F4**                   | Open the previous / next image relative to the image opened in the Editor. |
| Editor | **F3**, **F4**                               | Open the previous / next image relative to the currently selected thumbnail in the File Browser or Filmstrip. |
| Editor | **x**                                        | Synchronize the File Browser or Filmstrip with the Editor, to reveal the thumbnail of the currently opened image, clearing any active filters. |
| Editor | **y**                                        | As above, but without clearing the active filters (the thumbnail of the opened image will not be shown if it is filtered out). |
| Editor | **[**, **]**                                 | Rotate left / right. |
| Editor | **Ctrl-Up**, **Ctrl-Down**, **Ctrl-Left**, **Ctrl-Right** | Move the image in the preview (also with the numeric keypad arrows). |

### Editor: zoom and previews

| Where  | Shortcut        | Action |
|--------|-----------------|--------|
| Editor | **z**           | Zoom to 100%. |
| Editor | **f**           | Fit the whole image (or the crop) to the screen. |
| Editor | **+**, **=**    | Zoom in. |
| Editor | **-**, **_**    | Zoom out. |
| Editor | **>**           | Clipped highlight indication. |
| Editor | **<**           | Clipped shadow indication. |
| Editor | **Shift-e**     | Toggle exposure indication using false color. |
| Editor | **Shift-r**     | Preview the **red channel**. |
| Editor | **Shift-g**     | Preview the **green channel**. |
| Editor | **Shift-b**     | Preview the **blue channel**. |
| Editor | **Shift-v**     | Preview the **luminosity**. |
| Editor | **Shift-f**     | Preview the **focus mask**. More accurate on images with shallow depth of field, low noise and at higher zoom levels; zoom out to 10-30% to improve detection accuracy on noisy images. |
| Editor | **Shift-o**     | Preview the **sharpening contrast mask**. Only works when sharpening is enabled and zoom >= 100%. |

### Editor: tools

| Where  | Shortcut                    | Action |
|--------|-----------------------------|--------|
| Editor | **h**, **Shift-h**          | Hand tool. |
| Editor | **Shift-c**                 | **Crop** selection. Move the crop using **Shift**+**mouse drag**; resize the crop using **Ctrl**+**mouse drag**. |
| Editor | **Shift-s**                 | **Straighten** / **fine rotation**. Indicate the vertical or horizontal by drawing a guide line over the image preview; the angle of rotation is shown next to the guide line; the center of rotation is the geometrical center of the image. |
| Editor | **Shift-p**                 | **Perspective** correction. |
| Editor | **Shift-w**                 | Spot white balance. |
| Editor | **F1**                      | Show the help for the keyboard shortcuts of the tools. |

### Editor: tabs of the tool panel

| Where  | Shortcut  | Action |
|--------|-----------|--------|
| Editor | **Alt-u** | Switch to the **Favorites** tab. |
| Editor | **Alt-e** | Switch to the **Exposure** tab. |
| Editor | **Alt-d** | Switch to the **Detail** tab. |
| Editor | **Alt-c** | Switch to the **Color** tab. |
| Editor | **Alt-t** | Switch to the **Transform** tab. |
| Editor | **Alt-r** | Switch to the **Raw** tab. |
| Editor | **Alt-f** | Switch to the **Effects** tab. |
| Editor | **Alt-x** | Switch to the **Local** tab. |
| Editor | **Alt-m** | Switch to the **Metadata** tab. |

### Editor: local editing masks

| Where  | Shortcut   | Action |
|--------|------------|--------|
| Editor | **Ctrl-m** | Show/hide the **mask** of the selected region. |
| Editor | **Ctrl-x** | Enable/disable the selected region. |
| Editor (drawn mask) | **Ctrl-z**, **Ctrl-Shift-z** | In a drawn mask: undo the last strokes group / remove all the strokes. |

The two mask shortcuts act on the region that you worked on last, in any of the
tools that have masks (the last region that you selected, or whose mask you
showed): you don't need to have the mask panel focused, you can use them while
the focus is on the preview or on another tool. They only work while the header
of that tool is visible (also if the tool is folded), for instance not while you
are looking at another tab of the tool panel; if it is not, the key does
whatever else it is assigned to. **Ctrl-x** is not taken over while you are
typing in a text field, where it keeps cutting text. Only one mask is shown at
a time: showing the mask of another tool hides the previous one.

### Editor: adjusting the sliders with the keyboard

Hold the key of a slider, and press **+** or **-** to increase or decrease its
value, **0** or **\*** to set it to zero, or **/** to bring it back to its initial
value. **F1** shows the same help in the program. Only the sliders listed below have a key by default, but
*every* slider of the tools of the Exposure, Detail, Color and Effects tabs
(Sharpening, Denoise, Dehaze, Black and White, ...) can be given one in the
Keyboard Shortcuts tab of the Preferences: look for it under **Tool** in the
tree.

| Where  | Key       | Slider |
|--------|-----------|--------|
| Editor | **e**     | Exposure: compensation |
| Editor | **q**     | Exposure: black |
| Editor | **c**     | Tone curve: contrast |
| Editor | **s**     | Saturation |
| Editor | **v**     | Vibrance |
| Editor | **i**     | Lab adjustments: brightness |
| Editor | **j**     | Lab adjustments: contrast |
| Editor | **n**     | Lab adjustments: chromaticity |
| Editor | **t**     | White balance: temperature |
| Editor | **g**     | Log encoding: gain |
| Editor | **b**     | Log encoding: target gray |
| Editor | **w**     | Log encoding: white EV |
| Editor | **d**     | Log encoding: black EV |
| Editor | **k**     | Log encoding: highlight compression |
| Editor | **1** to **5** | Tone equalizer: the five bands |
| Editor | **o**     | Soft light: strength |

### File Browser

| Where        | Shortcut                                | Action |
|--------------|-----------------------------------------|--------|
| File Browser | **F5**                                  | Refresh the list of thumbnails. |
| File Browser | **Ctrl-f**                              | Focus the Find box. Type filenames to search for; partial filenames are supported. Separate the search terms using commas, e.g. *1001,1004,1199*. Exclude search terms by prefixing them with *!=*, e.g. *!=1001,1004,1199*. |
| File Browser | **Enter**                               | In the Find box: search. In the path box: go to the folder that you typed. |
| File Browser | **Esc**                                 | Reset the path box to the current folder (and give the focus back to the thumbnails). |
| File Browser | **Ctrl-o**                              | Focus the path box. |
| File Browser | **l**, **Ctrl-l**, **Ctrl-Alt-l**       | Show/hide the left panel / the right panel / both. |
| File Browser | **m**                                   | Show/hide all side panels. |
| File Browser | **t**                                   | Show/hide the toolbar. |
| File Browser | **i**, **Alt-i**                        | Show Exif info. |
| File Browser | **+**, **Alt-+**                        | Increase the thumbnail size. |
| File Browser | **-**, **Alt--**                        | Decrease the thumbnail size. |
| File Browser | **Ctrl-i**                              | Activate the inspector. |
| File Browser | **Ctrl-t**                              | Show the contents of the trash. |
| File Browser | **Ctrl-Shift-Delete**                   | Empty the trash (when the trash is shown). |

Filters (hold **Ctrl** to add to the current filter):

| Where        | Shortcut                  | Action |
|--------------|---------------------------|--------|
| File Browser | **0**                     | Show unranked images. |
| File Browser | **1** to **5**            | Show images ranked as 1 to 5 stars. |
| File Browser | **6**                     | Show not edited images. |
| File Browser | **7**                     | Show edited images. |
| File Browser | **Alt-0**                 | Show images without a color label. |
| File Browser | **Alt-1** to **Alt-5**    | Show images labeled Red, Yellow, Green, Blue, Purple. |
| File Browser | **Alt-6**                 | Show unsaved images. |
| File Browser | **Alt-7**                 | Show saved images. |
| File Browser | **d**                     | Clear all filters. |

On the thumbnails:

| Where                  | Shortcut                                | Action |
|------------------------|-----------------------------------------|--------|
| File Browser           | **Left**, **Right**, **Up**, **Down**   | Move the selection (add **Shift** to extend it). **Backspace** and **space** also select the previous / next thumbnail. |
| File Browser           | **Home**, **End**, **Page Up**, **Page Down** | Select the first / last thumbnail, scroll by a page. |
| File Browser           | **Ctrl-a**                              | Select all. |
| File Browser           | **Enter**                               | Open the selected image in the editor. |
| File Browser           | **F3**, **F4**                          | Open the previous / next image. |
| File Browser           | **F2**                                  | Rename the selected files. |
| File Browser           | **Shift-0** to **Shift-5**              | Set the rank (**Shift-0** to unrank). |
| File Browser           | **Ctrl-Shift-0** to **Ctrl-Shift-5**   | Set the color label (**0** to remove it). |
| File Browser           | **Delete**, **Shift-Delete**            | Move to the trash / restore from the trash. |
| File Browser           | **Ctrl-Shift-Delete**                   | Delete the selected files from the disk. |
| File Browser           | **Ctrl-c**, **Ctrl-v**, **Ctrl-Shift-v** | Copy the processing profile / paste it / paste only some of its parameters (**Ctrl-Insert** and **Shift-Insert** work as well). |
| File Browser           | **Ctrl-Shift-c**, **Ctrl-Shift-m**     | Copy / move the selected files to another folder. |
| File Browser           | **Ctrl-b** (**Ctrl-Shift-b** for fast export) | Put the selected images in the processing queue. |
| File Browser           | **Ctrl-Shift-s**                        | Add the selected images to the session. |
| File Browser           | **Ctrl-space**                          | Show the inspector popup. |
| File Browser (session) | **Ctrl-o**, **Ctrl-+**, **Ctrl--**, **Ctrl-s** | The session buttons (when they are shown): load a session from a file, add files to the session, remove the selected files from the session, save the session to a file. |

### Inspector

| Where     | Shortcut     | Action |
|-----------|--------------|--------|
| Inspector | **Shift-i**  | Quick info. |
| Inspector | **h**        | Show/hide the histogram. |
| Inspector | **c**        | Toggle color management. |
| Inspector | **j**        | Embedded preview image. |
| Inspector | **r**        | Fast raw rendering with a linear tone curve. |
| Inspector | **f**        | Fast raw rendering with a film-like tone curve. |
| Inspector | **s**        | Fast raw rendering with a shadow boosting tone curve. |
| Inspector | **w**        | Raw clipped pixels. |
| Inspector | **y**        | Split view. |
| Inspector | **Tab**      | Switch pane in the split view. |
| Inspector | **x**        | Fit to window. |
| Inspector | **z**        | Zoom to 100%. |
| Inspector | **Shift-f**  | Toggle the focus mask. |
| File Browser (while the inspector is shown) | **0** to **5**, **Ctrl-0** to **Ctrl-5** | Set the rank / the color label of the image shown in the inspector. |
| Inspector popup | **j**, **r**, **f**, **s**, **w** | Choose the rendering mode (same as above). |

### Queue

| Where | Shortcut                                          | Action |
|-------|---------------------------------------------------|--------|
| Queue | **Ctrl-s**                                        | Start or stop processing the images in the queue. |
| Queue | **Ctrl-a**                                        | Select all. |
| Queue | **Ctrl-e**                                        | Open the selected image in the editor. |
| Queue | **Left**, **Right**, **Up**, **Down**, **Home**, **End** | Move the selection (add **Shift** to extend it). |
| Queue | **Ctrl-Home**, **Ctrl-End**                       | Move the selected images to the head / tail of the queue. |
| Queue | **Delete**                                        | Remove the selected images from the queue. |

### Save As dialog

| Where          | Shortcut         | Action |
|----------------|------------------|--------|
| Save As Dialog | **Ctrl-Enter**   | Save the file. |
