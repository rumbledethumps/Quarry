#!/usr/bin/env python3
"""Build the title's panels, as art/style/README.md describes them.

  title_panels.py out.bin out.h [--preview out.png]

The title's menu and the progress of the save are on panels like the
upgrade screen's, made from art/panel-frame.png as art/panels.py makes
those: frame 1's corners, with their clamps, as they are, and its plain
steel and bolts between them. But they are a map of 4-bit tiles on plane 1,
in one palette of 16 colors, so the steel is cut to the colors that fit
beside the plate and the menus' font, merging the closest, and only the lit
tiles come, as nothing on the title dims. And every panel is symmetrical:
the run between the corners along the top and the bottom is built for its
left half and turned over for its right, the run down each side for its
top half and turned over for its bottom, and every panel has the same
pieces in the same places. The text is the menus' font on the plate.

The panels: the menu's, MENU_ROWS tall, with the progress panel hanging
from it a row below on two of the hangers of the upgrade screen, and the
smaller one of START GAME, for when there is no save. The progress panel
is too short for frame 1's two clamps down each side, one by each corner,
so its sides are plain steel, as the runs down the others' are, with one
of frame 1's clamps in the middle. Each map of MAPS is the panels as one
screen of the title shows them, COLS by ROWS cells.

The menus' items are drawn here, each centered to the pixel, so an item
of an odd length is half a cell over, in tiles of its own. The game writes
the progress, a line of FONT always an even length, so it is centered on
the cells.

out.bin is the palette, 16 colors as png2bin.py writes a palette row, then
the tiles, 32 bytes each, the left pixel of each pair in the high nibble:
tile 0 clear, then a glyph for each letter of FONT, the space the plate,
then the frames and the items. Then each map of MAPS, a byte a cell. out.h
gives the tile numbers, the maps and the rows of the text. Only the Python
standard library is used.
"""

import argparse
import os
import struct
from collections import Counter

import menus
import panels
from curtain import reduce
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))

PAD = panels.PAD
MENU_ROWS, START_ROWS, PROGRESS_ROWS = 10, 9, 7
GAP = 1  # rows between the menu's panel and the one hanging from it
PROGRESS_TOP = MENU_ROWS + GAP
COLS, ROWS = 20, PROGRESS_TOP + PROGRESS_ROWS  # a panel's width, and the most the title shows

# The left half of the run between the corners, along the top and the
# bottom of every panel: a dot is plain steel, B b a pair of bolts. The
# hangers are at the ends of the run.
EDGE = '..Bb..'
RUN = 2 * len(EDGE)
HANGERS = (0, RUN - 1)

# The menus' items, as src/title.c has them, and the rows of their text, the
# second ITEM_ROWS under the first, as src/menu.c spaces them: those of a
# save right under the menu panel's frame, and START GAME in the middle of
# its panel.
SAVE_ITEMS, SAVE_ROW = ('CONTINUE GAME', 'DELETE SAVE'), 3
START_ITEMS, START_ROW = ('START GAME',), 4
ITEM_ROWS = 3
PROGRESS_ROW = PROGRESS_TOP + PROGRESS_ROWS // 2

# The letters of the progress, PROGRESS 42%, or at 100, 100% COMPLETE!
FONT = ' ' + ''.join(sorted(set('PROGRESS 0123456789%' + '100% COMPLETE!') - {' '}))

BLACK = panels.OUTLINE
PLATE = panels.PLATE
CREAM = menus.PALETTE[menus.CREAM]
CREAM2 = menus.PALETTE[menus.CREAM2]
STEEL = 15 - 4  # the steel's colors, beside black, the plate and the creams


def mirror_x(block):
    return [row[::-1] for row in block]


def mirror_y(block):
    return block[::-1]


