#!/usr/bin/env python3
"""Build the upgrade screen's backdrop, as art/style/README.md describes it.

  backdrop.py out.bin out.h [--preview out.png]

The backdrop is two bands of 4-bit 16x16 tiles on plane 0, behind
everything: the ceiling across the top, from art/backdrop-ceiling.png, and
the floor along the foot, from art/backdrop-floor.png, both 320 wide, from
Retro Diffusion. Between them is plain wall, which the panels hide but for
the gaps between them, so each band can move on its own. Each band is
darkened, and a little cool, so the steel of the panels and the carts
stands out in front of it, and cut to 15 colors of its own palette, the
wall's color the first of them, the same in both.

A band's map is the whole screen high, ROWS rows, and a row more of its
art past its outer edge, so it can move a row and still fill the screen:
the ceiling's top row again over it, and the floor's bottom row again
under it. The rest is wall, tile 0.

out.bin is, for the ceiling and then the floor: the palette, 16 colors as
png2bin.py writes a palette row, the tiles, 128 bytes each, the left pixel
of each pair in the high nibble, and the map, a byte a cell, row by row.
out.h gives the sizes. Only the Python standard library is used.
"""

import argparse
import os
import struct
from collections import Counter

from curtain import reduce
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
DARKEN = (0.58, 0.6, 0.66)  # red, green and blue, darker and a little cool
COLS, ROWS = 20, 16          # of a band's map: the screen, and a row more
TILE = 16


def band(path):
    """A band's art, darkened, as rows of colors."""
    width, height, pixels = rgba(os.path.join(HERE, path))
    if width != COLS * TILE or height % TILE:
        raise SystemExit(f'backdrop: {path} is {width}x{height}, not {COLS * TILE} wide in whole tiles')
    return [[tuple(round(v * d) for v, d in zip(p[:3], DARKEN)) for p in row] for row in pixels]


def wall_color(art):
    """The wall: the floor's most common color of the darkest ones."""
    counts = Counter(c for row in art for c in row)
    dark = sorted(counts, key=sum)[:len(counts) // 3]
    return max(dark, key=lambda c: counts[c])


def build(art, wall, wall_rows_first):
    """A band's palette, tiles and map, its art at the top of the map after
    a row of its top row again, or at the foot before a row of its bottom
    row again."""
    counts = Counter(c for row in art for c in row if c != wall)
    to = reduce(counts, 14)
    to[wall] = wall
    colors = [wall] + sorted(set(to.values()) - {wall}, key=lambda c: 299 * c[0] + 587 * c[1] + 114 * c[2])
    index = {c: colors.index(to[c]) + 1 for c in to}
    tiles = [tuple([1] * TILE * TILE)]  # tile 0 is wall
    cells = []
    for ty in range(len(art) // TILE):
        line = []
        for tx in range(COLS):
            t = tuple(index[art[ty * TILE + y][tx * TILE + x]] for y in range(TILE) for x in range(TILE))
            if t not in tiles:
                tiles.append(t)
            line.append(tiles.index(t))
        cells.append(line)
    walls = [[0] * COLS for _ in range(ROWS - len(cells) - 1)]
    grid = walls + cells + [cells[-1]] if wall_rows_first else [cells[0]] + cells + walls
    if len(tiles) > 256:
        raise SystemExit(f'backdrop: {len(tiles)} tiles in a band, past 256')
    return colors, tiles, grid


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write the backdrop, both bands at their places, as a PNG')
    args = parser.parse_args()

    ceiling, floor = band('backdrop-ceiling.png'), band('backdrop-floor.png')
    wall = wall_color(floor)
    bands = [build(ceiling, wall, False), build(floor, wall, True)]

    data = bytearray()
    for colors, tiles, grid in bands:
        palette = [(0, 0, 0, 0)] + [c + (255,) for c in colors]
        palette += [(0, 0, 0, 0)] * (16 - len(palette))
        for r, g, b, a in palette:
            data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if a else 0))
        for t in tiles:
            data += bytes(t[i] << 4 | t[i + 1] for i in range(0, len(t), 2))
        for line in grid:
            data += bytes(line)
    with open(args.output, 'wb') as f:
        f.write(data)

    with open(args.header, 'w') as f:
        f.write('/* Made by art/backdrop.py. The upgrade screen\'s backdrop. */\n\n'
                '#ifndef BACKDROP_H\n#define BACKDROP_H\n\n'
                f'#define BACKDROP_COLS {COLS}\n'
                f'#define BACKDROP_ROWS {ROWS} /* of each band\'s map */\n'
                f'#define BACKDROP_CEILING_TILES {len(bands[0][1])}\n'
                f'#define BACKDROP_CEILING_H {len(ceiling)} /* of its art, from map row 1 */\n'
                f'#define BACKDROP_FLOOR_TILES {len(bands[1][1])}\n'
                f'#define BACKDROP_FLOOR_H {len(floor)} /* of its art, to the map\'s row before last */\n\n'
                '#endif\n')
    print(f'backdrop: {len(bands[0][1])} tiles of ceiling and {len(bands[1][1])} of floor, '
          f'{len(data)} bytes')

    if args.preview:
        # The ceiling's art at the top of the screen, and the floor's at the
        # foot, from halfway down.
        h = 240
        out = [[None] * (COLS * TILE) for _ in range(h)]
        for (colors, tiles, grid), top, rows in zip(bands, (-TILE, h - (ROWS - 1) * TILE),
                                                    (range(0, h // 2), range(h // 2, h))):
            for sy in rows:
                ty, y = divmod(sy - top, TILE)
                for tx, t in enumerate(grid[ty]):
                    for x in range(TILE):
                        out[sy][tx * TILE + x] = colors[tiles[t][y * TILE + x] - 1]
        rows = [[v for c in row for v in (c + (255,))] for row in out]
        write_png(args.preview, COLS * TILE, h, 6, rows)


if __name__ == '__main__':
    main()
