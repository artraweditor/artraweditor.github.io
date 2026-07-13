---
title: Home
layout: post
---

# About

Welcome to the home page of ART, a [free, open-source](https://www.gnu.org/philosophy/philosophy.html), cross-platform 
raw image processing program. 
ART is a derivative of the popular [RawTherapee](http://rawtherapee.com),
trading a bit of customization and control over various processing parameters for a simpler and (hopefully) easier to use interface,
while still maintaining the power and quality of RawTherapee.

## Features

At a first glance, ART appears very similar to RawTherapee. 
Compared to the latter, ART differs in the following main aspects:

- The user interface and the underlying processing pipeline have been significantly restructured, with many tools removed, some new tools added, and several tools rewritten and/or refactored. 

- Various new tools for performing local edits have been added, with support for various masking modes (both drawn and parametric).

- Better metadata handling (thanks to the [exiv2](http://exiv2.org) and [exiftool](http://exiftool.org) libraries), with (optional) support for reading and writing XMP sidecar files.

- Support for various [input and output custom image formats](Customformats) via a simple plugin system, including various [true HDR output formats](Hdroutput).

- Support for using [LibRaw](https://www.libraw.org) for decoding raw files.

- Support for [ACES CLF LUTs](https://docs.acescentral.com/clf/specification/) using [OpenColorIO](https://opencolorio.org/).

- Support for [CTL scripts](https://acescentral.com/knowledge-base-2/ctl/) using the [ACES CTL interpreter](https://github.com/ampas/CTL).

- Easy integration of [external tools](Usercommands), including [AI-based ones](AItools) for masking and denoising.

- A new automatic perspective correction tool (adapted from [darktable](http://darktable.org)) has been added.

- Star ratings and colour labels can be loaded and stored from/to XMP sidecar files.

- Snapshots are now permanent, saved in the processing profiles.

- Processing profiles have `.arp` extension instead of `.pp3`, to avoid conflicts with RawTherapee.

- The "inspector mode" tool of the file browser has been significantly enhanced.

## Status

The current version is 1.26.7. It was released on July 13th 2026.
[Change log](https://github.com/artraweditor/ART/compare/1.26.6...1.26.7).

## License 
ART is released under the [GNU General Public License version 3](https://www.gnu.org/licenses/gpl.html).
