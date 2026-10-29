#!/usr/bin/env python3
"""Build the dwarves and what they say, as art/style/README.md describes them.

  talk.py out_dir header [--preview out.png --behind screen.png]

A dwarf is a portrait Retro Diffusion drew, art/dwarves/name.png: his head
and shoulders on a plain background, in a frame of its own. The frame is
cut off, the background cleared from the edges in, and his colors brought
down to 15. He is a few 4-bit sprites, a band across his head and a band
across his shoulders, each as narrow as he is there, so the clear corners
take no room.

His speech bubble is a map of 2-bit tiles: clear, ink, paper and a shade
of paper along its foot. Its corners, edges and tail are drawn by hand
below, the tail reaching out of its left side toward his mouth, and its
lines are the panels' font in ink, a row of cells between them. The last
line ends with an OK, at the right, which the game puts in once the
bubble has come in. The bubble is cut into tiles, the same ones shared.

TALKS lists what the dwarves say: each one's name, the dwarf, his lines,
and where he and his bubble stand when they are in. Each becomes
out_dir/talkN.bin, from 1, a talk_t of src/xram.h, and the header gives
their numbers as TALK_name. Only the Python standard library is used.
"""

import argparse
import os
import struct
from collections import Counter

from curtain import reduce
from panel_font import GLYPHS
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))

# As src/xram.h gives them.
DWARF_SIZE = 80
DWARF_PIECES = 3
DWARF_BYTES = 2816
BUBBLE_COLS = 28
BUBBLE_ROWS = 10
BUBBLE_TILES = 48
TALK_BYTES = 14 + 8 * DWARF_PIECES + 32 + DWARF_BYTES + 8 + 16 * BUBBLE_TILES + BUBBLE_ROWS * BUBBLE_COLS
SCREEN_H = 240

# Where they stand: he is in the lower left corner, and his bubble beside
# him, its tail under his beard. The bubble is placed by its left and its
# foot, so the tail is as high whatever its lines. On the upgrade screen
# its foot is over the carts, which show what he talks about.
LEVEL = {'dwarf': (0, SCREEN_H - DWARF_SIZE), 'bubble': (68, SCREEN_H - 24)}
UPGRADES = {'dwarf': (0, SCREEN_H - DWARF_SIZE), 'bubble': (68, 196)}

TALKS = [
    # A new game's first level.
    ('WELCOME', 'miner', ['WELCOME TO QUARRY.', 'BREAK SOME BRICKS AND', 'BUY SOME UPGRADES.'], LEVEL),
    # Each first clear of a level, before its menu.
    ('COIN', 'miner', ['CONGRATULATIONS!', "HERE'S A COIN. YOU CAN", 'SPEND IT IN THE DRY.'], LEVEL),
    # The upgrade screen, as level 2 unlocks.
    ('UNLOCK', 'miner', ['GREAT JOB! EACH LEVEL YOU', 'CLEAR UNLOCKS THE NEXT.', 'PICK ITS CART BELOW.'], UPGRADES),
    # The first time on the upgrade screen, after any other.
    ('UPGRADES', 'miner', ['THIS IS THE DRY. SPEND', 'YOUR NUGGETS HERE ON', 'UPGRADES THAT HELP YOU', 'CLEAR LEVELS.'], UPGRADES),
]

CLEAR, INK, PAPER, SHADE = range(4)
COLORS = [None, (14, 14, 18), (250, 246, 234), (206, 199, 184)]
KEY = {'.': CLEAR, '#': INK, 'o': PAPER, 's': SHADE}

# The bubble's corners and edges, a cell each, from its top left corner.
CORNER = ['....####',
          '..##oooo',
          '.#oooooo',
          '.#oooooo',
          '#ooooooo',
          '#ooooooo',
          '#ooooooo',
          '#ooooooo']
FOOT = ['#ooooooo',
        '#ooooooo',
        '#ooooooo',
        '#ooooooo',
        '.#oooooo',
        '.#ssoooo',
        '..##ssss',
        '....####']
