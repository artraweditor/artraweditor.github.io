---
title: Building ART on Windows
---

# Building ART on Windows

These instructions reproduce, step by step, what the official [`windows.yml`](https://github.com/artraweditor/ART/blob/master/.github/workflows/windows.yml) GitHub Actions workflow does to produce the Windows installer (and portable `.7z`) releases published on the [releases page](https://github.com/artraweditor/ART/releases). The build uses [MSYS2](https://www.msys2.org/) and is meant to be run from an **MSYS2 shell**, not a plain Windows terminal.

## Supported variants

| Variant | Runner | MSYS2 subsystem | Compiler | Notes |
|---|---|---|---|---|
| x64 | `windows-latest` | `UCRT64` | gcc | |
| arm64 | `windows-11-arm` | `CLANGARM64` | clang | Requires SIMDE and extra warning-suppression flags |

## 1. Install MSYS2

Download and install MSYS2 from <https://www.msys2.org/> (the CI installs it to `C:\msys2`, so that path is assumed below — adjust it if you install elsewhere). Update it and open the shell that matches your target variant:

- x64 → the **UCRT64** shell (`C:\msys2\msys2_shell.cmd -ucrt64`)
- arm64 → the **CLANGARM64** shell (`C:\msys2\msys2_shell.cmd -clangarm64`)

All the commands below are run **inside that MSYS2 shell**.

Install the base tools:

```bash
pacman -Syu   # you may need to re-open the shell if pacman restarts itself
pacman -S git wget xz p7zip
```

## 2. Install prebuilt ART dependencies

ART publishes a prebuilt MSYS2 package repository (`artraweditor/msys2-repo`) containing pinned versions of several dependencies that are faster to grab than to build. Register it as a local pacman repository:

```bash
# UCRT64 (x64):
export ART_MSYS2_REPO=ucrt64
export ART_PKG_PREFIX=mingw-w64-ucrt-x86_64
export ART_MSYS2_REPO_VER=1.0.1
export ART_COMPILER=gcc
# CLANGARM64 (arm64), use instead:
# export ART_MSYS2_REPO=clangarm64
# export ART_PKG_PREFIX=mingw-w64-clang-aarch64
# export ART_MSYS2_REPO_VER=1.0
# export ART_COMPILER=clang

wget https://github.com/artraweditor/msys2-repo/releases/download/${ART_MSYS2_REPO_VER}/repo-${ART_MSYS2_REPO}.tar
tar xf repo-${ART_MSYS2_REPO}.tar

cat >> /etc/pacman.conf <<EOF
[custom-${ART_MSYS2_REPO}]
SigLevel = Optional TrustAll
Server = file://$(pwd)/repo-${ART_MSYS2_REPO}
EOF

pacman -Sy
for p in ${ART_COMPILER} cmake autotools ninja gtkmm3 lcms2 fftw lensfun mimalloc opencolorio; do
    pacman --noconfirm -S custom-${ART_MSYS2_REPO}/${ART_PKG_PREFIX}-${p}
done
```

This installs the compiler toolchain, CMake, Ninja, GTKmm3, LCMS2, FFTW, Lensfun, mimalloc and OpenColorIO in one step.

## 3. Remaining dependencies, built from source

### Exiv2 0.27.7

```bash
wget https://github.com/Exiv2/exiv2/releases/download/v0.27.7/exiv2-0.27.7-Source.tar.gz
tar xzf exiv2-0.27.7-Source.tar.gz
mkdir build-exiv2 && cd build-exiv2
cmake \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=c:/msys2/usr/local \
  -DEXIV2_ENABLE_WIN_UNICODE=1 \
  -DEXIV2_ENABLE_BMFF=1 \
  ../exiv2-0.27.7-Source
ninja install
cd ..
```

### LibRaw (latest master)

```bash
git clone --depth 1 https://github.com/LibRaw/LibRaw.git
cd LibRaw
autoreconf -i
# gcc for UCRT64, clang for CLANGARM64:
export CC=gcc CXX=g++
# export CC=clang CXX=clang++

CPPFLAGS=-DUSE_X3FTOOLS ./configure --prefix=c:/msys2/usr/local
make -j
make install
cd ..
```

### CTL (ACES CTL interpreter, latest master)

```bash
git clone --depth 1 https://github.com/ampas/CTL.git
mkdir build-CTL && cd build-CTL
cmake \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=c:/msys2/usr/local \
  -DCMAKE_CXX_FLAGS="-fpermissive -fms-extensions" \
  -DCTL_BUILD_TESTS=0 -DCTL_BUILD_TOOLS=0 \
  ../CTL
ninja install
cd ..
```

### SIMDE 0.8.2 — **arm64 (CLANGARM64) only**

```bash
wget https://github.com/mesonbuild/meson/releases/download/1.10.0/meson-1.10.0.tar.gz
tar xzf meson-1.10.0.tar.gz
wget https://github.com/simd-everywhere/simde/archive/refs/tags/v0.8.2.tar.gz
tar xzf v0.8.2.tar.gz
cd simde-0.8.2
python ../meson-1.10.0/meson.py setup build -Dbuildtype=release -Dtests=false -Dprefix=c:/msys2/usr/local
python ../meson-1.10.0/meson.py install -C build
cd ..
```

## 4. Configure and build ART

```bash
git clone https://github.com/artraweditor/ART.git
mkdir build && cd build
export PKG_CONFIG_PATH=c:/msys2/usr/local/lib/pkgconfig

# UCRT64 (x64):
ART_CXX_FLAGS=
ART_SIMDE=0
# CLANGARM64 (arm64), use instead:
# ART_CXX_FLAGS="-Wno-ignored-attributes -Wno-unused-command-line-argument"
# ART_SIMDE=1

cmake \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_LIBRAW=1 \
  -DENABLE_OCIO=1 \
  -DENABLE_CTL=1 \
  -DCTL_INCLUDE_DIR=/usr/local/include/CTL \
  -DCMAKE_LIBRARY_PATH=/usr/local/lib \
  -DBUILD_BUNDLE=1 \
  -DENABLE_SIMDE=${ART_SIMDE} \
  -DCMAKE_CXX_FLAGS="${ART_CXX_FLAGS}" \
  ../ART

ninja install
```

This installs a self-contained bundle under `build/Release`.

Update the Lensfun camera/lens database:

```bash
lensfun-update-data
```

## 5. Packaging: portable bundle, installer

Collect the DLLs and produce a portable, self-contained folder using ART's own bundling script:

```bash
cd build/Release
python ../../ART/tools/win/bundle_ART.py -o ../../bundle -v -E -I -m c:/msys2
cd ../..
```

To build the Windows installer, [Inno Setup](https://jrsoftware.org/isinfo.php) is required. From a regular Windows shell (PowerShell), with [Chocolatey](https://chocolatey.org/) available:

```powershell
choco install innosetup
cd bundle
iscc /F"installer" "WindowsInnoSetup.iss"
```

This produces `installer.exe`; rename it, e.g. `ART_<version>_Win64.exe` (or `..._Windows_arm64.exe` for the arm64 build).

Optionally, also archive the `bundle` folder itself as a portable, no-install-required `.7z` package:

```bash
mv bundle ART_portable
7z a ART_portable.7z ART_portable
```

## Reference

This document is derived from the CI definition in [`.github/workflows/windows.yml`](https://github.com/artraweditor/ART/blob/master/.github/workflows/windows.yml). Refer to that file for the exact, up-to-date, authoritative build recipe — these instructions may lag behind future CI changes.
