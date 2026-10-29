#!/usr/bin/env python3
"""Draw the energy gauge's fitting, fuel and bubble, and the meter in the
machine, as art/style/README.md describes them.

  gauge.py out.bin [--preview out.png]

The build runs this. out.bin is gauge_art_t of src/xram.h as far as its
glass, which the game makes for each level from the rock behind it: the
fitting, a run of the fuel, its surface, a bubble, the drop it throws up
as it pops, and the meter's frames.

The fitting is GAUGE_W wide and FITTING_H tall, the pipe of the upgrade
screen's backdrop: a length of the U-shaped pipe behind the crusher in
art/backdrop.png, and the ring where it joins, each widened by repeating a
plain column, as the posts of the frames are, and outlined in the navy of
the sprites. The pipe runs off the edge of the screen, and the ring grips
the end of the glass. This is the top one, and the bottom one is it
turned over, since the ring is the same both ways.

The fuel is GLASS_W wide, as the glass is, inside its outline: a column of
liquid lit from the upper left, brightest a little in from its left and
darkest at its right wall, the glint of the glass down it GLINT_COL in. Its
surface is a bright line, and a pixel higher at each wall, where the
liquid climbs the glass. Every row of the run is the same, so the game can
stack it to any height. The bubble is a ring 3 across, paler than the
fuel, the palest on its upper left, the fuel showing through its middle,
in a sprite BUBBLE_SIZE square. The drop is a single pixel of the fuel at
that sprite's top left.

The meter is the paddle that shows through the window of the machine on
the right wall, as an old parking meter's does, METER_W by METER_H, drawn
here by hand: a tab with a rounded top, nearly as wide as the window,
which the game slides up behind the machine from under the foot of the
window. Its colors are METER_PADDLE and METER_SHADE, which the game sets
to green, yellow or red.

The fitting is in the fitting row of art/palettes.png, the backdrop's own
colors of it, with the paddle's after them, and the fuel in the liquid row,
so its colors can change without touching the fitting. --preview writes the pieces side by side, to
look at.
"""

import argparse
import os

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
LIQUID_ROW, FITTING_ROW = 13, 14  # of art/palettes.png
GAUGE_W, FITTING_H = 16, 20
GLASS_W, LIQUID_H, GLINT_COL, BUBBLE_SIZE = 12, 16, 2, 4  # as src/xram.h
METER_W, METER_H, METER_PADDLE, METER_SHADE = 12, 8, 10, 11  # as src/xram.h

OUTLINE = (16, 19, 28)  # the navy of the sprites
# In art/backdrop.png, a row of the U-shaped pipe's left leg, between its
# outlines, and of the ring where it joins: the first pixel and the last.
PIPE_ROW, PIPE_X = 180, (115, 124)
RING_ROW, RING_X = 194, (116, 125)
# The liquid row: its body darkest to lightest, the glint over it and its
# surface.
L1, L2, L3, L4, L5, L6, L7, GLINT, SURFACE = range(1, 10)

# Across the fuel inside the glass's outline, left to right: a rim a little
# darker than its lit side, the glint, the brightest, then down to its
# shadowed wall.
BODY = [L5, GLINT, L7, L6, L6, L5, L4, L3, L2, L1]
LINE = [SURFACE] * 6 + [L7, L7, L6, L5]
BUBBLE = [[0, SURFACE, 0, 0], [SURFACE, 0, GLINT, 0], [0, GLINT, 0, 0], [0, 0, 0, 0]]
DROP = [[L6, 0, 0, 0]] + [[0] * BUBBLE_SIZE for _ in range(BUBBLE_SIZE - 1)]

# The meter's paddle: its outline, and its color and its shade, lit from
# the upper left.
PADDLE = {'.': 0, '#': 1, 'o': METER_PADDLE, 'x': METER_SHADE}
METER = ['...######...',
         '..#ooooox#..',
         '.#ooooooox#.',
         '.#ooooooox#.',
         '.#ooooooox#.',
         '.#ooooooox#.',
         '.#ooooooox#.',
         '.#ooooooox#.']


def widen(pixels, at, n):
    """The pixels with the one at repeated n more times."""
    return pixels[:at] + [pixels[at]] * n + pixels[at:]


def fitting():
    """The top fitting, as colors: the pipe, 14 wide, from the top of the
    screen, and at its foot the ring, 16 wide, a band of the ring's steel
    between rows of the outline."""
    _, _, backdrop = rgba(os.path.join(HERE, 'backdrop.png'))
    steel = lambda y, xs: [p[:3] for p in backdrop[y][xs[0]:xs[1] + 1]]
    pipe = [None, OUTLINE] + widen(steel(PIPE_ROW, PIPE_X), 5, 2) + [OUTLINE, None]
    ring = [OUTLINE] + widen(steel(RING_ROW, RING_X), 4, 4) + [OUTLINE]
    assert len(pipe) == len(ring) == GAUGE_W
    return [pipe] * (FITTING_H - 3) + [[OUTLINE] * GAUGE_W, ring, [OUTLINE] * GAUGE_W]


def fuel():
    """A run of the fuel, and its surface: the line on its second row, the
    liquid up the walls on its first, the run under them."""
    inside = lambda colors: [0] + colors + [0]
    run = [inside(BODY) for _ in range(LIQUID_H)]
    climb = [0] * GLASS_W
    climb[1], climb[GLASS_W - 2] = SURFACE, L6
    surface = [climb, inside(LINE)] + run[2:]
    return run, surface


def meter(row):
    """The meter's paddle, in the fitting row."""
    assert row[1] == OUTLINE and len(METER) == METER_H and all(len(line) == METER_W for line in METER)
    return [[PADDLE[c] for c in line] for line in METER]


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
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    row = [p[:3] for p in palettes[FITTING_ROW]]
    top = [[row.index(c, 1) if c else 0 for c in line] for line in fitting()]
    run, surface = fuel()
    paddle = meter(row)
    with open(args.output, 'wb') as f:
        f.write(pack(top) + pack(run) + pack(surface) + pack(BUBBLE) + pack(DROP) + pack(paddle))
    if args.preview:
        # The fitting row's colors, then the liquid row's after them.
        used = METER_SHADE + 1
        colors = palettes[FITTING_ROW][:used] + palettes[LIQUID_ROW][1:10]
        shift = lambda rows: [[c and c + used - 1 for c in row] for row in rows]
        pieces = [top, top[::-1], shift(run), shift(surface), shift(BUBBLE), shift(DROP), paddle]
        gap = [0] * 4
        rows = [sum(([p[y][x] if y < len(p) else 0 for x in range(len(p[0]))] + gap for p in pieces), [])
                for y in range(FITTING_H)]
        write_png(args.preview, len(rows[0]), FITTING_H, 3, rows, colors)


if __name__ == '__main__':
    main()
