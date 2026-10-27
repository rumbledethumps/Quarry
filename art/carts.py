#!/usr/bin/env python3
"""Draw the mine carts of the upgrade screen's stage select, as art/style/README.md describes them.

  carts.py out.bin out.h [--preview out.png]

A placeholder until the carts get their own art. A cart is 4 cells across
and 4 down, in 4-bit 8x8 tiles of one 16-color palette: a heap of ore on
top for a stage cleared, down onto the rim, then the body with a plate for
the stage's number in its two middle cells, and the wheels. The number is
in the middle of the cart, so the cart stands low in its cells, and its
top two rows come with the heap and without. The cell after
each cart holds the coupling to the next. The number's digits come lit and
dim. A locked stage's plate is blank, under a padlock: a 16x16 sprite in
the same palette, which also comes in two 8x16 halves, so it can break in
two. The steel is frame 1's, from art/panel-frame.png's colors.

out.bin is the palette, 16 colors as png2bin.py writes a palette row, then
the padlock and its halves, then the tiles, 32 bytes each, all with the
left pixel of each pair in the high nibble. out.h gives the tile numbers
and the padlock's place on its cart. Only the Python standard library is
used.
"""

import argparse
import struct

from panel_font import GLYPHS
from rd2png import write_png

PALETTE = [
    None,
    (0, 0, 0),        # 1 outline
    (42, 47, 51),     # 2 dark steel
    (253, 212, 66),   # 3 gold, lit
    (89, 96, 100),    # 4 mid steel
    (141, 154, 157),  # 5 light steel
    (201, 218, 220),  # 6 shine
    (30, 38, 48),     # 7 plate
    (18, 24, 32),     # 8 shadow
    (246, 242, 232),  # 9 cream
    (206, 199, 184),  # 10 cream, darker
    (104, 110, 118),  # 11 a dim digit
    (247, 183, 36),   # 12 gold
    (173, 111, 21),   # 13 dark gold
    (214, 214, 220),  # 14 ore
    (150, 150, 160),  # 15 ore, darker
]
OUT, DARK, GOLD_LIT, MID, LIGHT, SHINE, PLATE, SHADOW, CREAM, CREAM2, DIMTXT, GOLD, GOLD2, ORE, ORE2 = range(1, 16)

W, H = 32, 32


def blank(w, h, c=0):
    return [[c] * w for _ in range(h)]


def cart(heaped):
    """The cart, 32x32. Its number sits in the middle of it, so it stands
    low in its cells: a heap of ore on top, if heaped, down onto the rim at
    10, the body, with the plate's frame in it around the plate's two
    cells, and the wheels at the foot, in front of the body."""
    img = blank(W, H)
    if heaped:
        for x in range(3, W - 3):
            top = 9 - int(5 * (1 - ((x - W / 2) / (W / 2 - 3)) ** 2))
            for y in range(top, 10):
                img[y][x] = ORE2 if (x * 7 + y * 3) % 5 == 0 else ORE
            img[top][x] = OUT
        for x, y in ((9, 7), (14, 5), (19, 5), (23, 8), (12, 8), (17, 7)):
            img[y][x] = ORE2
            img[y - 1][x - 1] = SHINE
    for x in range(W):
        img[10][x] = img[13][x] = OUT
        img[11][x] = SHINE
        img[12][x] = LIGHT
    img[11][0] = img[12][0] = img[11][W - 1] = img[12][W - 1] = OUT
    for y in range(14, 28):
        inset = 2 + (y - 14) * 2 // 13
        for x in range(inset, W - inset):
            img[y][x] = DARK if y == 14 else MID
        img[y][inset] = img[y][W - 1 - inset] = OUT
        img[y][inset + 1] = LIGHT
        img[y][W - 2 - inset] = DARK
    for x in range(4, W - 4):
        img[28][x] = OUT
    # The plate is the cells 8 to 23 across and 16 to 23 down, and a line
    # more of it all round but the foot, then its frame, sunk in the body.
    for y in range(15, 24):
        img[y][7] = img[y][24] = PLATE
    for x in range(7, 25):
        img[15][x] = PLATE
    for x in range(6, 26):
        img[24][x] = LIGHT
    for y in range(14, 24):
        img[y][6] = DARK
        img[y][25] = LIGHT
    for cx in (8, 23):
        for y in range(25, 32):
            for x in range(cx - 4, cx + 4):
                d = (x + 0.5 - cx) ** 2 + (y + 0.5 - 28.5) ** 2
                if d < 10:
                    img[y][x] = DARK if d < 5 else OUT
        img[28][cx - 1] = SHINE
    for x, y in ((4, 16), (27, 16), (5, 22), (26, 22)):
        img[y][x] = SHINE
        img[y + 1][x] = DARK
    return img


def plate_cell(ch, colors):
    """A cell of the plate, with a glyph of the panels' font."""
    cell = blank(8, 8, PLATE)
    # A pixel in from the left, so two digits sit in the middle of the plate.
    on = {(x + 1, y) for y, line in enumerate(GLYPHS[ch]) for x, c in enumerate(line) if c == '#'}
    for x, y in on:
        if (x + 1, y + 1) not in on and x + 1 < 8 and y + 1 < 8:
            cell[y + 1][x + 1] = SHADOW
    for x, y in on:
        cell[y][x] = colors[0] if y < 4 else colors[1]
    return cell