def panel(src, rows):
    """A panel rows cells tall, as rows of colors, None outside its frame."""
    src_rows = len(src) // 8
    side = rows - 8  # cells down each side between the corners

    def along(sr, i):
        """Cell i of the run along the top or the bottom, from source row sr."""
        if i >= len(EDGE):
            return mirror_x(along(sr, RUN - 1 - i))
        ring = sr in (1, src_rows - 2)
        ch = EDGE[i]
        col = (panels.INNER_COL if ring else panels.PLAIN_COLS[i % len(panels.PLAIN_COLS)]) if ch == '.' else \
            panels.BOLT_COLS['Bb'.index(ch)]
        return panels.cell(src, col, sr)

    def down(c, j):
        """Cell j of the run down a side, in column c."""
        if j >= (side + 1) // 2:
            return mirror_y(down(c, side - 1 - j))
        ring = c in (1, COLS - 2)
        return panels.cell(src, c, panels.INNER_ROW if ring else panels.PLAIN_ROWS[j % len(panels.PLAIN_ROWS)])

    def block(r, c):
        sr = r if r < 4 else src_rows - (rows - r) if r >= rows - 4 else None
        if r < 2 or r >= rows - 2:
            return along(sr, c - 4) if 4 <= c < COLS - 4 else panels.cell(src, c, sr)
        if c < 2 or c >= COLS - 2:
            return down(c, r - 4) if sr is None else panels.cell(src, c, sr)
        if c in (2, COLS - 3) and r in (2, rows - 3):
            return panels.cell(src, c, sr)  # the plate's rounded corners
        return [[PLATE] * 8 for _ in range(8)]

    img = [[None] * (COLS * 8) for _ in range(rows * 8)]
    for r in range(rows):
        for c in range(COLS):
            for y, line in enumerate(block(r, c)):
                img[r * 8 + y][c * 8:c * 8 + 8] = line
    return img


def one_clamp(src, img):
    """The panel's sides plain steel, the top half's as the run down a side
    starts and the bottom half's that turned over, with one of frame 1's
    clamps in the middle of each."""
    rows = len(img) // 8
    for c in (0, COLS - 1):
        plain = panels.cell(src, c, panels.PLAIN_ROWS[0])
        for r in range(2, rows - 2):
            for y, line in enumerate(plain if 2 * r <= rows - 1 else mirror_y(plain)):
                img[r * 8 + y][c * 8:c * 8 + 8] = line
    (y0, y1), = panels.CLAMPS_DOWN
    top = (rows * 8 - (y1 - y0 + 1)) // 2
    for y in range(y0, y1 + 1):
        for x in list(range(8)) + list(range(COLS * 8 - 8, COLS * 8)):
            img[top + y - y0][x] = src[y][x]
    return img


def place(screen, img, row):
    for y, line in enumerate(img):
        screen[row * 8 + y] = line[:]


def hangers(screen):
    """The hangers' bars from the menu's panel down to the progress panel,
    from two pixels into one frame to two into the other: those of the
    upgrade screen, each side the other's mirror but lit from the left."""
    top, bottom = MENU_ROWS * 8 - PAD - 2, PROGRESS_TOP * 8 + PAD + 2
    for h in HANGERS:
        x0 = (4 + h) * 8 + 2 if h < len(EDGE) else COLS * 8 - 1 - ((4 + RUN - 1 - h) * 8 + 6)
        for y in range(top, bottom):
            for dx, color in enumerate((BLACK, panels.SHINE, panels.STEEL, panels.DARK, BLACK)):
                screen[y][x0 + dx] = color


def glyph(ch):
    """A letter of the menus' font, on the plate."""
    colors = {menus.FILL: PLATE, menus.CREAM: CREAM, menus.CREAM2: CREAM2, menus.OUTLINE: BLACK}
    return [[colors[i] for i in row] for row in menus.glyph(ch)]


def items(screen, words, row):
    """The menu's items on its panel, each centered to the pixel on a row,
    ITEM_ROWS apart."""
    for i, word in enumerate(words):
        x0 = COLS * 4 - 4 * len(word)
        for j, ch in enumerate(word):
            for y, line in enumerate(glyph(ch)):
                screen[(row + i * ITEM_ROWS) * 8 + y][x0 + 8 * j:x0 + 8 * j + 8] = line


def screens(src):
    """The maps of the title as pictures, in the order of MAPS."""
    blank = lambda: [[None] * (COLS * 8) for _ in range(ROWS * 8)]
    save, start = blank(), blank()
    place(save, panel(src, MENU_ROWS), 0)
    place(save, one_clamp(src, panel(src, PROGRESS_ROWS)), PROGRESS_TOP)
    hangers(save)
    items(save, SAVE_ITEMS, SAVE_ROW)
    place(start, panel(src, START_ROWS), 0)
    items(start, START_ITEMS, START_ROW)
    return [save, start]


