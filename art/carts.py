#!/usr/bin/env python3
"""Build the mine carts of the upgrade screen's stage select, as art/style/README.md describes them.

  carts.py out.bin out.h [--preview out.png]

A cart is art/cart.png, from Retro Diffusion, 32x24: a graphite steel tub
with a yellow rim and two wheels. It stands in cells 4 across and
CELL_ROWS down, in 4-bit 8x8 tiles of one 16-color palette, low enough
that the stage's number on its side is in the middle of it, rim to foot:
the number is a plate in the cart's two middle cells of row PLATE_ROW,
drawn here over the art's own plate. A stage cleared carries a heap of ore
over the rim, so the cart's top two rows come with the heap and without.
The cell after each cart holds the coupling to the next, at the wheels'
axles. The number's digits come lit and dim, in the panels' font.

A locked stage's plate is blank, under a padlock: art/padlock.png, from
Retro Diffusion, 16x16, a sprite with a palette of its own, its body over
the plate and its shackle over the rim. It also comes in two 8x16 halves,
so it can break in two.

out.bin is the carts' palette and the padlock's, 16 colors each as
png2bin.py writes a palette row, then the padlock and its halves, then the
tiles, 32 bytes each, all with the left pixel of each pair in the high
nibble. out.h gives the tile numbers and the places on a cart. Only the
Python standard library is used.
"""

import argparse
import os
import struct
from collections import Counter

from curtain import reduce
from panel_font import GLYPHS
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
W, CELL_ROWS = 32, 5
H = CELL_ROWS * 8
TOP = 11         # the art's top in the cells, so its rim is at 12
RIM = TOP + 1    # the top of the rim, under any heap
FOOT = TOP + 24  # just under the wheels, where the track is
PLATE_ROW = 2
COUPLING_ROW = 3
# The plate: inside, the two middle cells of PLATE_ROW and a pixel more
# each side, under its frame.
PLATE_X0, PLATE_X1 = 7, 25
PLATE_Y0, PLATE_Y1 = PLATE_ROW * 8, PLATE_ROW * 8 + 8
# The colors that must stay as they are: the plate and the digits.
PLATE = (30, 38, 48)
SHADOW = (18, 24, 32)
CREAM, CREAM2 = (246, 242, 232), (206, 199, 184)
DIMTXT = (104, 110, 118)
ORE, ORE2 = (214, 214, 220), (150, 150, 160)
# The padlock: its body over the plate, its shackle over the rim.
LOCK_LEFT, LOCK_BODY = 8, 7  # its left in the cart, and its first row of body
LOCK_TOP = PLATE_Y0 - LOCK_BODY


def art(name):
    """An image of art/ as rows of colors, None where it is clear."""
    _, _, pixels = rgba(os.path.join(HERE, name))
    return [[p[:3] if p[3] >= 128 else None for p in row] for row in pixels]


def luma(c):
    return (299 * c[0] + 587 * c[1] + 114 * c[2]) // 1000