TOP = ['########'] + ['oooooooo'] * 7
BOTTOM = ['oooooooo'] * 6 + ['ssssssss', '########']
SIDE = ['#ooooooo'] * 8
INSIDE = ['oooooooo'] * 8

# The tail, two cells across and two down: the column left of the bubble,
# and the bubble's left edge, open where the tail joins it.
TAIL = ['........#ooooooo',
        '........#ooooooo',
        '.......#oooooooo',
        '.......#oooooooo',
        '......#ooooooooo',
        '.....#oooooooooo',
        '.....#oooooooooo',
        '....#ooooooooooo',
        '...#oooooooooooo',
        '...#ooosssoooooo',
        '..#oss###ooooooo',
        '.#s##...#ooooooo',
        '.##.....#ooooooo',
        '##......#ooooooo',
        '........#ooooooo',
        '........#ooooooo']
TAIL_UP = 2  # rows of cells above the bubble's bottom edge


def mirror(cell):
    return [line[::-1] for line in cell]


def pixels(art):
    return [[KEY[c] for c in line] for line in art]


def close(a, b, d):
    return sum((x - y) ** 2 for x, y in zip(a, b)) < d * d


def portrait(name):
    """The dwarf as rows of colors, None clear, DWARF_SIZE square, his
    shoulders on the bottom row."""
    w, h, px = rgba(os.path.join(HERE, 'dwarves', name + '.png'))
    px = [[p[:3] for p in row] for row in px]
    frame = px[1][1]
    inside = [(x, y) for y in range(h) for x in range(w) if not close(px[y][x], frame, 30)]
    left, top = min(x for x, _ in inside), min(y for _, y in inside)
    right, bottom = max(x for x, _ in inside) + 1, max(y for _, y in inside) + 1
    img = [row[left:right] for row in px[top:bottom]]
    w, h = right - left, bottom - top
    edge = [(x, y) for y in range(h) for x in range(w) if x in (0, w - 1) or y in (0, h - 1)]
    ground = Counter(img[y][x] for x, y in edge).most_common(1)[0][0]
    # The background, from the edges in.
    todo = [(x, y) for x, y in edge if close(img[y][x], ground, 40)]
    clear = set(todo)
    while todo:
        x, y = todo.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in clear and close(img[ny][nx], ground, 40):
                clear.add((nx, ny))
                todo.append((nx, ny))
    img = [[None if (x, y) in clear else img[y][x] for x in range(w)] for y in range(h)]
    if w > DWARF_SIZE or h > DWARF_SIZE:
        raise SystemExit(f'talk.py: {name} is {w}x{h}, more than {DWARF_SIZE} square')
    pad = (DWARF_SIZE - w) // 2
    img = [[None] * pad + row + [None] * (DWARF_SIZE - w - pad) for row in img]
    return [[None] * DWARF_SIZE for _ in range(DWARF_SIZE - h)] + img