# The padlock, with its keyhole in the middle, as the plate's number is.
LOCK = ['.....######.....',
        '....#sSSSSs#....',
        '...#sS####Ss#...',
        '...#s#....#s#...',
        '...#s#....#s#...',
        '...#s#....#s#...',
        '.##############.',
        '.#hhhhhhhhhhhh#.',
        '.#hffff##ffffr#.',
        '.#hfff####fffr#.',
        '.#hfff####fffr#.',
        '.#hffff##ffffr#.',
        '.#hffff##ffffr#.',
        '.#rrrrrrrrrrrr#.',
        '.##############.',
        '................']
LOCK_COLORS = {'.': 0, '#': OUT, 's': LIGHT, 'S': SHINE, 'h': GOLD_LIT, 'f': GOLD, 'r': GOLD2}
# Where the padlock goes on its cart: its body over the plate.
LOCK_LEFT, LOCK_TOP = 8, 9


def lock():
    return [[LOCK_COLORS[c] for c in line] for line in LOCK]


def packed(img):
    return bytes(row[x] << 4 | row[x + 1] for row in img for x in range(0, len(row), 2))


def coupling():
    """The link to the next cart, in the cell after a cart, at its foot."""
    cell = blank(8, 8)
    for x in range(8):
        cell[1][x] = OUT
        cell[2][x] = MID
        cell[3][x] = OUT
    return cell


def cells(img):
    return [[[row[cx * 8:cx * 8 + 8] for row in img[cy * 8:cy * 8 + 8]] for cx in range(len(img[0]) // 8)]
            for cy in range(len(img) // 8)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write a cleared cart, an open one and a locked one')
    args = parser.parse_args()

    heaped, body = cells(cart(True)), cells(cart(False))
    tiles = [blank(8, 8)]  # tile 0 is clear
    names = []

    def add(name, tile):
        names.append((name, len(tiles)))
        tiles.append(tile)

    for r in (0, 1):
        for c in range(4):
            add(f'HEAP_{r}_{c}', heaped[r][c])
    for r in (1, 2, 3):
        for c in range(4):
            if r == 2 and c in (1, 2):
                continue
            add(f'BODY_{r}_{c}', body[r][c])
    add('COUPLING', coupling())
    add('PLATE', blank(8, 8, PLATE))
    for d in '0123456789':
        add(f'DIGIT_{d}', plate_cell(d, (CREAM, CREAM2)))
    for d in '0123456789':
        add(f'DIM_{d}', plate_cell(d, (DIMTXT, DIMTXT)))

    data = bytearray()
    for c in PALETTE:
        r, g, b = c or (0, 0, 0)
        data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))
    padlock = lock()
    data += packed(padlock)
    data += packed([row[:8] for row in padlock]) + packed([row[8:] for row in padlock])
    for t in tiles:
        data += packed(t)
    with open(args.output, 'wb') as f:
        f.write(data)

    first = dict(names)
    with open(args.header, 'w') as f:
        f.write('/* Made by art/carts.py. The tiles of the stage select\'s mine carts. */\n\n'
                '#ifndef CARTS_H\n#define CARTS_H\n\n'
                f'#define CART_TILE_HEAP {first["HEAP_0_0"]} /* the top two rows of a cart with a heap, 4 across */\n'
                f'#define CART_TILE_BODY {first["BODY_1_0"]} /* a cart under its top row, row by row, without the plate */\n'
                f'#define CART_TILE_COUPLING {first["COUPLING"]}\n'
                f'#define CART_TILE_PLATE {first["PLATE"]} /* blank, under a padlock */\n'
                f'#define CART_TILE_DIGIT {first["DIGIT_0"]} /* lit, then dim, 0 to 9 */\n'
                f'#define CART_TILE_DIM {first["DIM_0"]}\n'
                f'#define CART_TILES {len(tiles)}\n'
                f'#define CART_LOCK_LEFT {LOCK_LEFT} /* the padlock\'s place on its cart */\n'
                f'#define CART_LOCK_TOP {LOCK_TOP}\n\n'
                '#endif\n')
    print(f'carts: {len(tiles)} tiles')

    if args.preview:
        def compose(heaped, plate):
            img = blank(W + 8, H)
            grid = [[None] * 5 for _ in range(4)]
            i = first['BODY_1_0']
            for r in (1, 2, 3):
                for c in range(4):
                    if r == 2 and c in (1, 2):
                        grid[r][c] = plate[c - 1]
                    else:
                        grid[r][c] = tiles[i]
                        i += 1
            if heaped:
                for c in range(4):
                    grid[0][c] = tiles[first['HEAP_0_0'] + c]
                    grid[1][c] = tiles[first['HEAP_1_0'] + c]
            grid[3][4] = tiles[first['COUPLING']]
            for r in range(4):
                for c in range(5):
                    if grid[r][c]:
                        for y in range(8):
                            for x in range(8):
                                img[r * 8 + y][c * 8 + x] = grid[r][c][y][x]
            return img
        d = lambda n: tiles[first['DIGIT_0'] + n]
        dm = lambda n: tiles[first['DIM_0'] + n]
        locked = compose(False, [tiles[first['PLATE']]] * 2)
        for y, row in enumerate(padlock):
            for x, c in enumerate(row):
                if c:
                    locked[LOCK_TOP + y][LOCK_LEFT + x] = c
        carts = [compose(True, [d(0), d(1)]), compose(True, [dm(0), dm(2)]), compose(False, [dm(0), dm(3)]), locked]
        out = [[c for img in carts for c in img[y]] for y in range(H)]
        rows = [[v for c in row for v in ((PALETTE[c] + (255,)) if c else (40, 10, 60, 255))] for row in out]
        write_png(args.preview, len(out[0]), H, 6, rows)


if __name__ == '__main__':
    main()
