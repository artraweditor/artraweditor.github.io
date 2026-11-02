---
title: GUI performance tuning
---

# Tuning the performance of the GUI

ART's default settings aim at a reasonable compromise between responsiveness,
accuracy of the preview and memory usage on an average machine. If you are
running on a very fast machine you can often get a snappier interface, while on
a slower machine, or one with little RAM, a few changes can make editing
considerably smoother.

Most of the options described here are in **Preferences → Performance**.

**Contents:**
- [Slider update delays](#delays)
- [Preview accuracy vs speed](#preview)
- [Memory usage](#memory)
- [Threads](#threads)
- [GPU acceleration](#gpu)
- [File browser and thumbnails](#thumbs)
- [Suggested starting points](#recipes)

Note that benchmarking by feel is unreliable: change one thing at a time, and
try it on the kind of image (and the tools) you actually use.


## Slider update delays {#delays}

When you drag a slider (or type into its spin button), ART does not re-process
the preview at every single value. Instead, it waits until the slider has
*stopped changing for a given amount of time*, and only then asks the
processing engine to update the preview. If the value changes again during the
wait, the timer restarts. The wait is configured in **Preferences →
Performance → Slider update delay**:

- **Delay for most tools (ms)** (default: `100`): used by the sliders of the
  majority of tools;
- **Delay for slow tools (ms)** (default: `200`): used by the sliders of tools
  that are expensive to compute, such as the white balance, raw black/white
  points, flat-field, dual demosaic contrast, and a few others.

Both values range from 0 to 2000 ms. The effect is:

- **Lower values** make the preview follow the slider more closely, at the
  cost of more frequent (and, on a slow machine, wasted) updates. With `0` the
  preview is updated on every single change, which only makes sense on a very
  fast machine and for light edits.
- **Higher values** reduce CPU load while dragging, because intermediate
  positions of the slider are skipped, but the preview will lag behind by
  (at least) the delay after you stop moving the slider.

Rules of thumb:

- On a slow machine, if the preview "stutters" while you drag a slider,
  *increase* the delays (e.g. 300/600 ms).
- On a fast machine, if the interface feels laggy because the preview
  only moves after you stop, *decrease* them (e.g. 30/100 ms, or even 0).
- Keep the "slow tools" delay greater than or equal to the "most tools" one:
  that is the intent of the two settings.

The changes apply to tools opened after the setting is changed, so restarting
ART after changing them is the safest option.

Related: the checkbox **Interrupt preview updates when a newer edit arrives**
(in the *Preview Accuracy* box) lets ART abandon a preview computation that has
become stale because you have moved the slider again, instead of always
completing it. This makes the detail preview (zoom ≥ 100%) much more
responsive while dragging sliders with a slow pipeline, but if processing is
slow the preview might not update at all until the slider stops moving. Turn it
off to restore the older behaviour, in which every update is always completed.
It is enabled by default.


## Preview accuracy vs speed {#preview}

The *Preview Accuracy* box controls how much work ART does for the preview at
zoom levels below 100%. Doing less work makes the preview faster, but it is
then less faithful to what the exported image will look like.

- **Resampling quality for the preview image at <100% zoom**
  (`Low`/`Medium`/`High`, default `Medium`): the quality of the algorithm used
  to scale the preview down. `Low` is the fastest.
- **Demosaicing method used for the preview at <100% zoom** (`Fast` or
  `As in ARP`, default `As in ARP`): with `Fast`, ART uses a quick demosaicing
  algorithm for the zoomed-out preview regardless of the one chosen in the
  profile. This speeds up the preview considerably for slow demosaicing
  methods, at the price of a less accurate rendering of fine detail.
- **White balance position in the preview pipeline**: applying the white
  balance *after* demosaicing is faster, applying it *before* is more accurate.
  The third choice (before demosaicing only at ≥100% zoom) is a compromise.
- **Show effects of noise reduction in the preview at <100% zoom**
  (default: on): noise reduction is expensive, so disabling this makes the
  zoomed-out preview faster, but you will not see the effects of denoising
  unless you zoom in to 100% (even when enabled, the zoomed-out rendering is
  not fully accurate).
- **Use faster but less accurate renderer for CTL scripts in the preview at
  <100% zoom** (only in builds with CTL support, default: off): speeds up the
  preview when you use [CTL scripts](Luts#ctl), at the cost of some accuracy.

If you only care about speed while editing, set resampling quality to `Low`,
demosaicing to `Fast`, white balance after demosaicing, and disable the
noise-reduction preview. The final output is *not* affected by any of these:
they apply only to the preview.


## Memory usage {#memory}

Some settings trade memory for responsiveness: bigger caches keep more data
around so that it does not have to be recomputed or reloaded.

- **CLUT Cache → Maximum number of cached CLUTs** (default: `5`, range 1–50):
  how many [LUTs](Luts) (Hald CLUTs, CLF, etc.) are kept in memory after being
  loaded. If you switch often between several LUTs, or use many in a profile,
  raise it to avoid reloading them; on a low-memory system you can lower it.
  Large 3D LUTs can take a significant amount of memory each.
- **Inspect → Maximum number of cached images** (default: `2`, range 1–12):
  how many images are kept in memory for the File Browser's inspector (the
  large preview shown when you hover over a thumbnail). More cached images make
  it faster to move back and forth between the same few pictures, at the cost
  of RAM. 
- **Inspect → Quick inspect popup size (as % of window size)** (30–100):
  a smaller popup is cheaper to render.
- **File Browser → Cache options** (in the *File Browser* tab of Preferences):
  *Maximum thumbnail height* and *Maximum number of cache entries* (default
  `20000`) control the size of the on-disk thumbnail cache. This trades disk
  space for faster directory browsing, not RAM.

Note that the biggest consumer of memory is the image being edited itself, and
the intermediate buffers of the processing pipeline, which depend on the size
of the image and on the tools that are enabled; there is no setting to
reduce this other than working with fewer expensive tools enabled at once.


## Threads {#threads}

- **Maximum number of threads for Noise Reduction and Wavelet Levels**
  (default: `0` = automatic, i.e. as many as there are CPU cores): the number of
  threads used by these memory-hungry tools. Their memory usage grows with the
  number of threads, so on a machine with many cores but little RAM, setting a
  limit (e.g. 4) can avoid swapping and actually make things faster.
- **Maximum number of threads for updating thumbnails** (default: `0` =
  automatic; applies at next start): limits the CPU used for generating
  thumbnails in the File Browser. Lowering it makes ART more pleasant to use
  while a big folder is being scanned, at the cost of slower thumbnail
  generation.


## GPU acceleration {#gpu}

In builds with Vulkan support, **Preferences → Performance → GPU acceleration**
lets ART offload some expensive operations to the GPU. Enabling it (and
choosing the device, if you have more than one, otherwise leave it on `Auto`)
takes effect at the next start of the application. If no suitable Vulkan
device is found, ART falls back automatically to the CPU, and the dialog tells
you if there is no device at all.

**Only a few tools currently have a GPU implementation.** Everything else
always runs on the CPU, so enabling the GPU does not speed up the rest of the
pipeline (demosaicing, tone and color tools, local adjustments, etc.). The
tools that can use the GPU are:

- **Noise Reduction**, including its *Final smoothing* step when the
  *Guided filter* method is selected;
- **Smoothing**, but only for the **Non-local means** and **Wavelets** modes.
  The other modes (Guided, Gaussian, Glow, Halation, Lens blur, Motion blur,
  Add noise) run on the CPU.

These are also the tools that are the slowest on the CPU, so if you use them
the gain can be large; if you don't, you will see no difference. The GPU is
used only for the preview and the export, not for generating thumbnails.
Images too large to fit in a single GPU buffer are processed in tiles
automatically.

If the GPU runs out of memory or fails while processing, ART falls back to the
CPU for the affected operation (or for the rest of the session, if the device
is lost), so the result is always produced.

Results from the GPU and CPU code paths are not required to be bit-identical:
tiny differences (well below visibility) are expected.


## File browser and thumbnails {#thumbs}

The *File Browser* box of the Performance tab has three options that affect
how the thumbnails are generated:

- **Cache processed thumbnail images** (default: on): stores the thumbnails
  *with* the editing profile applied in the cache, so they do not have to be
  re-rendered every time you open the folder. It costs some disk space, but
  makes returning to a folder you have already edited much faster.
- **Lazy caching of thumbnail images** (default: on): thumbnails are written to
  the cache only when they are actually needed (e.g. when they become visible),
  rather than for all the images in a directory as soon as it is opened. This
  speeds up opening large folders.
- **Delay update of thumbnail images while opening directories** (default:
  off): postpones the thumbnails' update, giving priority to showing the folder
  content quickly. It can help on slow disks or network drives.

There is also **Serialize reading of TIFF files** (default: on) in the *TIFF
Read Settings* box: when browsing folders with many uncompressed TIFF files,
reading them one at a time instead of in parallel increases the speed of
thumbnail generation, since the bottleneck is disk I/O rather than CPU.
Disable it if your TIFFs are compressed or on a very fast SSD.

Finally, the **Fast Export** *maximum width/height* (default 1920×1920) limits
the size of the images produced by the fast export function; smaller values
make it faster.


## Suggested starting points {#recipes}

**A slow machine, or one with little RAM (e.g. an old laptop with 4–8 GB):**

- slider delays: 300 ms / 600 ms;
- preview resampling quality `Low`, preview demosaicing `Fast`, white balance
  *after* demosaicing, noise-reduction preview off;
- *Maximum number of cached images* (Inspect): 1; *Maximum number of cached
  CLUTs*: 2–3;
- noise reduction/wavelet threads: 2–4; thumbnail threads: 1–2;
- keep *Lazy caching* on, and enable *Delay update of thumbnail images*.

**A fast machine with plenty of RAM (e.g. 12+ cores, 32 GB or more):**

- slider delays: 0–30 ms / 50–100 ms (or leave the defaults if they already
  feel fine);
- enable GPU acceleration if available (it only helps Noise Reduction and the
  Non-local means and Wavelets modes of Smoothing, see [above](#gpu));
- *Maximum number of cached images* (Inspect): 6–12; *Maximum number of cached
  CLUTs*: 10 or more;
- preview resampling quality `High`, demosaicing `As in ARP`, white balance
  before demosaicing, noise-reduction preview on;
- leave the thread limits at 0 (automatic).

If after tuning ART is still sluggish, check that you are not running out of
RAM (the system starting to swap is by far the most common cause of a very
slow GUI), and consider disabling or simplifying the most expensive tools
(e.g. high-quality denoising, many local-editing layers with complex masks)
while you are editing, enabling them back at the end.
