#!/usr/bin/env python3
"""Build the tiles of the menus, as art/style/README.md describes them.

  menus.py out.bin out.h [--preview out.png]

The menus are a 4-bit tile layer of 8x8 tiles on plane 2, over everything
but the sprites, with one palette of 16 colors. A menu is a dark box with
the panels' font on it, cream with a shadow, framed in black and yellow
caution tape set in gray steel: from its outside in, a black outline, a
light steel edge, the tape, a dark steel edge, and a black line. The
tape's stripes run on 45 degrees, 4 px of each color, in TAPE palette
entries by where they fall, so turning those entries round moves the
stripes along: the tape marches. The frame comes as its 4 corners and its
4 edges; the stripes join from cell to cell. A thin rule of light steel
over its shadow sets a menu's title off from its items.

out.bin is the palette, 16 colors as png2bin.py writes a palette row, then
the tiles, 32 bytes each, the left pixel of each pair in the high nibble:
tile 0 clear, then a tile for each glyph of FONT, the space the box's
inside, then the frame, then the rule. out.h gives the tile numbers. Only the Python
standard library is used.
"""

import argparse
import struct

from panel_font import GLYPHS
from panels import FONT
from rd2png import write_png

PALETTE = [
    None,
    (2, 13, 26),      # 1 the inside of a box
    (250, 246, 234),  # 2 cream
    (206, 199, 184),  # 3 cream, darker
    (0, 0, 0),        # 4 the letters' shadow, and outlines
    (142, 160, 178),  # 5 light steel
    (92, 98, 108),    # 6 dark steel
    (240, 188, 40),   # 7 to 10: the tape, as it starts
    (240, 188, 40),
    (14, 14, 18),
    (14, 14, 18),
]
FILL, CREAM, CREAM2, OUTLINE, STEEL_LIGHT, STEEL_DARK, TAPE = range(1, 8)
TAPE_PHASES = 4


def glyph(ch):
    """A letter on the inside of a box: cream, darker toward its foot, with
    a shadow down and right, a pixel in from the left."""
    cell = [[FILL] * 8 for _ in range(8)]
    on = {(x + 1, y) for y, line in enumerate(GLYPHS.get(ch, [])) for x, c in enumerate(line) if c == '#'}
    for x, y in on:
        if (x + 1, y + 1) not in on and x + 1 < 8 and y + 1 < 8:
            cell[y + 1][x + 1] = OUTLINE
    for x, y in on:
        cell[y][x] = CREAM if y < 4 else CREAM2
    return cell


def frame(top, bottom, left, right):
    """A cell of the frame: along the top or the bottom edge, down the left
    or the right, or both, at a corner. Each pixel's color is by how far it
    is in from the box's outside edges."""
    cell = [[FILL] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            d = min(y if top else 7 - y if bottom else 9, x if left else 7 - x if right else 9)
            if d == 0 or d == 7:
                c = OUTLINE
            elif d == 1:
                c = STEEL_LIGHT
            elif d == 6:
                c = STEEL_DARK
            elif d < 6:
                c = TAPE + (x - y) % 8 // 2  # the stripe's phase, 0 to 3
            else:
                continue
            cell[y][x] = c
    return cell


def rule():
    """A cell of the rule under a title: a line of light steel across its
    middle, with a shadow under it."""
    cell = [[FILL] * 8 for _ in range(8)]
    cell[3] = [STEEL_LIGHT] * 8
    cell[4] = [OUTLINE] * 8
    return cell


FRAMES = (('TL', True, False, True, False), ('TR', True, False, False, True),
          ('BL', False, True, True, False), ('BR', False, True, False, True),
          ('T', True, False, False, False), ('B', False, True, False, False),
          ('L', False, False, True, False), ('R', False, False, False, True))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write a small box to look at')
    args = parser.parse_args()

    tiles = [[[0] * 8 for _ in range(8)]]
    tiles += [glyph(ch) for ch in FONT]
    first_frame = len(tiles)
    tiles += [frame(*f[1:]) for f in FRAMES]
    tiles.append(rule())

    data = bytearray()
    palette = PALETTE + [None] * (16 - len(PALETTE))
    for c in palette:
        r, g, b = c or (0, 0, 0)
        data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))
    for t in tiles:
        data += bytes(row[x] << 4 | row[x + 1] for row in t for x in range(0, 8, 2))
    with open(args.output, 'wb') as f:
        f.write(data)

    font_c = ''.join('\\x10' if c == '\x10' else c for c in FONT)
    with open(args.header, 'w') as f:
        f.write('/* Made by art/menus.py. The tiles of the menus. */\n\n'
                '#ifndef MENUS_H\n#define MENUS_H\n\n'
                f'#define MENU_FONT "{font_c}" /* from MENU_TILE_GLYPH, the space first */\n'
                '#define MENU_TILE_GLYPH 1\n'
                f'#define MENU_TILE_FRAME {first_frame} /* the corners, top left, top right, bottom left, '
                'bottom right, then the top, bottom, left and right edges */\n'
                f'#define MENU_TILE_RULE {len(tiles) - 1} /* under a title */\n'
                f'#define MENU_TILES {len(tiles)}\n'
                f'#define MENU_TAPE {TAPE} /* the first of the tape\'s palette entries */\n'
                f'#define MENU_TAPE_PHASES {TAPE_PHASES}\n\n'
                '#endif\n')
    print(f'menus: {len(tiles)} tiles')

    if args.preview:
        cols, rows = 12, 5
        text = 'MENU'
        grid = [[0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                top, bottom, left, right = r == 0, r == rows - 1, c == 0, c == cols - 1
                if top or bottom or left or right:
                    name = ('T' if top else 'B' if bottom else '') + ('L' if left else 'R' if right else '')
                    grid[r][c] = first_frame + [f[0] for f in FRAMES].index(name)
                else:
                    grid[r][c] = 1
        for i, ch in enumerate(text):
            grid[2][(cols - len(text)) // 2 + i] = 1 + FONT.index(ch)
        img = [[palette[tiles[grid[r][c]][y][x]] for c in range(cols) for x in range(8)]
               for r in range(rows) for y in range(8)]
        out = [[v for p in row for v in ((p + (255,)) if p else (60, 20, 90, 255))] for row in img]
        write_png(args.preview, cols * 8, rows * 8, 6, out)


if __name__ == '__main__':
    main()
