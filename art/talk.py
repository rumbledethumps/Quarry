#!/usr/bin/env python3
"""Build the dwarves and what they say, as art/style/README.md describes them.

  talk.py out_dir header [--preview out.png --behind screen.png]

A dwarf is a portrait Retro Diffusion drew, art/dwarves/name.png: his head
and shoulders on a plain background, wider than he is, or in a frame of
its own, which is cut off. The background is cleared from the edges in,
and he is cut to DWARF_SIZE square: at the foot, and if he is wider, on
the side against the edge of the screen, so the arm toward his bubble
stays whole. His colors are brought down to 15. He is a few 4-bit
sprites, a band across his head and a band across his shoulders, each as
narrow as he is there, so the clear corners take no room. Each dwarf has
a portrait for each side of the screen, facing his bubble.

His speech bubble is a map of 2-bit tiles: clear, ink, paper and a shade
of paper along its foot. Its corners, edges and tail are drawn by hand
below, the tail reaching out of its side toward his mouth, and its lines
are the panels' font in ink, a row of cells between them. The last line
ends with an OK, at the right, which the game puts in once the bubble has
come in, but on the title, where he stays while the player picks from the
menu above him. The bubble is cut into tiles, the same ones shared.

TALKS lists what the dwarves say: each one's name, the dwarf, his side,
where his bubbles go, and his bubbles, one after another, each its lines,
or a place of its own and its lines. Each
dwarf on each side a talk uses is a dwarf_t of src/xram.h in
out_dir/dwarves.bin, and each bubble a bubble_t in out_dir/bubbles.bin,
one after another from 1. The header gives the talks' numbers as
TALK_name, TALK_STAYS a bit for each that stays, and TALK_TABLE each
one's dwarf, first bubble and how many, TALK_SEEN each one's bit of the
save's talks seen, or 0, and TALK_SEEN_name the bit of each with one.
Only the Python standard library is used.
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
DWARF_ASSET_BYTES = 6 + 8 * DWARF_PIECES + 32 + DWARF_BYTES
BUBBLE_ASSET_BYTES = 10 + 8 + 16 * BUBBLE_TILES + BUBBLE_ROWS * BUBBLE_COLS
SCREEN_W, SCREEN_H = 320, 240

# The dwarves, and the portrait of each for each side of the screen, in
# art/dwarves/, and whether to turn it round: on the left he faces right,
# toward his bubble, and on the right, left, lit from the upper left either
# way. Until each is drawn, the miner stands in for him, turned round on the
# right, as he does for the friendly dwarf on the right.
LEFT, RIGHT = 'left', 'right'
DWARVES = {
    'FRIENDLY': {LEFT: ('friendly-red-left', False), RIGHT: ('friendly-red-right', False)},
    'FOREMAN': {LEFT: ('miner', False), RIGHT: ('miner', True)},
    'COMMITTEEMAN': {LEFT: ('miner', False), RIGHT: ('miner', True)},
}

# The talks shown only once, and each one's bit of the save's talks seen.
# The others need none: the greeting is for a game with no save, and a
# coin's for a level's first clear, which the save keeps. A bit keeps its
# meaning for good, so a save is still good as talks, levels and their
# coins are added: the foreman's was the first level's welcome, and the
# dry's the first word on the upgrade screen. Bits 1 and 4 were never set,
# and are free.
SEEN = {'FOREMAN': 0, 'UNLOCK': 2, 'DRY': 3}

# Where they stand: he is in a lower corner, and his bubble beside him, its
# tail under his beard. The bubble is placed by its foot, so the tail is as
# high whatever its lines, and BUBBLE_GAP px from the edge of the screen on
# his side. On the upgrade screen its foot is just over the carts, so they
# show, or for what he says of the panels, low over the carts, so the
# panels show. On the title he stays, with no OK, and his bubble is a row
# shorter, clear of the panel over it.
BUBBLE_GAP = 68
LEVEL = {'foot': SCREEN_H - 24}
DRY = {'foot': 196}
DRY_LOW = dict(LEVEL)
TITLE = dict(LEVEL, stays=True)

# What the dwarves say: the talks but the coins', each with a key of its
# own in a debug build, then the coins', from COIN1, one for each level, and
# COIN1's for a level past them.
TALKS = [
    # The title, with no save.
    ('GREENHORN', 'FRIENDLY', LEFT, TITLE,
     [['WELCOME, GREENHORN.', "HEAD ON IN WHEN YOU'RE", 'READY TO BREAK SOME ROCK.']]),
    # The first time on the upgrade screen, after any other: the panels, with
    # his bubble over the carts, then the carts, with it over the panels.
    ('DRY', 'FRIENDLY', LEFT, DRY,
     [(DRY_LOW, ['THIS IS THE DRY. USE THE', 'PANELS TO UPGRADE YOUR', 'MACHINES.']),
      ['SELECT A CART TO BEGIN', 'MINING THAT LEVEL.']]),
    # A new game's first level.
    ('FOREMAN', 'FOREMAN', LEFT, LEVEL,
     [['OVER HERE, GREENHORN.', 'PAY ATTENTION BECAUSE I', "WON'T REPEAT MYSELF."],
      ['PUSH THE BUTTON TO LAUNCH', 'A WRECKING BALL THEN KEEP', 'IT FROM FALLING.'],
      ["THAT'S ALL.", 'NOW GET TO WORK.']]),
    # The upgrade screen, as level 2 unlocks.
    ('UNLOCK', 'COMMITTEEMAN', RIGHT, DRY,
     [['EVERY TIME YOU CLEAR A', 'LEVEL THE NEXT BECOMES', 'AVAILABLE.']]),
    # The first clear of each level, before its menu, with its coin.
    ('COIN1', 'COMMITTEEMAN', RIGHT, LEVEL,
     [['NICE WORK!', "HERE'S A UNION COIN."]]),
    ('COIN2', 'COMMITTEEMAN', RIGHT, LEVEL,
     [["AREN'T YOU QUITE THE", "NIPPER. YOU'VE EARNED", 'ANOTHER COIN.']]),
    ('COIN3', 'COMMITTEEMAN', RIGHT, LEVEL,
     [["DIDN'T ANYONE EXPLAIN", 'THE COINS TO YOU?']]),
    ('COIN4', 'COMMITTEEMAN', RIGHT, LEVEL,
     [['KEEP SAVING THESE', 'COINS FOR POWERFUL', 'UPGRADES.']]),
    ('COIN5', 'COMMITTEEMAN', RIGHT, LEVEL,
     [["YOU'VE EARNED 5 COINS AND", 'COMPLETED THE GAME.'],
      ["SORRY, THE COINS DON'T", 'DO ANYTHING YET.'],
      ['THANK YOU FOR PLAYING MY', 'GAME JAM ENTRY.']]),
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


def green(c):
    """Whether a color is a green, as of the background."""
    return c[1] > c[0] + 50 and c[1] > c[2] + 50


def portrait(name, turned, side):
    """The dwarf as rows of colors, None clear, DWARF_SIZE square, his
    shoulders on the bottom row, turned round if asked, for the side of the
    screen he stands on."""
    w, h, px = rgba(os.path.join(HERE, 'dwarves', name + '.png'))
    px = [[p[:3] for p in (row[::-1] if turned else row)] for row in px]
    # A frame of its own goes: it has the corner's color, and he is inside
    # it, clear of every edge.
    frame = px[0][0]
    inside = [(x, y) for y in range(h) for x in range(w) if not close(px[y][x], frame, 30)]
    left, top = min(x for x, _ in inside), min(y for _, y in inside)
    right, bottom = max(x for x, _ in inside) + 1, max(y for _, y in inside) + 1
    if left and top and right < w and bottom < h:
        px = [row[left:right] for row in px[top:bottom]]
        w, h = right - left, bottom - top
    edge = [(x, y) for y in range(h) for x in range(w) if x in (0, w - 1) or y in (0, h - 1)]
    ground = Counter(px[y][x] for x, y in edge).most_common(1)[0][0]
    # The background, from the edges in, and any other green of it left in
    # his outline, as he is drawn on plain green.
    todo = [(x, y) for x, y in edge if close(px[y][x], ground, 40)]
    clear = set(todo)
    while todo:
        x, y = todo.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in clear and close(px[ny][nx], ground, 40):
                clear.add((nx, ny))
                todo.append((nx, ny))
    clear |= {(x, y) for y in range(h) for x in range(w) if green(px[y][x])}
    he = [(x, y) for y in range(h) for x in range(w) if (x, y) not in clear]
    left, top = min(x for x, _ in he), min(y for _, y in he)
    right, bottom = max(x for x, _ in he) + 1, max(y for _, y in he) + 1
    # Cut to size: at the foot, and on the side against the screen's edge.
    bottom = min(bottom, top + DWARF_SIZE)
    if right - left > DWARF_SIZE:
        if side == LEFT:
            left = right - DWARF_SIZE
        else:
            right = left + DWARF_SIZE
    img = [[None if (x, y) in clear else px[y][x] for x in range(left, right)] for y in range(top, bottom)]
    w, h = right - left, bottom - top
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


def bubble(lines, ok, side):
    """The bubble, as rows of the 4 colors, with its OK cells as paper, and
    the cell of the O. Its tail is on the side of the dwarf: on the left
    for one on the left, the tail's column first, or on the right. The OK
    ends the last line, at the right, a cell after it, with a cell clear
    all round it for the cursor. Without one, the cell is 0, 0, which is a
    corner of the picture, and there is no row under the last line."""
    cols = max(max(len(line) for line in lines), len(lines[-1]) + 4 if ok else 0) + 2
    rows = 2 * len(lines) + (2 if ok else 1)
    if cols + 1 > BUBBLE_COLS or rows > BUBBLE_ROWS:
        raise SystemExit(f'talk.py: a bubble of {cols} by {rows} cells is too big')
    w, h = 8 * (cols + 1), 8 * rows
    img = [[CLEAR] * w for _ in range(h)]
    at = 1 if side == LEFT else 0  # the picture's column of the bubble's left edge

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
            put(pixels(cell), at + c, r)
    if side == LEFT:
        put(pixels(TAIL), 0, rows - 1 - TAIL_UP)
    else:
        put(pixels(mirror(TAIL)), cols - 1, rows - 1 - TAIL_UP)
    for i, line in enumerate(lines):
        for j, ch in enumerate(line):
            glyph(img, 8 * (at + 1 + j), 8 * (1 + 2 * i), ch)
    return img, (at + cols - 4, rows - 3) if ok else (0, 0)


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


def dwarf_asset(dwarf, side):
    """A dwarf_t, and the dwarf as RGBA rows to look at."""
    img = portrait(*DWARVES[dwarf][side], side)
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
    x = 0 if side == LEFT else SCREEN_W - DWARF_SIZE
    data = struct.pack('<hhBB', x, SCREEN_H - DWARF_SIZE, len(cut), 0)
    data += b''.join(heads) + bytes(8 * (DWARF_PIECES - len(cut)))
    data += b''.join(color16(c) for c in ([None] + colors + [None] * 15)[:16])
    data += bytes(images) + bytes(DWARF_BYTES - len(images))
    if len(data) != DWARF_ASSET_BYTES:
        raise SystemExit(f'talk.py: a dwarf of {len(data)} bytes, not the {DWARF_ASSET_BYTES} of dwarf_t')
    print(f'talk: {dwarf} on the {side} in {len(colors)} colors, {len(cut)} pieces, {len(images)} bytes')
    shown = [[(*to[c], 255) if c else (0, 0, 0, 0) for c in row] for row in img]
    return data, shown, (x, SCREEN_H - DWARF_SIZE)


def bubble_asset(lines, side, where):
    """A bubble_t, and the bubble as RGBA rows to look at, with where it
    goes."""
    stays = where.get('stays', False)
    pic, (ok_col, ok_row) = bubble(lines, not stays, side)
    tiles, grid = cells(pic)
    ok = [row[:] for row in pic]
    for j, ch in enumerate('' if stays else 'OK'):
        glyph(ok, 8 * (ok_col + j), 8 * ok_row, ch)
    ok_tiles, ok_grid = cells(ok)
    ok_cells = [ok_tiles[ok_grid[ok_row][ok_col + j]] for j in range(2)]
    for t in ok_cells:
        if t not in tiles:
            tiles.append(t)
    if len(tiles) > BUBBLE_TILES:
        raise SystemExit(f'talk.py: the bubble takes {len(tiles)} tiles, more than {BUBBLE_TILES}')

    cols = len(grid[0])
    x = BUBBLE_GAP if side == LEFT else SCREEN_W - BUBBLE_GAP - 8 * cols
    y = where['foot'] - len(grid) * 8
    data = struct.pack('<hhBBBBBB', x, y, len(grid), cols, ok_col, ok_row,
                       tiles.index(ok_cells[0]), tiles.index(ok_cells[1]))
    data += b''.join(color16(c) for c in COLORS)
    for t in tiles + [tiles[0]] * (BUBBLE_TILES - len(tiles)):
        for row in t:
            data += bytes([row[0] << 6 | row[1] << 4 | row[2] << 2 | row[3],
                           row[4] << 6 | row[5] << 4 | row[6] << 2 | row[7]])
    for r in range(BUBBLE_ROWS):
        row = grid[r] if r < len(grid) else []
        data += bytes(row + [0] * (BUBBLE_COLS - len(row)))
    if len(data) != BUBBLE_ASSET_BYTES:
        raise SystemExit(f'talk.py: a bubble of {len(data)} bytes, not the {BUBBLE_ASSET_BYTES} of bubble_t')
    print(f'talk: a bubble of {cols} by {len(grid)} cells, {len(tiles)} tiles')
    shown = [[(*COLORS[c], 255) if c else (0, 0, 0, 0) for c in row] for row in ok]
    return data, shown, (x, y)


def seen(name):
    """The talk's bit of the save's talks seen, or 0."""
    return 1 << SEEN[name] if name in SEEN else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('out_dir')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write the first talk, in place, to look at')
    parser.add_argument('--behind', help='a screenshot to put the preview on')
    args = parser.parse_args()

    dwarves, bubbles, table = [], [], []
    for name, dwarf, side, where, said in TALKS:
        if where.get('stays') and len(said) > 1:
            raise SystemExit(f'talk.py: {name} stays, with no OK, so it has one bubble')
        if (dwarf, side) not in dwarves:
            dwarves.append((dwarf, side))
        table.append((dwarves.index((dwarf, side)) + 1, len(bubbles) + 1, len(said)))
        for lines in said:
            at, lines = lines if isinstance(lines, tuple) else (where, lines)
            bubbles.append((lines, side, at))
    built = [dwarf_asset(*d) for d in dwarves]
    with open(os.path.join(args.out_dir, 'dwarves.bin'), 'wb') as f:
        f.write(b''.join(data for data, *_ in built))
    said = [bubble_asset(*b) for b in bubbles]
    with open(os.path.join(args.out_dir, 'bubbles.bin'), 'wb') as f:
        f.write(b''.join(data for data, *_ in said))

    if args.preview:
        if args.behind:
            w, h, back = rgba(args.behind)
        else:
            w, h, back = 320, 240, [[(20, 22, 28, 255)] * 320 for _ in range(240)]
        out = [[p[:3] for p in row] for row in back]
        for _, img, (x0, y0) in (said[0], built[0]):
            for y, row in enumerate(img):
                for x, p in enumerate(row):
                    if p[3] and 0 <= x0 + x < w and 0 <= y0 + y < h:
                        out[y0 + y][x0 + x] = p[:3]
        write_png(args.preview, w, h, 2, [[v for c in row for v in c] for row in out])

    coins = [name for name, *_ in TALKS if name.startswith('COIN')]
    if coins != [f'COIN{n}' for n in range(1, len(coins) + 1)] or TALKS[-len(coins)][0] != 'COIN1':
        raise SystemExit('talk.py: the coins\' talks are last, COIN1 and on')
    with open(args.header, 'w') as f:
        f.write('/* Made by art/talk.py. What the dwarves say: each talk a dwarf of\n'
                '   ROM:dwarves and bubbles of ROM:bubbles, from 1. */\n\n'
                '#ifndef TALKS_H\n#define TALKS_H\n\n')
        for n, (name, *_) in enumerate(TALKS, 1):
            f.write(f'#define TALK_{name} {n}\n')
        stays = sum(1 << n for n, talk in enumerate(TALKS) if talk[3].get('stays'))
        f.write(f'#define TALKS {len(TALKS)}\n'
                f'#define TALK_COINS {len(coins)} /* from TALK_COIN1, the coin of each level */\n'
                f'#define TALK_STAYS 0x{stays:04X} /* a bit for each talk that stays, with no OK, from TALK 1 */\n'
                f'#define TALK_DWARVES {len(dwarves)}\n'
                f'#define TALK_BUBBLES {len(bubbles)}\n'
                '/* For each talk from 1: its dwarf, its first bubble, and how many. */\n'
                '#define TALK_TABLE {' + ', '.join('{%d, %d, %d}' % t for t in table) + '}\n'
                '/* For each talk from 1: its bit of talks_seen, if it is shown once, or 0. */\n'
                '#define TALK_SEEN {' + ', '.join(f'0x{seen(name):02X}' for name, *_ in TALKS) + '}\n')
        for name in SEEN:
            f.write(f'#define TALK_SEEN_{name} 0x{seen(name):02X}\n')
        f.write('\n#endif\n')


if __name__ == '__main__':
    main()