# The maps, in order: the menu's panel and the progress panel hanging from
# it, as with a save, and the panel of START GAME, with none.
MAPS = ('SAVE', 'START')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write each map to look at')
    args = parser.parse_args()

    _, _, frame = rgba(os.path.join(HERE, 'panel-frame.png'))
    pictures = screens(panels.source(frame))

    # The steel down to the colors that fit, merging the closest.
    counts = Counter(c for pic in pictures for row in pic for c in row if c not in (None, BLACK, PLATE, CREAM, CREAM2))
    to = reduce(counts, STEEL)
    pictures = [[[to.get(c, c) for c in row] for row in pic] for pic in pictures]
    colors = sorted({BLACK, PLATE, CREAM, CREAM2} | set(to.values()), key=lambda c: 299 * c[0] + 587 * c[1] + 114 * c[2])
    if len(colors) > 15:
        raise SystemExit(f'title_panels: {len(colors)} colors, past 15')
    index = {c: i + 1 for i, c in enumerate(colors)}
    index[None] = 0

    def key(block):
        return tuple(index[c] for row in block for c in row)

    tiles = [key([[None] * 8 for _ in range(8)])] + [key(glyph(ch)) for ch in FONT]
    maps = []
    for pic in pictures:
        grid = bytearray()
        for r in range(ROWS):
            for c in range(COLS):
                t = key([line[c * 8:c * 8 + 8] for line in pic[r * 8:r * 8 + 8]])
                if t not in tiles:
                    tiles.append(t)
                grid.append(tiles.index(t))
        maps.append(grid)
    if len(tiles) > 256:
        raise SystemExit(f'title_panels: {len(tiles)} tiles, past 256')

    data = bytearray()
    for c in [None] + colors + [None] * (15 - len(colors)):
        r, g, b = c or (0, 0, 0)
        data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))
    for t in tiles:
        data += bytes(t[i] << 4 | t[i + 1] for i in range(0, 64, 2))
    for grid in maps:
        data += grid
    with open(args.output, 'wb') as f:
        f.write(data)

    with open(args.header, 'w') as f:
        f.write('/* Made by art/title_panels.py. The tiles of the title\'s panels. */\n\n'
                '#ifndef TITLE_PANELS_H\n#define TITLE_PANELS_H\n\n'
                f'#define TITLE_FONT "{FONT}" /* from TITLE_TILE_GLYPH, the space, the plate, first */\n'
                '#define TITLE_TILE_GLYPH 1\n'
                f'#define TITLE_TILES {len(tiles)}\n'
                f'#define TITLE_COLS {COLS}\n'
                f'#define TITLE_ROWS {ROWS}\n'
                + ''.join(f'#define TITLE_MAP_{name} {i}\n' for i, name in enumerate(MAPS)) +
                f'#define TITLE_MAPS {len(MAPS)}\n'
                f'#define TITLE_SAVE_ROW {SAVE_ROW} /* the text of the first item of a save, of its map */\n'
                f'#define TITLE_START_ROW {START_ROW} /* the text of START GAME */\n'
                f'#define TITLE_PROGRESS_ROW {PROGRESS_ROW} /* the progress, which the game writes */\n\n'
                '#endif\n')
    print(f'title_panels: {len(tiles)} tiles, {len(tiles) - 1 - len(FONT)} of them the frames and the items; '
          f'the steel in {STEEL} colors, from {len(counts)}')

    if args.preview:
        back = (40, 10, 60)
        out = [[] for _ in range(ROWS * 8)]
        for i, grid in enumerate(maps):
            for y in range(ROWS * 8):
                for x in range(COLS * 8):
                    t = tiles[grid[y // 8 * COLS + x // 8]][y % 8 * 8 + x % 8]
                    out[y] += list(colors[t - 1] if t else back)
                if i < len(maps) - 1:
                    out[y] += list(back) * 8
        write_png(args.preview, len(out[0]) // 3, ROWS * 8, 2, out)


if __name__ == '__main__':
    main()
