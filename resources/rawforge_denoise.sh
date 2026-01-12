#!/bin/bash

# Python interpreter to use
PYTHON=$HOME/src/rawforge-venv/bin/python

# ensure exiftool and zenity are in the PATH
export PATH=$HOME/.local/bin:/opt/local/bin:/usr/local/bin:$PATH

#############################################################################
# create a temporary dir for storing intermediate files

# create the python script
d=$(mktemp -d)
t=$d/rr.py
cat <<EOF > $t
import argparse
import os
import sys
import time
import subprocess
import numpy
import json
from RawForge.application.ModelHandler import ModelHandler
from RawForge.application.MODEL_REGISTRY import MODEL_REGISTRY
import RawForge.application.InferenceWorker as iw
from RawHandler.RawHandler import CoreRawMetadata


def getopts():
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('output')
    models = sorted(MODEL_REGISTRY.keys())
    p.add_argument('--model', choices=models, default='TreeNetDenoise')
    p.add_argument('--device')
    p.add_argument('--exiftool')
    def get_iso(s):
        s = s.lower()
        return int(s) if s != 'auto' else s
    p.add_argument('--iso', type=get_iso)
    def get_strength(s):
        v = int(s)
        if not (0 < v <= 50):
            raise ValueError("invalid strength value")
        return v / 10.0
    p.add_argument('--strength', type=get_strength, default="10")
    return p.parse_args()

def main():
    opts = getopts()
    handler = ModelHandler()
    if opts.device:
        handler.set_device(opts.device)
    handler.load_model(opts.model)
    print("1", flush=True)

    handler.colorspace = 'camera'

    iso = handler.load_rh(opts.input)
    print("2", flush=True)

    if opts.iso is not None:
        if opts.iso == 'auto':
            if opts.exiftool:
                res = subprocess.run([opts.exiftool, '-json', opts.input],
                                     stdout=subprocess.PIPE, check=True,
                                     text=True)
                data = json.loads(res.stdout)[0]
                try:
                    v = data['ISO']
                    if isinstance(v, str) and v.startswith('Hi '):
                        v = v[3:]
                    iso = int(v)
                except (KeyError, ValueError) as e:
                    pass
                iso = int(round(iso * float(data.get('ScaleFactor35efl', 1))))
            print(f'auto iso set to: {iso}')
        else:
            iso = opts.iso
    iso *= opts.strength

    handler.rh.colorspace = 'camera'
    md = handler.rh.core_metadata
    handler.rh.core_metadata = CoreRawMetadata(
        md.black_level_per_channel,
        md.white_level,
        numpy.eye(3),
        md.raw_pattern,
        md.camera_white_balance,
        md.iheight,
        md.iwidth)
    def rgb_colorspace_transform(*args, **kwds):
        return numpy.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
    handler.rh.rgb_colorspace_transform = rgb_colorspace_transform
    
    conditioning = [iso, 0]

    def tqdm(iterable, *args, **kwds):
        l = list(iterable)
        n = len(l)
        p = 2
        for i, r in enumerate(l):
            yield r
            c = 2 + int(98 * i/n)
            if c > p:
                print(str(c), flush=True)
                p = c
    iw.tqdm = tqdm

    w = iw.InferenceWorker(handler.model, 
                           handler.model_params,
                           handler.device, handler.rh, conditioning, None)
    try:
        img, denoised = w.run()
        handler.handle_full_image(denoised, opts.output, True)
    except Exception as e:
        for line in str(e).splitlines():
            sys.stderr.write(f'ERROR: {line}\n')
        sys.stderr.flush()
        sys.exit(0)
    
    if opts.exiftool and os.path.exists(opts.output):
        subprocess.run([opts.exiftool, '-TagsFromFile', opts.input, opts.output,
                        '-all', '-icc_profile', '-overwrite_original'])

if __name__ == '__main__':
    main()
EOF

$PYTHON "${d}/rr.py" \
        "$1" "${d}/out.dng" \
        --exiftool exiftool \
        --iso auto \
        --model TreeNetDenoiseLight \
    | zenity --progress --auto-kill --auto-close --text="Denoising..."

# check if there was an error
err=
if [ -f "$d/error" ]; then
    err=$(cat "$d/error" | awk '/ERROR:/ { $1=""; print $0 }' | sed 's/^ //g')
fi

if [ "$err" != "" ]; then
    # show the error message if something went wrong
    zenity --error --text="$err"
elif [ -f "${d}/out.dng" ]; then
    on="${1%.*}-denoised.dng"
    i=1
    while [ -f "${on}" ]; do
        on="${1%.*}-denoised-${i}.dng"
        i=$(expr $i + 1)
    done
    mv "${d}/out.dng" "${on}"
    # finally, use the same sidecar for the denoise image as for the
    # original image, except that we override WB and denoising settings
    if [ -f "$1.arp" ]; then
        cp "$1.arp" "${on}.arp"
        cat <<EOF >> "${on}.arp"

[Impulse Denoising]
Enabled=false

[Denoise]
Enabled=false
EOF
    fi
else
    zenity --error --text="Denoising error!"
fi

# remove the temporary dir
rm -rf $d