def cart(heaped):
    """The cart in its cells: the art, the plate's frame and inside over its
    own plate, hooks for the couplings at each end, and the heap, if heaped."""
    src = art('cart.png')
    img = [[None] * W for _ in range(H)]
    for y, row in enumerate(src):
        for x, c in enumerate(row):
            img[TOP + y][x] = c
    shades = sorted({c for row in src for c in row if c}, key=luma)
    dark, light = shades[1], shades[len(shades) * 3 // 4]
    for y in range(PLATE_Y0 - 1, PLATE_Y1 + 1):
        for x in range(PLATE_X0 - 1, PLATE_X1 + 1):
            edge_dark = y == PLATE_Y0 - 1 or x == PLATE_X0 - 1
            edge_light = y == PLATE_Y1 or x == PLATE_X1
            img[y][x] = dark if edge_dark else light if edge_light else PLATE
    axle = FOOT - 5
    for x in (0, W - 1):
        img[axle - 1][x] = img[axle + 1][x] = shades[0]
        img[axle][x] = shades[len(shades) // 2]
    if heaped:
        for x in range(3, W - 3):
            # Flat across its top, with no lone pixel on the peak.
            top = RIM - 1 - min(4, int(5 * (1 - ((x - W / 2) / (W / 2 - 3)) ** 2)))
            for y in range(top, RIM):
                img[y][x] = ORE2 if (x * 7 + y * 3) % 5 == 0 else ORE
            img[top][x] = shades[0]
    return img


def coupling(img):
    """The link to the next cart, in the cell after it, at the axles, in
    the colors of the hooks at the cart's ends."""
    cell = [[None] * 8 for _ in range(8)]
    axle = FOOT - 5 - COUPLING_ROW * 8
    for x in range(8):
        cell[axle - 1][x] = cell[axle + 1][x] = img[FOOT - 6][0]
        cell[axle][x] = img[FOOT - 5][0]
    return cell


def plate_cell(ch, colors):
    """A cell of the plate, with a glyph of the panels' font, or none."""
    cell = [[PLATE] * 8 for _ in range(8)]
    if ch:
        # A pixel in from the left, so two digits sit in the middle of the plate.
        on = {(x + 1, y) for y, line in enumerate(GLYPHS[ch]) for x, c in enumerate(line) if c == '#'}
        for x, y in on:
            if (x + 1, y + 1) not in on and x + 1 < 8 and y + 1 < 8:
                cell[y + 1][x + 1] = SHADOW
        for x, y in on:
            cell[y][x] = colors[0] if y < 4 else colors[1]
    return cell


def padlock():
    """art/padlock.png, the white inside its shackle clear, and outlined
    along its foot."""
    img = art('padlock.png')
    darkest = min((c for row in img for c in row if c), key=luma)
    for y in range(LOCK_BODY):
        for x in range(16):
            if img[y][x] and luma(img[y][x]) > 220:
                img[y][x] = None
    img[15] = [darkest if c else None for c in img[15]]
    return img


def cells(img):
    return [[[row[cx * 8:cx * 8 + 8] for row in img[cy * 8:cy * 8 + 8]] for cx in range(len(img[0]) // 8)]
            for cy in range(len(img) // 8)]


def palette_of(images, fixed, n):
    """The colors of images cut to n: fixed as they are, the rest merged
    into what is left. Returns the palette, None first, and a map from each
    color to its index."""
    counts = Counter(c for img in images for row in img for c in row if c and c not in fixed)
    to = reduce(counts, n - len(fixed)) if counts else {}
    colors = fixed + sorted(set(to.values()), key=luma)
    palette = [None] + colors + [None] * (15 - len(colors))
    index = {c: palette.index(to.get(c, c)) for c in list(to) + fixed}
    return palette, index


def packed(img, index):
    return bytes(index.get(row[x], 0) << 4 | index.get(row[x + 1], 0) for row in img for x in range(0, len(row), 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write a cleared cart, an open one and a locked one, on a track')
    args = parser.parse_args()

    heaped, plain = cart(True), cart(False)
    heap_top = min(y for y, row in enumerate(heaped) if any(row))
    link = coupling(plain)
    heaped_cells, body = cells(heaped), cells(plain)
    tiles = [[[None] * 8 for _ in range(8)]]  # tile 0 is clear
    names = []

    def add(name, tile):
        names.append((name, len(tiles)))
        tiles.append(tile)

    for r in (0, 1):
        for c in range(4):
            add(f'HEAP_{r}_{c}', heaped_cells[r][c])
    for r in range(1, CELL_ROWS):
        for c in range(4):
            if r == PLATE_ROW and c in (1, 2):
                continue
            add(f'BODY_{r}_{c}', body[r][c])
    add('COUPLING', link)
    add('PLATE', plate_cell(None, None))
    for d in '0123456789':
        add(f'DIGIT_{d}', plate_cell(d, (CREAM, CREAM2)))
    for d in '0123456789':
        add(f'DIM_{d}', plate_cell(d, (DIMTXT, DIMTXT)))

    palette, index = palette_of([heaped, plain, link], [PLATE, SHADOW, CREAM, CREAM2, DIMTXT], 15)
    lock = padlock()
    lock_palette, lock_index = palette_of([lock], [], 15)

    data = bytearray()
    for pal in (palette, lock_palette):
        for c in pal:
            r, g, b = c or (0, 0, 0)
            data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))
    data += packed(lock, lock_index)
    data += packed([row[:8] for row in lock], lock_index) + packed([row[8:] for row in lock], lock_index)
    for t in tiles:
        data += packed(t, index)
    with open(args.output, 'wb') as f:
        f.write(data)

    first = dict(names)
    with open(args.header, 'w') as f:
        f.write('/* Made by art/carts.py. The tiles of the stage select\'s mine carts. */\n\n'
                '#ifndef CARTS_H\n#define CARTS_H\n\n'
                f'#define CART_CELL_ROWS {CELL_ROWS}\n'
                f'#define CART_TILE_HEAP {first["HEAP_0_0"]} /* the top two rows of a cart with a heap, 4 across */\n'
                f'#define CART_TILE_BODY {first["BODY_1_0"]} /* a cart under its top row, row by row, without the plate */\n'
                f'#define CART_TILE_COUPLING {first["COUPLING"]}\n'
                f'#define CART_COUPLING_ROW {COUPLING_ROW}\n'
                f'#define CART_TILE_PLATE {first["PLATE"]} /* blank, under a padlock */\n'
                f'#define CART_PLATE_ROW {PLATE_ROW}\n'
                f'#define CART_TILE_DIGIT {first["DIGIT_0"]} /* lit, then dim, 0 to 9 */\n'
                f'#define CART_TILE_DIM {first["DIM_0"]}\n'
                f'#define CART_TILES {len(tiles)}\n'
                f'#define CART_RIM {RIM} /* the top of the rim, under any heap */\n'
                f'#define CART_HEAP_TOP {heap_top} /* the top of the heap */\n'
                f'#define CART_FOOT {FOOT} /* just under the wheels, where the track is */\n'
                f'#define CART_LOCK_LEFT {LOCK_LEFT} /* the padlock\'s place on its cart */\n'
                f'#define CART_LOCK_TOP {LOCK_TOP}\n\n'
                '#endif\n')
    print(f'carts: {len(tiles)} tiles')

    if args.preview:
        cut = {c: palette[i] for c, i in index.items()}
        lock_cut = {c: lock_palette[i] for c, i in lock_index.items()}

        def compose(top, plate, locked=False):
            """A cart and its coupling, as the palettes show them, on a
            stand-in track."""
            img = [[None] * (W + 8) for _ in range(H + 2)]
            for r in range(CELL_ROWS):
                for c in range(5):
                    if c == 4:
                        cell = link if r == COUPLING_ROW else None
                    elif r == PLATE_ROW and c in (1, 2):
                        cell = plate[c - 1]
                    else:
                        cell = (top if r < 2 else body)[r][c]
                    if cell:
                        for y in range(8):
                            for x in range(8):
                                if cell[y][x]:
                                    img[r * 8 + y][c * 8 + x] = cut[cell[y][x]]
            if locked:
                for y, row in enumerate(lock):
                    for x, c in enumerate(row):
                        if c:
                            img[LOCK_TOP + y][LOCK_LEFT + x] = lock_cut[c]
            for x in range(W + 8):
                img[FOOT][x] = img[FOOT + 1][x] = (120, 126, 130)
            return img
        lit = lambda n: plate_cell(str(n), (CREAM, CREAM2))
        dim = lambda n: plate_cell(str(n), (DIMTXT, DIMTXT))
        carts = [compose(heaped_cells, [lit(0), lit(1)]), compose(heaped_cells, [dim(0), dim(2)]),
                 compose(body, [dim(0), dim(3)]), compose(body, [plate_cell(None, None)] * 2, True)]
        out = [[c for img in carts for c in img[y]] for y in range(H + 2)]
        rows = [[v for c in row for v in ((c + (255,)) if c else (40, 10, 60, 255))] for row in out]
        write_png(args.preview, len(out[0]), len(out), 6, rows)


if __name__ == '__main__':
    main()
