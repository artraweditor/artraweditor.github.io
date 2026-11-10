#!/usr/bin/env python3
"""ART user command: generate a CLF 3DLUT from the processing parameters.

The .arp sidecar of the selected file is turned into a CLF 3DLUT (ACES CLF,
optionally gzip-compressed as .clfz) that reproduces the colour/tone
processing of the sidecar and can be loaded in the Film Simulation tool.

How it works: an identity 3D grid is written as a floating point TIFF image,
(encoded with the PQ curve and tagged as linear Rec.2020 or Rec.709), then
processed with ART-cli using a copy of the sidecar in which all the "spatial"
tools (sharpening, denoise, crop, lens corrections...) and the white balance
are disabled; the processed grid is the content of the LUT, which is wrapped
in the CLF together with the needed shaper and colour space conversions.

Usage: make_3dlut.py [-o OUT] [-s SIZE] [-c COLORSPACE] [-z] [--no-gui] FILE

  FILE             the image whose sidecar (FILE.arp) is used, or the .arp
                   file itself. If there is no sidecar, the default
                   processing parameters are used.
  -o, --output     output file (.clf or .clfz). If not given, it is asked
                   with a file dialog.
  -s, --size       small (16), medium (36), large (64, default), huge (121)
  -c, --colorspace rec2020 (default) or rec709
  -z, --compressed gzip the output (implied by a .clfz extension)
  --no-gui         do not use dialogs: print messages to the terminal
                   (needs -o)

Needs numpy, tifffile and exiftool (but not a POSIX shell). ART-cli (and
ART-dialogs, for the GUI) are found in $PATH, where ART puts them. The code
shared by all the Python user commands is in art_usercommand.py, next to this
file."""

import argparse
import base64
import configparser
import gzip
import math
import os
import subprocess
import sys
import tempfile

import numpy
import tifffile

from art_usercommand import last_lines, run, run_with_progress, show_error

LINEAR_REC_2020 = b'AAAC2GxjbXMEMAAAbW50clJHQiBYWVogB+YACAAWABAACQAtYWNzcEFQUEwAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPbWAAEAAAAA0y1sY21zAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANZGVzYwAAASAAAABOY3BydAAAAXAAAAA2d3RwdAAAAagAAAAUY2hhZAAAAbwAAAAsclhZWgAAAegAAAAUYlhZWgAAAfwAAAAUZ1hZWgAAAhAAAAAUclRSQwAAAiQAAAAQZ1RSQwAAAiQAAAAQYlRSQwAAAiQAAAAQY2hybQAAAjQAAAAkZG1kZAAAAlgAAABaZG1uZAAAArQAAAAibWx1YwAAAAAAAAABAAAADGVuVVMAAAAyAAAAHABMAGkAbgBlAGEAcgAgAFIAZQBjAC4AIAAyADAAMgAwACAAKABJAEMAQwAgAFYANAApAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAABoAAAAcAFAAdQBiAGwAaQBjACAARABvAG0AYQBpAG4AAFhZWiAAAAAAAAD21gABAAAAANMtc2YzMgAAAAAAAQxCAAAF3v//8yUAAAeTAAD9kP//+6H///2iAAAD3AAAwG5YWVogAAAAAAAArGkAAEdv////gVhZWiAAAAAAAAAgAwAAC60AAMv+WFlaIAAAAAAAACppAACs4wAAB61wYXJhAAAAAAAAAAAAAQAAY2hybQAAAAAAAwAAAAC1PwAASsEAACuFAADMCAAAIYkAAAvHbWx1YwAAAAAAAAABAAAADGVuVVMAAAA+AAAAHAAjAHUAcwAvAHAAaQB4AGwAcwAvAEEAUgBUACMAMQAuADAAMAAwADAAMAAwADoAMAAuADAAMAAwADAAMAAhAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAYAAAAcAEEAUgBUAAA='

