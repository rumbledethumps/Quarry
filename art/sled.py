#!/usr/bin/env python3
"""Draw the sleds and their jets, as art/style/README.md describes them.

  sled.py

Writes art/sleds/sled-<width>.png for each width of TUNE_WIDTHS in
src/tuning.h, for the number of jets in TUNE_JETS, and art/jet.png. Run it
after a change to either. Each sled is an image of its own, so any one of
them can be touched up by hand after, and each has small details of its
own: scuffs, and a lamp between each two jets.

A sled image is its width wide. Its first 8 rows are the sled, level: the
plate, rows 0 to 2, then the mount the jets hang from, rows 3 and 4. Under
that are the sled tilted 1 px in 8 to the right as it falls, then 2 px in
8, 24 rows each. The jets are sprites of their own, so they can swivel:
art/jet.png has a frame for each, 8x12, with the nozzle on rows 0 to 2.

The colors are indexes of the sled row of art/palettes.png.
"""

import os
import random
import re

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
SLED_ROW = 4  # the sled row of art/palettes.png
TILTS = (1, 2)
TILT_ROWS = 24  # SLED_TILT_ROWS in src/xram.h

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


def sled(width, jets):
    """The rows of the level sled, 8 rows of color indexes."""
    rng = random.Random(width)
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
    return rows


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


def main():
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    colors = palettes[SLED_ROW]
    widths, jets = tuning('TUNE_WIDTHS'), tuning('TUNE_JETS')
    folder = os.path.join(HERE, 'sleds')
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.startswith('sled-') and old.endswith('.png'):
            os.remove(os.path.join(folder, old))
    for width, n in zip(widths, jets):
        level = sled(width, n)
        rows = level + [r for t in TILTS for r in tilted(level[:5], width, t)]
        write_png(os.path.join(folder, f'sled-{width}.png'), width, len(rows), 3, rows, colors)
    frames = [jet(None, False)] + [jet(f, False) for f in range(3)] + [jet(f, True) for f in range(3)]
    strip = [[c for frame in frames for c in frame[y]] for y in range(12)]
    write_png(os.path.join(HERE, 'jet.png'), 8 * len(frames), 12, 3, strip, colors)


if __name__ == '__main__':
    main()
