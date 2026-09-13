---
title: Building ART on Linux
---

# Building ART on Linux

These instructions reproduce, step by step, what the official [`linux.yml`](https://github.com/artraweditor/ART/blob/master/.github/workflows/linux.yml) GitHub Actions workflow does to produce the Linux release builds (tarball + AppImage) published on the [releases page](https://github.com/artraweditor/ART/releases). They are a faithful, from-source recipe: every dependency is built at the exact version the CI pins, so the result should match the official binaries closely.

## Supported variants

The workflow builds two variants in parallel, differing only in a handful of flags:

| Variant | Runner | Arch flag | Notes |
|---|---|---|---|
| x86_64 | `ubuntu-22.04` | `-DENABLE_SIMDE=0` | Standard build |
| arm64 | `ubuntu-22.04-arm` | `-DENABLE_SIMDE=1` | Requires the SIMDE library (SSE/NEON translation) |

A **Debug** build can also be produced (`-DCMAKE_BUILD_TYPE=Debug`), matching the workflow's `debug` input.

These instructions were validated against Ubuntu 22.04; they should also work unmodified on any recent Debian/Ubuntu derivative.

## 1. Base packages

```bash
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  git \
  build-essential \
  cmake \
  curl \
  pkg-config \
  libgtk-3-dev \
  libgtkmm-3.0-dev \
  librsvg2-dev \
  liblcms2-dev \
  libfftw3-dev \
  libtiff5-dev \
  libcanberra-gtk3-dev \
  libinih-dev \
  libbrotli-dev \
  libexpat1-dev \
  gvfs \
  wget
sudo python3 -m pip install meson
```

Install Ninja (the distro package is often too old):

```bash
# x86_64:
wget https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-linux.zip
# arm64, use instead:
# wget https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-linux-aarch64.zip
unzip ninja-linux*.zip
sudo mv ninja /usr/local/bin
```

## 2. Dependencies built from source

ART needs recent versions of several libraries that are usually not available (or too old) in distro repositories. Build and install each of these, in order, into `/usr/local`:

### LCMS2 2.16

```bash
wget https://downloads.sourceforge.net/project/lcms/lcms/2.16/lcms2-2.16.tar.gz
tar xzf lcms2-2.16.tar.gz
cd lcms2-2.16
autoreconf -i
./configure --with-fastfloat
make -j$(nproc)
sudo make install
cd ..
```

### Exiv2 0.28.8

```bash
mkdir exiv2 && cd exiv2
wget https://github.com/Exiv2/exiv2/archive/refs/tags/v0.28.8.tar.gz
tar xzf v0.28.8.tar.gz
mkdir build && cd build
cmake ../exiv2-0.28.8 -DCMAKE_BUILD_TYPE=Release -DEXIV2_ENABLE_BMFF=1
make -j$(nproc)
sudo make install
cd ../..
```

### Lensfun 0.3.4

```bash
git clone --depth 1 --branch v0.3.4 https://github.com/lensfun/lensfun.git
mkdir build_lensfun && cd build_lensfun
cmake -DCMAKE_BUILD_TYPE=Release ../lensfun
make -j$(nproc)
sudo make install
cd ..
```

### LibRaw (latest master)

```bash
git clone --depth 1 https://github.com/LibRaw/LibRaw.git
cd LibRaw
autoreconf -i
CPPFLAGS=-DUSE_X3FTOOLS ./configure
make -j$(nproc)
sudo make install
cd ..
```

### CTL (ACES CTL interpreter, latest master)

```bash
git clone --depth 1 https://github.com/ampas/CTL.git
mkdir build-CTL && cd build-CTL
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS=-fpermissive ../CTL
make -j$(nproc)
sudo make install
cd ..
```

### OpenColorIO 2.4.1

```bash
mkdir ocio && cd ocio
wget https://github.com/AcademySoftwareFoundation/OpenColorIO/archive/refs/tags/v2.4.1.tar.gz
tar xzf v2.4.1.tar.gz
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release \
  -DOCIO_BUILD_PYTHON=OFF -DOCIO_BUILD_APPS=0 \
  -DOCIO_BUILD_TESTS=0 -DOCIO_BUILD_GPU_TESTS=0 \
  ../OpenColorIO-2.4.1
make -j$(nproc)
sudo make install
cd ../..
```

### mimalloc 2.1.7

```bash
mkdir mimalloc && cd mimalloc
wget https://github.com/microsoft/mimalloc/archive/refs/tags/v2.1.7.tar.gz
tar xzf v2.1.7.tar.gz
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ../mimalloc-2.1.7
make -j$(nproc)
sudo make install
cd ../..
```

### SIMDE 0.8.2 — **arm64 only**

```bash
wget https://github.com/simd-everywhere/simde/archive/refs/tags/v0.8.2.tar.gz
tar xzf v0.8.2.tar.gz
cd simde-0.8.2
meson setup build -Dbuildtype=release -Dtests=false
sudo meson install -C build
cd ..
```

After installing native libraries, refresh the linker cache:

```bash
sudo ldconfig
```

## 3. Configure and build ART

Clone the ART repository, then configure with CMake:

```bash
git clone https://github.com/artraweditor/ART.git
mkdir build && cd build

# Set to 1 only for the arm64 build:
ART_SIMDE=0

cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_BUNDLE=1 \
  -DENABLE_CTL=1 \
  -DENABLE_LIBRAW=1 \
  -DCTL_INCLUDE_DIR=/usr/local/include/CTL \
  -DCMAKE_LIBRARY_PATH=/usr/local/lib \
  -DENABLE_SIMDE=${ART_SIMDE} \
  ../ART

make -j$(nproc)
make install
```

This installs a self-contained bundle under `build/Release` (or `build/Debug` for a debug build).

Update the Lensfun camera/lens database inside the bundle:

```bash
PYTHONPATH=/usr/local/lib/python3.8/site-packages lensfun-update-data
```

## 4. Packaging as an AppImage

The CI additionally builds a private, newer copy of glib (2.83.3) to work around bugs in the distro version, which is dropped into the bundle in place of the system libraries. This step is **optional** for a purely local build, but is what makes the official AppImage portable across older distros:

```bash
wget https://download.gnome.org/sources/glib/2.83/glib-2.83.3.tar.xz
tar xJf glib-2.83.3.tar.xz
cd glib-2.83.3
meson setup build -Dbuildtype=release -Dglib_debug=disabled -Dprefix=/opt/glib
meson compile -C build
sudo meson install -C build
cd ..
```

Bundle the release build into a redistributable folder using ART's own bundling script:

```bash
cd build/Release   # or build/Debug
python3 ../../ART/tools/linux/bundle_ART.py -o ../../ART-bundle -v -E -I
cd ../..
```

If you built the custom glib above, drop it into the bundle's `lib/` directory:

```bash
for l in libgmodule-2.0.so.0 libglib-2.0.so.0 libgio-2.0.so.0; do
  rm -f ART-bundle/lib/${l}
  cp /opt/glib/lib/$(uname -m)-linux-gnu/${l} ART-bundle/lib/
done
```

Finally, wrap the bundle into an AppImage:

```bash
# x86_64: appimagetool-x86_64.AppImage; arm64: appimagetool-aarch64.AppImage
wget https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage
chmod a+x appimagetool-x86_64.AppImage

cd ART-bundle
ln -s share/icons/hicolor/128x128/apps/ART.png
cat > AppRun <<'EOF'
#!/bin/sh
export ART_MKDESKTOP=no
d=$(dirname "$0")
if [ "$1" = "--cli" ]; then
  shift
  exec "${d}/ART-cli" "$@"
else
  exec "${d}/ART" "$@"
fi
EOF
chmod a+x AppRun
cat > ART.desktop <<'EOF'
[Desktop Entry]
Name=ART
Type=Application
Exec=ART
Comment=ART is a free RAW image processor
Icon=ART
Categories=Graphics;
EOF
cd ..

ARCH=x86_64 ./appimagetool-x86_64.AppImage -n ART-bundle
```

The resulting `.AppImage` file is a standalone executable that runs on most Linux distributions without installation.

## Reference

This document is derived from the CI definition in [`.github/workflows/linux.yml`](https://github.com/artraweditor/ART/blob/master/.github/workflows/linux.yml). Refer to that file for the exact, up-to-date, authoritative build recipe — these instructions may lag behind future CI changes.