LINEAR_REC_709 = b'AAACwGxjbXMEQAAAbW50clJHQiBYWVogB+gABgAFAAwAAQAkYWNzcEFQUEwAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPbWAAEAAAAA0y1sY21zAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANZGVzYwAAASAAAAA2Y3BydAAAAVgAAAA2d3RwdAAAAZAAAAAUY2hhZAAAAaQAAAAsclhZWgAAAdAAAAAUYlhZWgAAAeQAAAAUZ1hZWgAAAfgAAAAUclRSQwAAAgwAAAAQZ1RSQwAAAgwAAAAQYlRSQwAAAgwAAAAQY2hybQAAAhwAAAAkZG1kZAAAAkAAAABaZG1uZAAAApwAAAAibWx1YwAAAAAAAAABAAAADGVuVVMAAAAaAAAAHABsAGkAbgBlAGEAcgAgAHIAZQBjADcAMAA5AABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAABoAAAAcAFAAdQBiAGwAaQBjACAARABvAG0AYQBpAG4AAFhZWiAAAAAAAAD21gABAAAAANMtc2YzMgAAAAAAAP/9/////v////7////9AAEAA///////////AAAAAQAA/+9YWVogAAAAAAAAfDIAAEAKAAAF0lhZWiAAAAAAAAAhVwAADVYAAK+XWFlaIAAAAAAAAFlNAACyoAAAHcRwYXJhAAAAAAAAAAAAAQAAY2hybQAAAAAAAwAAAACj1wAAVHsAAEzNAACZmgAAJmYAAA9cbWx1YwAAAAAAAAABAAAADGVuVVMAAAA+AAAAHAAjAHUAcwAvAHAAaQB4AGwAcwAvAEEAUgBUACMAMQAuADAAMAAwADAAMAAwADoAMAAuADAAMAAwADAAMAAhAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAYAAAAcAEEAUgBUAAA='

ICC_PROFILES = {'rec2020': LINEAR_REC_2020, 'rec709': LINEAR_REC_709}

lutsize = {
    'small': 16,
    'medium': 36,
    'large': 64,
    'huge': 121
}

PQSCALE = 100  # 1.0 is 100 nits


def getopts(argv):
    p = argparse.ArgumentParser(description='Generate a CLF 3DLUT from the '
                                'processing parameters of an image.')
    p.add_argument('infile')
    p.add_argument('-o', '--output')
    p.add_argument('-s', '--size', choices=list(lutsize), default='large')
    p.add_argument('-z', '--compressed', action='store_true')
    p.add_argument('-c', '--colorspace', choices=list(ICC_PROFILES),
                   default='rec2020')
    p.add_argument('--no-gui', action='store_true')
    # internal: run the conversion, reporting progress to the progress dialog
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    opts = p.parse_args(argv)
    if (opts.no_gui or opts.worker) and not opts.output:
        p.error('-o/--output is required with --no-gui')
    return opts


def info(msg, opts):
    if opts.worker:
        # "# text" sets the label of the progress dialog
        print('# ' + msg, flush=True)
    else:
        print('-' * 80)
        print(msg)
        print('-' * 80, flush=True)


def sidecar_of(infile):
    if infile.lower().endswith('.arp'):
        return infile
    return infile + '.arp'


def make_arp(opts):
    p = configparser.ConfigParser(default_section=None,
                                  delimiters=['='],
                                  comment_prefixes=['#'],
                                  interpolation=None)
    p.optionxform = str

    pparamsfile = sidecar_of(opts.infile)
    if os.path.exists(pparamsfile):
        info(f'importing procparams from {pparamsfile}...', opts)
        p.read(pparamsfile, encoding='utf-8')
    else:
        info('generating default procparams...', opts)

    def sec(name):
        if not p.has_section(name):
            p.add_section(name)
        return p[name]

    to_disable = [
        'CACorrection',
        'Coarse Transformation',
        'Crop',
        'Defringing',
        'Dehaze',
        'Denoise',
        'Distortion',
        'FattalToneMapping',
        'Film Negative',
        'Gradient',
        'Grain',
        'Impulse Denoising',
        'Local Contrast',
        'Luminance Curve',
        'OutputSharpening',
        'PCVignette',
        'Perspective',
        'Resize',
        'Rotation',
        'Sharpening',
        'Smoothing',
        'Spot Removal',
        'TextureBoost',
        'Vignetting Correction',
        'White Balance',
    ]
    for tool in to_disable:
        sec(tool)['Enabled'] = 'false'
    sec('LensProfile')['LcMode'] = 'none'

    to_override = [
        ('ToneCurve', 'HistogramMatching', 'false'),
        ('HSL Equalizer', 'Smoothing', '0'),
        ('LogEncoding', 'Auto', 'false'),
        ('LogEncoding', 'AutoGain', 'false'),
        ('LogEncoding', 'Regularization', '0'),
        ('ToneEqualizer', 'Regularization', '0'),
        ('Common Properties for Transformation', 'AutoFill', 'false'),
        ('Color Management', 'InputProfile', '(embedded)'),
        ('Color Management', 'OutputProfile', 'RTv4_Linear_Rec2020'),
        ('MetaData', 'Mode', '0')
    ]
    for (tool, key, val) in to_override:
        sec(tool)[key] = val

    cc = sec('ColorCorrection')
    cc['DisableSpatialGuides'] = 'true'
    for key in list(cc.keys()):
        if key.startswith('AreaMaskEnabled_'):
            cc[key] = 'false'
        elif key.startswith('ContrastThresholdMask_'):
            cc[key] = '0'
        elif key.startswith('DrawnMaskEnabled_'):
            cc[key] = 'false'
        elif key.startswith('LightnessMaskDetail_'):
            cc[key] = '0'
        elif key.startswith('MaskSmoothing_'):
            cc[key] = '0'
        elif key.startswith('ParametricMaskBlur_'):
            cc[key] = '-10'

    with open(os.path.join(opts.tempdir, 'base.tif.arp'), 'w',
              encoding='utf-8', newline='\n') as out:
        p.write(out, False)


