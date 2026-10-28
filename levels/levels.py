#!/usr/bin/env python3
"""The levels: each one's playfield and its bricks.

  levels.py out.bin out.h [--preview dir]

The build runs this. Each level is a function below, with what it is for
said first, which returns a Level: the playfield's walls, the inner faces
of its posts, and its bricks, each where it goes on the screen, in pixels,
and its color. The helpers lay out the usual shapes, a grid of letters
and walls with a margin each side, and a level can place anything by
hand too. LEVELS levels are written: the ones designed, then the last of
them again for the rest, until more are designed.

The checks: every brick is inside its playfield, under the beam and above
the sled, no two overlap, a level has no more than BRICKS_MAX of them, and
its posts are on the screen, the right one clear of the energy gauge.

out.bin is LEVELS level_t of src/bricks.c, one after another: the walls,
the count of bricks, a spare byte, then BRICKS_MAX bricks, each its x, its
y and its color, the rest zero. out.h #defines LEVELS and the bricks of
each level, LEVEL1_BRICKS and on, for the tests. --preview writes
level-<n>.png for each level into dir, to look at. Only the Python
standard library is used.
"""

import argparse
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'art'))
from rd2png import rgba, write_png  # noqa: E402

LEVELS = 10


def define(name, path):
    """A number #defined in a file of src/."""
    with open(os.path.join(HERE, '..', 'src', path)) as f:
        return int(re.search(rf'#define {name} (-?\d+)', f.read()).group(1))


SCREEN_W, SCREEN_H = 320, 240
BRICK_W, BRICK_H = define('BRICK_W', 'bricks.h'), define('BRICK_H', 'bricks.h')
BRICKS_MAX = define('BRICKS_MAX', 'xram.h')
BEAM_H, POST_W = define('BEAM_H', 'xram.h'), define('POST_W', 'xram.h')
GAUGE_X = define('GAUGE_X', 'play.c')
PADDLE_Y = define('TUNE_PADDLE_Y', 'tuning.h')
SLED_WIDTH_MAX = define('SLED_WIDTH_MAX', 'xram.h')
BALL = 8

# The letters of a grid, a color each, in the order of BRICK_GRAY and on,
# and . for no brick.
COLORS = 'xrgby'  # gray, red, green, blue, gold


class Level:
    """A playfield from left to right, its walls on the screen, and its
    bricks, each (x, y, color)."""

    def __init__(self, left, right, bricks):
        self.left, self.right, self.bricks = left, right, bricks


def grid(rows, x=0, y=0, gap=2):
    """Bricks from rows of letters, the top left one at x, y, each gap px
    from the next across and down."""
    return [(x + c * (BRICK_W + gap), y + r * (BRICK_H + gap), COLORS.index(ch))
            for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != '.']


def fit(bricks, left, right, top=32):
    """A level of the bricks with left px of room between the left wall and
    them, and right px between them and the right wall, the playfield in
    the middle of the screen and the bricks' top at top."""
    x0, y0 = min(b[0] for b in bricks), min(b[1] for b in bricks)
    width = max(b[0] for b in bricks) + BRICK_W - x0 + left + right
    wall = (SCREEN_W - width) // 2
    return Level(wall, wall + width, [(x - x0 + wall + left, y - y0 + top, c) for x, y, c in bricks])


def level_1():
    """A block of 4 by 4 gray bricks, 2 px apart, with half a brick of room
    for the ball between it and each wall."""
    return fit(grid(['xxxx',
                     'xxxx',
                     'xxxx',
                     'xxxx']), left=12, right=12)


def level_2():
    """Level 1 with red bricks in the middle of its top two rows, which take
    two hits."""
    return fit(grid(['xrrx',
                     'xrrx',
                     'xxxx',
                     'xxxx']), left=12, right=12)


DESIGNED = [level_1, level_2]


def check(n, level):
    def fail(message):
        sys.exit(f'levels.py: level {n}: {message}')

    if len(level.bricks) > BRICKS_MAX:
        fail(f'{len(level.bricks)} bricks, more than {BRICKS_MAX}')
    if level.left < POST_W or level.right > GAUGE_X - POST_W:
        fail(f'walls {level.left} and {level.right} put a post off the screen or over the energy gauge')
    if level.right - level.left < SLED_WIDTH_MAX:
        fail(f'{level.right - level.left} px wide, narrower than the widest sled')
    for i, (x, y, c) in enumerate(level.bricks):
        if not (level.left <= x and x + BRICK_W <= level.right and BEAM_H <= y and
                y + BRICK_H <= PADDLE_Y - 2 * BALL):
            fail(f'brick {i} at {x}, {y} is outside the playfield, or too near the beam or the sled')
        for j, (x2, y2, _) in enumerate(level.bricks[:i]):
            if abs(x - x2) < BRICK_W and abs(y - y2) < BRICK_H:
                fail(f'bricks {j} and {i} overlap')


def packed(level):
    data = struct.pack('<hhBB', level.left, level.right, len(level.bricks), 0)
    for x, y, c in level.bricks + [(0, 0, 0)] * (BRICKS_MAX - len(level.bricks)):
        data += struct.pack('<hBB', x, y, c)
    return data


def preview(level, path):
    """The level as the game lays it out, with plain posts and beam."""
    _, _, palettes = rgba(os.path.join(HERE, '..', 'art', 'palettes.png'))
    _, _, brick = rgba(os.path.join(HERE, '..', 'art', 'brick.png'))
    steel = (120, 128, 138)
    out = [[(16, 16, 20)] * SCREEN_W for _ in range(SCREEN_H)]
    for y in range(SCREEN_H):
        for x in list(range(level.left - 16, level.left)) + list(range(level.right, level.right + 16)):
            out[y][x] = steel
    for y in range(BEAM_H):
        for x in range(level.left, level.right):
            out[y][x] = steel
    for bx, by, c in level.bricks:
        for y in range(BRICK_H):
            for x in range(BRICK_W):
                out[by + y][bx + x] = palettes[1 + c][palettes[1].index(brick[y][x])][:3]
    write_png(path, SCREEN_W, SCREEN_H, 2, [[v for p in r for v in p] for r in out])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='a folder for a picture of each level')
    args = parser.parse_args()
    designed = [design() for design in DESIGNED]
    levels = designed + [designed[-1]] * (LEVELS - len(designed))
    for n, level in enumerate(levels, 1):
        check(n, level)
    with open(args.output, 'wb') as f:
        f.write(b''.join(packed(level) for level in levels))
    with open(args.header, 'w') as f:
        f.write('/* Written by levels/levels.py. */\n#ifndef LEVELS_H\n#define LEVELS_H\n\n')
        f.write(f'#define LEVELS {LEVELS}\n')
        for n, level in enumerate(levels, 1):
            f.write(f'#define LEVEL{n}_BRICKS {len(level.bricks)}\n')
        f.write('\n#endif\n')
    if args.preview:
        os.makedirs(args.preview, exist_ok=True)
        for n, level in enumerate(levels, 1):
            preview(level, os.path.join(args.preview, f'level-{n}.png'))


if __name__ == '__main__':
    main()
