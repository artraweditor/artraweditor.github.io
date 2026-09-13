---
title: Building ART on macOS
---

# Building ART on macOS

These instructions reproduce, step by step, what the official [`macos.yml`](https://github.com/artraweditor/ART/blob/master/.github/workflows/macos.yml) GitHub Actions workflow does to produce the macOS `.dmg` releases published on the [releases page](https://github.com/artraweditor/ART/releases).

## Supported variants

| Variant | Runner | Homebrew prefix | Extra library | Notes |
|---|---|---|---|---|
| Intel (x64) | `macos-15-intel` | `/usr/local` | — | Set `HOMEBREW_PREFIX` manually |
| Apple Silicon (arm64) | `macos-14` | `/opt/homebrew` (default) | SIMDE | `HOMEBREW_PREFIX` is already set by the runner environment |

A **Debug** build with AddressSanitizer enabled can also be produced (`-DCMAKE_BUILD_TYPE=Debug -DWITH_SAN="address -fsanitize-recover=address"`), matching the workflow's `debug` input.

## 1. Base packages via Homebrew

```bash
brew install \
  gtkmm3 \
  gtk-mac-integration \
  little-cms2 \
  meson \
  cmake \
  fftw \
  exiv2 \
  lensfun \
  pkgconfig \
  automake \
  libtool \
  opencolorio \
  librsvg \
  adwaita-icon-theme \
  libomp \
  ctl \
  expat
```

On **Apple Silicon** only, also install SIMDE:

```bash
brew install simde
```

On **Intel** Macs, Homebrew's prefix is not automatically exported in the shell environment the way it is on Apple Silicon runners, so set it explicitly:

```bash
export HOMEBREW_PREFIX=/usr/local
```

(On Apple Silicon, `HOMEBREW_PREFIX` is normally already `/opt/homebrew` — check with `brew --prefix` and export it if it isn't set.)

## 2. Dependencies built from source

Homebrew's `little-cms2`, `librsvg`, and system GTK+ are not quite what ART needs, so the CI rebuilds a few pieces itself.

### LCMS2 2.17

```bash
curl -O -L https://downloads.sourceforge.net/project/lcms/lcms/2.17/lcms2-2.17.tar.gz
tar xzf lcms2-2.17.tar.gz
cd lcms2-2.17
./configure --prefix=/opt/local
make -j$(sysctl -n hw.ncpu)
sudo make install
cd ..
```

### LibRaw (latest master, with OpenMP support)

```bash
export C_FLAGS="-Xpreprocessor -fopenmp ${HOMEBREW_PREFIX}/opt/libomp/lib/libomp.dylib -I${HOMEBREW_PREFIX}/opt/libomp/include"

git clone --depth 1 https://github.com/LibRaw/LibRaw.git
git clone --depth 1 https://github.com/LibRaw/LibRaw-cmake.git
cd LibRaw
ln -s ../LibRaw-cmake/CMakeLists.txt
ln -s ../LibRaw-cmake/cmake
export PKG_CONFIG_PATH=/opt/local/lib/pkgconfig
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_X3FTOOLS=1 \
  -DCMAKE_INSTALL_PREFIX=/opt/local \
  -DOpenMP_C_FLAGS="$C_FLAGS" \
  -DOpenMP_CXX_FLAGS="$C_FLAGS" \
  -DOpenMP_C_LIB_NAMES=libomp \
  -DOpenMP_CXX_LIB_NAMES=libomp \
  -DOpenMP_libomp_LIBRARY="${HOMEBREW_PREFIX}/opt/libomp/lib/libomp.dylib" \
  -DCMAKE_CXX_FLAGS="-Wno-unused-command-line-argument -Wno-deprecated-register -Wno-unknown-warning-option"
make -j$(sysctl -n hw.ncpu)
sudo make install
cd ../..
```

### Patched GTK+ 3.24.43 (Quartz colorspace fix)

ART's macOS build patches GTK+ to fix colour handling on the native Quartz backend, then installs it into `/opt/local` alongside the other custom libraries:

```bash
curl -O https://download.gnome.org/sources/gtk+/3.24/gtk%2B-3.24.43.tar.xz
tar xJf gtk%2B-3.24.43.tar.xz
cd gtk+-3.24.43
# Patch is shipped inside the ART repository:
patch -p1 < ../ART/tools/osx/gdk-window-quartz-colorspace.patch
export PKG_CONFIG_PATH="${HOMEBREW_PREFIX}/opt/expat/lib/pkgconfig"
meson setup build \
  -Dbuildtype=release \
  -Dprefix=/opt/local \
  -Ddemos=false -Dexamples=false -Dtests=false \
  -Dx11_backend=false -Dintrospection=false \
  -Dc_args=-I${HOMEBREW_PREFIX}/include \
  -Dc_link_args=-I${HOMEBREW_PREFIX}/lib
cd build
meson compile
sudo meson install
cd ../..
```

## 3. Configure and build ART

```bash
git clone https://github.com/artraweditor/ART.git
mkdir build && cd build

# Set to 1 only for the Apple Silicon (arm64) build:
ART_SIMDE=0

export PKG_CONFIG_PATH="/opt/local/lib/pkgconfig:${HOMEBREW_PREFIX}/opt/expat/lib/pkgconfig"
export C_FLAGS="-Xpreprocessor -fopenmp ${HOMEBREW_PREFIX}/opt/libomp/lib/libomp.dylib -I${HOMEBREW_PREFIX}/opt/libomp/include"

cmake ../ART \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_CTL=1 \
  -DENABLE_LIBRAW=1 \
  -DENABLE_SIMDE=${ART_SIMDE} \
  -DOpenMP_C_FLAGS="$C_FLAGS" \
  -DOpenMP_CXX_FLAGS="$C_FLAGS" \
  -DOpenMP_C_LIB_NAMES=libomp \
  -DOpenMP_CXX_LIB_NAMES=libomp \
  -DOpenMP_libomp_LIBRARY="${HOMEBREW_PREFIX}/opt/libomp/lib/libomp.dylib" \
  -DCTL_INCLUDE_DIR="${HOMEBREW_PREFIX}/include/CTL" \
  -DCMAKE_CXX_FLAGS="-I${HOMEBREW_PREFIX}/include -Wno-unused-command-line-argument -Wno-deprecated-register -Wno-unknown-warning-option"

make -j$(sysctl -n hw.ncpu)
make install
```

This produces `build/Release/ART.app` (or `build/Debug/ART.app` for a debug build).

Update the Lensfun camera/lens database:

```bash
lensfun-update-data
```

(Optional, matches CI) Install `exiftool`, used as a fallback for metadata handling on some raw formats:

```bash
wget https://exiftool.org/ver.txt
pkgname="ExifTool-$(cat ver.txt).pkg"
wget "https://sourceforge.net/projects/exiftool/files/${pkgname}/download" -O "${pkgname}"
sudo installer -pkg "${pkgname}" -target /
```

## 4. Packaging as a `.dmg`

ART ships its own macOS bundling script, which collects all the required dynamic libraries into a self-contained `.app` and wraps it in a disk image:

```bash
OUTDIR=$(pwd)
cd build/Release/ART.app   # or build/Debug/ART.app
python3 "${OUTDIR}/ART/tools/osx/bundle_ART.py" \
  -o "${OUTDIR}" -v \
  -r /opt/local/lib \
  -r "${HOMEBREW_PREFIX}/lib" \
  -p "${HOMEBREW_PREFIX}" \
  -e -I \
  -d "ART-macOS-$(uname -m)"
cd "${OUTDIR}"
```

For a debug build, add `--debug` to the `bundle_ART.py` invocation.

The `-d` argument produces a `.dmg` disk image named after the string you pass; open it to verify the bundled `ART.app` launches with no missing-library errors before distributing it.

## Reference

This document is derived from the CI definition in [`.github/workflows/macos.yml`](https://github.com/artraweditor/ART/blob/master/.github/workflows/macos.yml). Refer to that file for the exact, up-to-date, authoritative build recipe — these instructions may lag behind future CI changes.
