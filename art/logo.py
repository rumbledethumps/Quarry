#!/usr/bin/env python3
"""Turn a logo from Retro Diffusion into art/logo.png.

  logo.py in.png

in.png is the 192x64 logo on a plain white background, as
art/style/README.md asks for it. Every near-white pixel goes clear, inside
the letters too, the colors are cut to 15, and any moss or slime green
turns to rock of the same lightness. It writes art/logo.png and the logo row of
art/palettes.png. Only the Python standard library is used.
"""

import argparse
import colorsys
import os
from collections import Counter

from curtain import reduce
from rd2png import luma, rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_ROW = 7  # the logo row of art/palettes.png
MOSS = (55, 180)  # the hues of moss and slime
ROCK = (22, 0.2)  # the hue and saturation they turn to


def stone(color):
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in color))
    if MOSS[0] <= h * 360 <= MOSS[1]:
        h, s = ROCK[0] / 360, ROCK[1]
    return tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('input')
    args = parser.parse_args()
    width, height, pixels = rgba(args.input)
    if (width, height) != (192, 64):
        raise SystemExit(f'logo: {args.input} is {width}x{height}, not 192x64')
    for row in pixels:
        for x, p in enumerate(row):
            if p[0] > 235 and p[1] > 235 and p[2] > 235:
                row[x] = (0, 0, 0, 0)
    to = reduce(Counter(p[:3] for row in pixels for p in row if p[3]), 15)
    colors = sorted(set(to.values()), key=luma)
    index = {c: colors.index(to[c]) + 1 for c in to}
    rows = [[index[p[:3]] if p[3] else 0 for p in row] for row in pixels]
    palette = [(0, 0, 0, 0)] + [stone(c) + (255,) for c in colors]
    palette += [(0, 0, 0, 0)] * (16 - len(palette))
    write_png(os.path.join(HERE, 'logo.png'), width, height, 3, rows, palette)
    _, rows_count, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    palettes[LOGO_ROW] = palette
    write_png(os.path.join(HERE, 'palettes.png'), 16, rows_count, 6,
              [[v for c in row for v in c] for row in palettes])


if __name__ == '__main__':
    main()
