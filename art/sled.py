#!/usr/bin/env python3
"""Draw the sleds and their jets, as art/style/README.md describes them.

  sled.py out.bin
      The build runs this. It draws a sled for each width of TUNE_WIDTHS in
      src/tuning.h, with the number of jets in TUNE_JETS, into out.bin, each
      in a slot of SLED_SLOT bytes of src/xram.h. It also writes each sled
      as sleds/sled-<width>.png beside out.bin, to look at.

  sled.py --jet art/jet.png
      Draws the frames of a jet. A jet is a sprite of its own, so it can
      swivel: a frame is 8x12, with the nozzle on rows 0 to 2.

Each sled has small details of its own: scuffs, and a lamp between each two
jets. Its image is its width rounded up to 4, the size of its sprite. Its
first 8 rows are the sled, flat: the plate, rows 0 to 2, then the mount the
jets hang from, rows 3 and 4. Under that are the sled tilted 1 px in 8 to
the right as it falls, then 2 px in 8, 24 rows each.

The colors are indexes of the sled row of art/palettes.png.
"""

import argparse
import os
import random
import re

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
SLED_ROW = 4  # the sled row of art/palettes.png
TILTS = (1, 2)
TILT_ROWS = 24  # SLED_TILT_ROWS in src/xram.h
SLOT = 64 * (8 + 2 * TILT_ROWS) // 2  # SLED_SLOT in src/xram.h

# The colors, by their index in the sled row.
OUTLINE, G0, TAIL, G1, Y1, G2, RED, G3, ORANGE, Y2, Y3, Y4, Y5 = range(1, 14)

# The flames, under the nozzle, in the order of their frames: short, medium
# and long. b is the core, c and a its sides, d the red end, and e the
# smoky tip.
FLAMES = [
    ['..abba..', '..cbbc..', '...ad...'],
    ['..abba..', '..cbbc..', '..abba..', '...bc...', '...d....'],
    ['..abba..', '..cbbc..', '..cbbc..', '...bc...', '...cd...', '...e....'],
]
FLAME_COLORS = {'a': ORANGE, 'b': Y5, 'c': Y3, 'd': RED, 'e': TAIL}


def tuning(name):
    """A table of src/tuning.h, such as TUNE_WIDTHS."""
    with open(os.path.join(HERE, '..', 'src', 'tuning.h')) as f:
        text = f.read()
    match = re.search(rf'#define {name} \{{([^}}]*)\}}', text)
    return [int(n) for n in match.group(1).split(',')]


def jet_x(width, jets, i):
    """The center of jet i under a sled, as jet_x() in src/paddle.c."""
    return width // 2 if jets == 1 else 7 + i * (width - 14) // (jets - 1)


def image_width(width):
    """The width of a sled's image and sprite, a multiple of 4."""
    return (width + 3) // 4 * 4


def sled(width, jets):
    """The rows of the flat sled, 8 rows of color indexes, its image width
    wide."""
    rng = random.Random(width)
    pad = [0] * (image_width(width) - width)
    rows = [[0] * width for _ in range(8)]
    rows[0] = [Y5] * width  # the crisp top, the full width
    rows[1] = [Y3] * width
    rows[2] = [0] + [Y1] * (width - 2) + [0]  # the underside bevels in
    for x in range(8, width - 7, 8):
        rows[1][x] = Y1  # bolts
    for start in range(2, width - 4, 16):
        end = min(start + 12, width - 2)
        x = rng.randrange(start, end)
        if rows[1][x] == Y3:
            rows[1][x] = Y4  # a scuff, paint worn bright
        if rng.random() < 0.5:
            rows[2][rng.randrange(start, end)] = Y2
    if jets == 1:
        left, right = width // 2 - 6, width // 2 + 6
    else:
        left, right = 3, width - 3
    for x in range(left, right):
        rows[3][x] = G0
        rows[4][x] = OUTLINE if x in (left, right - 1) else G1
    for x in range(left + 1, right - 1, 4):
        rows[3][x] = G2  # rivets
    for i in range(jets - 1):
        x = (jet_x(width, jets, i) + jet_x(width, jets, i + 1)) // 2 + rng.choice((-1, 0, 1))
        rows[4][x] = ORANGE  # a lamp between each two jets
    return [row + pad for row in rows]


def tilted(rows, width, tilt):
    """The sled tilted tilt px in 8, the right end lower."""
    out = [[0] * width for _ in range(TILT_ROWS)]
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c:
                out[y + x * tilt // 8][x] = c
    return out


def jet(flame, swivel):
    """A jet frame: the nozzle, and the flame under it, or none. Swiveled, the
    mouth and the flame lean left, which pushes the sled right."""
    rows = [[0] * 8 for _ in range(12)]
    rows[0][2:6] = [G2, G1, G1, G1]  # the neck, under the mount
    rows[1][1:7] = [G3, G1, OUTLINE, OUTLINE, G1, G1]
    rows[2][1:7] = [G0, OUTLINE, OUTLINE, OUTLINE, OUTLINE, G0]  # the mouth
    if swivel:
        rows[2] = rows[2][1:] + [0]
    if flame is not None:
        for k, line in enumerate(FLAMES[flame]):
            shift = 1 + k // 3 if swivel else 0
            for x, ch in enumerate(line):
                if ch != '.':
                    rows[3 + k][x - shift] = FLAME_COLORS[ch]
    return rows


def pack(rows):
    """Rows of 4-bit colors, two pixels to a byte, the left in the high
    nibble, as png2bin.py packs them."""
    return bytes(row[x] << 4 | row[x + 1] for row in rows for x in range(0, len(row), 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('--jet', action='store_true', help='draw the jet frames instead')
    args = parser.parse_args()
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    colors = palettes[SLED_ROW]
    if args.jet:
        frames = [jet(None, False)] + [jet(f, False) for f in range(3)]
        frames += [jet(f, True) for f in range(3)]
        strip = [[c for frame in frames for c in frame[y]] for y in range(12)]
        write_png(args.output, 8 * len(frames), 12, 3, strip, colors)
        return
    folder = os.path.join(os.path.dirname(os.path.abspath(args.output)), 'sleds')
    os.makedirs(folder, exist_ok=True)
    data = bytearray()
    for width, n in zip(tuning('TUNE_WIDTHS'), tuning('TUNE_JETS')):
        flat = sled(width, n)
        rows = flat + [r for t in TILTS for r in tilted(flat[:5], image_width(width), t)]
        write_png(os.path.join(folder, f'sled-{width}.png'), image_width(width), len(rows), 3,
                  rows, colors)
        one = pack(rows)
        data += one + bytes(SLOT - len(one))
    with open(args.output, 'wb') as f:
        f.write(data)


if __name__ == '__main__':
    main()