def band(img, top, bottom):
    """The pieces of the band of rows from top to bottom: as narrow as the
    dwarf is there, in widths of 4, no more than 64 each. Each is (x, y, w,
    h)."""
    cols = [x for x in range(DWARF_SIZE) if any(img[y][x] for y in range(top, bottom))]
    if not cols:
        return []
    left, right = min(cols), max(cols) + 1
    n = -(-(right - left) // 64)
    w = -(-(right - left) // (4 * n)) * 4
    left = max(0, min(left, DWARF_SIZE - n * w))
    return [(left + i * w, top, w, bottom - top) for i in range(n)]


def pieces(img):
    """The fewest bytes of pieces that cover the dwarf: a band over his
    head, and one under it from a row that is a multiple of 4."""
    best = None
    for split in range(DWARF_SIZE - 64, 65, 4):
        cut = band(img, 0, split) + band(img, split, DWARF_SIZE)
        size = sum(w * h // 2 for _, _, w, h in cut)
        if len(cut) <= DWARF_PIECES and (best is None or size < best[0]):
            best = size, cut
    return best[1]


def bubble(lines):
    """The bubble, as rows of the 4 colors, with its OK cells as paper, and
    the cell of the O. The OK ends the last line, at the right, a cell after
    it, with a cell clear all round it for the cursor."""
    cols = max(max(len(line) for line in lines), len(lines[-1]) + 4) + 2
    rows = 2 * len(lines) + 2
    if cols + 1 > BUBBLE_COLS or rows > BUBBLE_ROWS:
        raise SystemExit(f'talk.py: a bubble of {cols} by {rows} cells is too big')
    w, h = 8 * (cols + 1), 8 * rows
    img = [[CLEAR] * w for _ in range(h)]

    def put(art, col, row):
        for y, line in enumerate(art):
            for x, c in enumerate(line):
                img[row * 8 + y][col * 8 + x] = c

    for r in range(rows):
        for c in range(cols):
            top, bottom, left, right = r == 0, r == rows - 1, c == 0, c == cols - 1
            cell = (CORNER if top and left else mirror(CORNER) if top and right else
                    FOOT if bottom and left else mirror(FOOT) if bottom and right else
                    TOP if top else BOTTOM if bottom else SIDE if left else mirror(SIDE) if right else INSIDE)
            put(pixels(cell), c + 1, r)
    put(pixels(TAIL), 0, rows - 1 - TAIL_UP)
    for i, line in enumerate(lines):
        for j, ch in enumerate(line):
            glyph(img, 8 * (j + 2), 8 * (1 + 2 * i), ch)
    return img, (cols - 3, rows - 3)


def glyph(img, x0, y0, ch):
    """A letter of the panels' font in ink, a pixel in from the left of its
    cell, as on the menus."""
    if ch != ' ' and ch not in GLYPHS:
        raise SystemExit(f'talk.py: the font has no {ch!r}')
    for y, line in enumerate(GLYPHS.get(ch, [])):
        for x, c in enumerate(line):
            if c == '#':
                img[y0 + y][x0 + x + 1] = INK


def cells(img):
    """The image cut into tiles, each a tuple of its rows, and the map of
    them, tile 0 clear."""
    tiles = [tuple((CLEAR,) * 8 for _ in range(8))]
    grid = []
    for r in range(len(img) // 8):
        row = []
        for c in range(len(img[0]) // 8):
            t = tuple(tuple(img[r * 8 + y][c * 8:c * 8 + 8]) for y in range(8))
            if t not in tiles:
                tiles.append(t)
            row.append(tiles.index(t))
        grid.append(row)
    return tiles, grid


def color16(c):
    r, g, b = c or (0, 0, 0)
    return struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))


def build(dwarf, lines, where):
    """A talk_t, and its dwarf and bubble as RGBA rows to look at."""
    img = portrait(dwarf)
    counts = Counter(c for row in img for c in row if c)
    to = reduce(counts, 15)
    colors = sorted(set(to.values()), key=lambda c: 299 * c[0] + 587 * c[1] + 114 * c[2])
    index = {c: colors.index(to[c]) + 1 for c in to}
    cut = pieces(img)
    images = bytearray()
    heads = []
    for x, y, w, h in cut:
        heads.append(struct.pack('<hhHBB', x, y, len(images), (h // 4 - 1) << 4 | (w // 4 - 1), 0))
        for row in img[y:y + h]:
            line = [index.get(c, 0) for c in row[x:x + w]]
            images += bytes(line[i] << 4 | line[i + 1] for i in range(0, w, 2))
    if len(images) > DWARF_BYTES:
        raise SystemExit(f'talk.py: {dwarf} takes {len(images)} bytes, more than {DWARF_BYTES}')

    pic, (ok_col, ok_row) = bubble(lines)
    tiles, grid = cells(pic)
    ok = [row[:] for row in pic]
    for j, ch in enumerate('OK'):
        glyph(ok, 8 * (ok_col + j), 8 * ok_row, ch)
    ok_tiles, ok_grid = cells(ok)
    ok_cells = [ok_tiles[ok_grid[ok_row][ok_col + j]] for j in range(2)]
    for t in ok_cells:
        if t not in tiles:
            tiles.append(t)
    if len(tiles) > BUBBLE_TILES:
        raise SystemExit(f'talk.py: the bubble takes {len(tiles)} tiles, more than {BUBBLE_TILES}')

    dwarf_x, dwarf_y = where['dwarf']
    bubble_x, bubble_y = where['bubble'][0], where['bubble'][1] - len(grid) * 8
    data = struct.pack('<hhhhBBBBBB', dwarf_x, dwarf_y, bubble_x, bubble_y, len(grid), ok_col, ok_row,
                       tiles.index(ok_cells[0]), tiles.index(ok_cells[1]), len(cut))
    data += b''.join(heads) + bytes(8 * (DWARF_PIECES - len(cut)))
    data += b''.join(color16(c) for c in ([None] + colors + [None] * 15)[:16])
    data += bytes(images) + bytes(DWARF_BYTES - len(images))
    data += b''.join(color16(c) for c in COLORS)
    for t in tiles + [tiles[0]] * (BUBBLE_TILES - len(tiles)):
        for row in t:
            data += bytes([row[0] << 6 | row[1] << 4 | row[2] << 2 | row[3],
                           row[4] << 6 | row[5] << 4 | row[6] << 2 | row[7]])
    for r in range(BUBBLE_ROWS):
        row = grid[r] if r < len(grid) else []
        data += bytes(row + [0] * (BUBBLE_COLS - len(row)))
    if len(data) != TALK_BYTES:
        raise SystemExit(f'talk.py: a talk of {len(data)} bytes, not the {TALK_BYTES} of talk_t')

    shown = [[(*to[c], 255) if c else (0, 0, 0, 0) for c in row] for row in img]
    bubble_px = [[(*COLORS[c], 255) if c else (0, 0, 0, 0) for c in row] for row in ok]
    print(f'talk: {dwarf} in {len(colors)} colors, {len(cut)} pieces, {len(images)} bytes; '
          f'a bubble of {len(grid[0])} by {len(grid)} cells, {len(tiles)} tiles')
    return data, shown, bubble_px, cut


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('out_dir')
    parser.add_argument('header')
    parser.add_argument('--count', type=int, help='how many talks the build expects')
    parser.add_argument('--preview', help='also write the first talk, in place, to look at')
    parser.add_argument('--behind', help='a screenshot to put the preview on')
    args = parser.parse_args()
    if args.count is not None and args.count != len(TALKS):
        raise SystemExit(f'talk.py: there are {len(TALKS)} talks, not {args.count}; set QUARRY_TALKS')

    for n, (name, dwarf, lines, where) in enumerate(TALKS, 1):
        data, shown, bubble_px, _ = build(dwarf, lines, where)
        with open(os.path.join(args.out_dir, f'talk{n}.bin'), 'wb') as f:
            f.write(data)
        if args.preview and n == 1:
            if args.behind:
                w, h, back = rgba(args.behind)
            else:
                w, h, back = 320, 240, [[(20, 22, 28, 255)] * 320 for _ in range(240)]
            out = [[p[:3] for p in row] for row in back]
            for img, (x0, y0) in ((bubble_px, (where['bubble'][0], where['bubble'][1] - len(bubble_px))),
                                  (shown, where['dwarf'])):
                for y, row in enumerate(img):
                    for x, p in enumerate(row):
                        if p[3] and 0 <= x0 + x < w and 0 <= y0 + y < h:
                            out[y0 + y][x0 + x] = p[:3]
            write_png(args.preview, w, h, 2, [[v for c in row for v in c] for row in out])

    with open(args.header, 'w') as f:
        f.write('/* Made by art/talk.py. What the dwarves say, each ROM:talkN. */\n\n'
                '#ifndef TALKS_H\n#define TALKS_H\n\n')
        for n, (name, *_) in enumerate(TALKS, 1):
            f.write(f'#define TALK_{name} {n}\n')
        f.write(f'#define TALKS {len(TALKS)}\n\n#endif\n')


if __name__ == '__main__':
    main()
