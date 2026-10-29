#!/usr/bin/env python3
"""Draw the energy gauge's fittings, fuel and bubble, as art/style/README.md
describes them.

  gauge.py out.bin [--preview out.png]

The build runs this. out.bin is gauge_art_t of src/xram.h as far as its
glass, which the game makes for each level from the rock behind it: the
top fitting, the bottom fitting, a run of the fuel, its surface, and a
bubble.

The fittings are GAUGE_W wide and FITTING_H tall: a brass pipe from off
the edge of the screen into a hex nut that grips the end of the glass,
its faces lit from the left, the light on its top chamfer. The fuel is
GLASS_W wide, as the glass is, inside its outline: a column of liquid lit
from the upper left, brightest a little in from its left and darkest at
its right wall, the glint of the glass down it GLINT_COL in. Its surface
is a bright line, and a pixel higher at each wall, where the liquid
climbs the glass. Every row of the run is the same, so the game can stack
it to any height. The bubble is a ring 3 across, paler than the fuel, the
palest on its upper left, the fuel showing through its middle, in a sprite
BUBBLE_SIZE square.

The fittings are in the brass row of art/palettes.png, and the fuel in
the liquid row, so its colors can change without touching the brass.
--preview writes the pieces side by side, to look at.
"""

import argparse
import os

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
LIQUID_ROW, BRASS_ROW = 13, 14  # of art/palettes.png
GAUGE_W, FITTING_H, PIPE_W, NUT_H = 16, 20, 8, 8
GLASS_W, LIQUID_H, GLINT_COL, BUBBLE_SIZE = 12, 16, 2, 4  # as src/xram.h

# The brass row, by index, darkest first.
OUTLINE, B0, B1, B2, B3, B4 = range(1, 7)
# The liquid row: its body darkest to lightest, the glint over it and its
# surface.
L1, L2, L3, L4, L5, L6, L7, GLINT, SURFACE = range(1, 10)

# Across the fuel inside the glass's outline, left to right: a rim a little
# darker than its lit side, the glint, the brightest, then down to its
# shadowed wall.
BODY = [L5, GLINT, L7, L6, L6, L5, L4, L3, L2, L1]
LINE = [SURFACE] * 6 + [L7, L7, L6, L5]
BUBBLE = [[0, SURFACE, 0, 0], [SURFACE, 0, GLINT, 0], [0, GLINT, 0, 0], [0, 0, 0, 0]]


def pipe(rows, top, bottom):
    """The pipe, PIPE_W wide down the middle, from row top to bottom: a
    cylinder lit from the left, outlined each side."""
    x0 = (GAUGE_W - PIPE_W) // 2
    shades = [OUTLINE, B3, B3, B2, B2, B1, B0, OUTLINE]
    for y in range(top, bottom):
        rows[y][x0:x0 + PIPE_W] = shades


def nut(rows, top):
    """A hex nut NUT_H tall across the fitting, seen from the side: three
    faces, the left one lit, the middle and the right one in shadow, a
    light chamfer along its top and a dark one along its foot."""
    for x in range(1, GAUGE_W - 1):
        q = x / (GAUGE_W - 1)
        face = B4 if q < 0.25 else B2 if q < 0.75 else B1
        rows[top + 1][x] = min(B4, face + 1)
        for y in range(top + 2, top + NUT_H - 2):
            rows[y][x] = face
        rows[top + NUT_H - 2][x] = max(B0, face - 1)
    for y in range(top, top + NUT_H):
        rows[y][0] = rows[y][GAUGE_W - 1] = OUTLINE
    rows[top][:] = rows[top + NUT_H - 1][:] = [OUTLINE] * GAUGE_W


def fittings():
    """The top fitting, its pipe off the top of the screen, and the bottom
    one, its pipe off the foot."""
    top = [[0] * GAUGE_W for _ in range(FITTING_H)]
    pipe(top, 0, FITTING_H - NUT_H)
    nut(top, FITTING_H - NUT_H)
    bottom = [[0] * GAUGE_W for _ in range(FITTING_H)]
    nut(bottom, 0)
    pipe(bottom, NUT_H, FITTING_H)
    return top, bottom


def fuel():
    """A run of the fuel, and its surface: the line on its second row, the
    liquid up the walls on its first, the run under them."""
    inside = lambda colors: [0] + colors + [0]
    run = [inside(BODY) for _ in range(LIQUID_H)]
    climb = [0] * GLASS_W
    climb[1], climb[GLASS_W - 2] = SURFACE, L6
    surface = [climb, inside(LINE)] + run[2:]
    return run, surface


def pack(rows):
    """Rows of 4-bit colors, two pixels to a byte, the left in the high
    nibble, as png2bin.py packs them."""
    return bytes(row[x] << 4 | row[x + 1] for row in rows for x in range(0, len(row), 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('--preview', help='also write the pieces side by side as a PNG')
    args = parser.parse_args()
    assert len(BODY) == GLASS_W - 2 and BODY[GLINT_COL - 1] == GLINT
    top, bottom = fittings()
    run, surface = fuel()
    with open(args.output, 'wb') as f:
        f.write(pack(top) + pack(bottom) + pack(run) + pack(surface) + pack(BUBBLE))
    if args.preview:
        _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
        # The brass row's colors, then the liquid row's after them.
        colors = palettes[BRASS_ROW][:7] + palettes[LIQUID_ROW][1:10]
        shift = lambda rows: [[c and c + 6 for c in row] for row in rows]
        pieces = [top, bottom, shift(run), shift(surface), shift(BUBBLE)]
        gap = [0] * 4
        rows = [sum(([p[y][x] if y < len(p) else 0 for x in range(len(p[0]))] + gap for p in pieces), [])
                for y in range(FITTING_H)]
        write_png(args.preview, len(rows[0]), FITTING_H, 3, rows, colors)


if __name__ == '__main__':
    main()