def process(opts):
    info('processing base image...', opts)
    cmd = ['ART-cli', '-s',
           '-o', os.path.join(opts.tempdir, 'lut.tif'),
           '-b32', '-t', '-c', os.path.join(opts.tempdir, 'base.tif')]
    try:
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, errors='replace')
    except OSError as e:
        raise RuntimeError(f'cannot run ART-cli: {e}')
    if res.returncode != 0 or not os.path.exists(
            os.path.join(opts.tempdir, 'lut.tif')):
        lines = [l for l in res.stdout.splitlines() if l.strip()]
        tail = '\n'.join(lines[-5:])
        raise RuntimeError(f'ART-cli failed (exit status {res.returncode}):'
                           f'\n{tail}')


def pq(a, scale, inv):
    m1 = 2610.0 / 16384.0
    m2 = 2523.0 / 32.0
    c1 = 107.0 / 128.0
    c2 = 2413.0 / 128.0
    c3 = 2392.0 / 128.0
    with numpy.errstate(all='ignore'):
        if not inv:
            # assume 1.0 is 100 nits, normalise so that 1.0 is 10000 nits
            a = a / scale
            # apply the PQ curve
            aa = numpy.power(a, m1)
            res = numpy.power((c1 + c2 * aa) / (1.0 + c3 * aa), m2)
        else:
            p = numpy.power(a, 1.0 / m2)
            aa = numpy.fmax(p - c1, 0.0) / (c2 - c3 * p)
            res = numpy.power(aa, 1.0 / m1)
            res = res * scale
    return res


def make_base(opts):
    dim = lutsize[opts.size]
    info(f'generating base table of size {dim}...', opts)
    sz = complex(0, float(dim))
    table = numpy.mgrid[0.0:1.0:sz, 0.0:1.0:sz, 0.0:1.0:sz].reshape(3, -1).T
    n = int(round(math.sqrt(dim**3)))
    data = pq(table.reshape(-1), PQSCALE, True).astype(numpy.float32)
    data = data.reshape(n, n, -1)
    output = os.path.join(opts.tempdir, 'base.tif')
    profile = base64.b64decode(ICC_PROFILES[opts.colorspace])
    tifffile.imwrite(output, data, photometric='rgb')
    profname = os.path.join(opts.tempdir, 'profile.icc')
    with open(profname, 'wb') as f:
        f.write(profile)
    try:
        subprocess.run(['exiftool', '-icc_profile<=' + profname,
                        '-overwrite_original', output], check=True,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError('exiftool not found in $PATH (it is needed to '
                           'embed the ICC profile in the base image)')


def clf_matrix(comment, rows):
    arr = '\n'.join('        ' + ' '.join(f'{v:.8f}' for v in r) for r in rows)
    return (f'  <Matrix inBitDepth="32f" outBitDepth="32f" >\n'
            f'    <!-- {comment} -->\n'
            f'    <Array dim="3 3">\n{arr}\n    </Array>\n'
            f'  </Matrix>\n')


AP0_TO_REC2020 = clf_matrix('ACES AP0 to Rec2020', [
    (1.50910172, -0.2589874, -0.2501146),
    (-0.07757638, 1.17706684, -0.09949036),
    (0.0020526, -0.03114411, 1.02909153)])

REC2020_TO_AP0 = clf_matrix('Linear Rec.2020 to ACES AP0', [
    (0.67022657, 0.15216775, 0.17760585),
    (0.0441723, 0.86177705, 0.09405057),
    (0.0, 0.02577705, 0.97422293)])

AP0_TO_REC709 = clf_matrix('ACES AP0 to Linear Rec.709', [
    (2.55128702, -1.11947013, -0.4318176),
    (-0.27586285, 1.36601602, -0.09015301),
    (-0.01729251, -0.14852912, 1.16582168)])

REC709_TO_AP0 = clf_matrix('Linear Rec.709 to ACES AP0', [
    (0.43392843, 0.3762503, 0.18982151),
    (0.088802, 0.81526168, 0.09593625),
    (0.01775005, 0.10944762, 0.87280228)])

MATRICES = {
    'rec2020': (AP0_TO_REC2020, REC2020_TO_AP0),
    'rec709': (AP0_TO_REC709, REC709_TO_AP0),
}


def make_lut(opts):
    info('converting processed base image to clf 3dlut...', opts)
    data = tifffile.imread(os.path.join(opts.tempdir, 'lut.tif'))
    data = data.reshape(-1, 3)
    dim = int(round(math.pow(data.shape[0], 1.0 / 3.0)))
    to_out, from_out = MATRICES[opts.colorspace]

    # the 1D shaper, applied to every half float
    halfs = numpy.arange(65536, dtype=numpy.uint16).view(numpy.float16)
    with numpy.errstate(all='ignore'):
        shaped = pq(halfs.astype(numpy.float64), PQSCALE, False)
        shaped = shaped.astype(numpy.float16).view(numpy.uint16)

    fopen = gzip.open if opts.compressed else open
    with fopen(opts.output, 'wt', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<ProcessList compCLFversion="3" id="1">\n')
        f.write(to_out)
        f.write('<LUT1D inBitDepth="32f" outBitDepth="32f" '
                'halfDomain="true" rawHalfs="true">\n')
        f.write('  <Array dim="65536 1">\n')
        numpy.savetxt(f, shaped, fmt='    %d')
        f.write('  </Array>\n')
        f.write('</LUT1D>\n')
        f.write('<LUT3D inBitDepth="32f" outBitDepth="32f" '
                'interpolation="tetrahedral">\n')
        f.write(f'  <Array dim="{dim} {dim} {dim} 3">\n')
        numpy.savetxt(f, data, fmt='    %.8f  %.8f  %.8f')
        f.write('  </Array>\n')
        f.write('</LUT3D>\n')
        f.write(from_out)
        f.write('</ProcessList>\n')


def convert(opts):
    with tempfile.TemporaryDirectory() as d:
        opts.tempdir = d
        make_base(opts)
        make_arp(opts)
        process(opts)
        make_lut(opts)


def ask_output(infile):
    stem = os.path.splitext(infile)[0]
    cmd = ['ART-dialogs', '--title=Save LUT as...', '--file-selection',
           '--save', '--confirm-overwrite',
           '--filename=' + stem + '.clf',
           '--file-filter=CLF LUTs | *.clf',
           '--file-filter=Compressed CLF LUTs | *.clfz',
           '--file-filter=All files | *']
    res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    return res.stdout.strip() if res.returncode == 0 else ''


def main(argv):
    opts = getopts(argv)
    opts.infile = os.path.abspath(opts.infile)
    if opts.output:
        opts.output = os.path.abspath(opts.output)

    if opts.worker or opts.no_gui:
        if opts.output.lower().endswith('.clfz'):
            opts.compressed = True
        if opts.worker:
            try:
                convert(opts)
            except Exception as e:
                print(f'{e}', file=sys.stderr)
                sys.exit(1)
        else:
            convert(opts)
            print(f'Generated CLF 3DLUT in {opts.output}')
        return

    if not opts.output:
        opts.output = ask_output(opts.infile)
        if not opts.output:
            return
    cmd = [sys.executable, os.path.abspath(__file__), '--worker',
           '-o', opts.output, '-s', opts.size, '-c', opts.colorspace]
    if opts.compressed:
        cmd.append('-z')
    cmd.append(opts.infile)
    name = os.path.basename(opts.infile)
    with tempfile.TemporaryDirectory() as d:
        errfile = os.path.join(d, 'err.txt')
        status = run_with_progress(
            cmd, errfile,
            f'Generating CLF 3DLUT from the .arp sidecar of {name}...',
            width=500, pulsate=True)
        if status is None:
            # cancelled: do not leave a partial file
            if os.path.exists(opts.output):
                try:
                    os.remove(opts.output)
                except OSError:
                    pass
            return
        err = last_lines(errfile, 6)
    if status == 0 and os.path.isfile(opts.output):
        subprocess.run(['ART-dialogs', '--info', '--no-markup',
                        '--text=Generated CLF 3DLUT in ' + opts.output])
    else:
        show_error(f'Error generating CLF 3DLUT in {opts.output}: {err}')


if __name__ == '__main__':
    run(main)
