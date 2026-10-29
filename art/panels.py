#!/usr/bin/env python3
"""Build the panels of the upgrade screen, as art/style/README.md describes them.

  panels.py out.bin out.h [--preview out.png]

The panels are an 8-bit tile layer of 8x8 tiles. Each frame is two cells
thick, drawn three pixels in from the edge of its cells, so there is a gap
between two panels side by side. The frames are put together here from the
cells of art/panel-frame.png, frame 1 of the style guide fitted to the
cells: its corners as they are, its plain steel and its bolts along each
edge as each panel's layout says, so panels of any height share them, and
hangers up to the rail. Its bottom half is its top half turned over.

The contents of a panel, its plate and the glyphs on it, come from
art/panel-font.png, in the order of FONT, then the short digits and the
pips, and then the plate's four rounded corners. They come twice, lit and
dim, so the panels to the sides can be dim. So does the inner ring of each
frame, which holds the edge of the display, its pixels inside frame 1's
black outline: dim, only they dim, so a dim display is dark right to the
frame. The inner ring's plain steel is one cell along each edge, to keep
it to few tiles; it hardly varies in frame 1. The outer ring comes once,
and stays lit.

out.bin is the palette, 256 colors as png2bin.py writes a palette row, then
256 tiles of 64 bytes, then the tile map of each panel's frame, one after
another, row by row, 20 cells across and 19 down, the top row for the
hangers, which the game copies into a slot of its map as the panel comes
near.
out.h gives the tile numbers and the height of each panel. Only the Python
standard library is used.
"""

import argparse
import os
import struct

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))

FONT = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\x10/%+-.:?'
PLATE = (56, 71, 87)  # the flat plate inside a frame
DIM = 0.42            # a dim panel's contents, of the lit colors
COLS, ROWS = 20, 19   # the cells of a panel, the top row for its hangers
PAD = 3               # the clear pixels outside a frame
BAND = 16             # a frame's depth, with PAD

# Each panel's frame: its rows, from its top edge, in steps of 2, a line of
# its text, and what is along each
# edge between its corners: across the top and the bottom, a character a
# cell for cells 4 to 15, and down the sides for rows 4 to rows - 5. A dot
# is plain steel, B b a pair of bolts, and H, along the top, a hanger, and
# start is where the panel's edges start in the runs of plain steel. The
# corners, with their clamps, are frame 1's own: four cells along each edge
# from each corner.
LAYOUTS = [
    dict(rows=18, start=0, top='H..Bb......H', bottom='..Bb....Bb..', left='..Bb..Bb..', right='Bb......Bb'),
    dict(rows=18, start=5, top='H......Bb..H', bottom='Bb........Bb', left='....Bb....', right='Bb......Bb'),
    dict(rows=16, start=2, top='H......Bb..H', bottom='....Bb......', left='Bb......', right='...Bb...'),
    dict(rows=16, start=4, top='H...Bb.....H', bottom='Bb......Bb..', left='...Bb...', right='Bb......'),
    dict(rows=14, start=7, top='H..........H', bottom='..Bb..Bb....', left='..Bb..', right='Bb....'),
]

# The cells of art/panel-frame.png that plain steel and bolts come from.
# Plain steel walks through frame 1's own plain cells in their order, each
# edge of each panel from a place of its own, so its grain doesn't repeat
# every cell, as if cloned.
PLAIN_COLS = (6, 7, 8, 9, 10, 11, 12, 13)
PLAIN_ROWS = (4, 7, 8, 9, 10, 13)  # 9, 10 and 13 are 8, 7 and 4 turned over
INNER_COL, INNER_ROW = 6, 7  # the inner ring's plain steel: the cells most like the others
HANGER_COL = 9
BOLT_COLS = (14, 15)
BOLT_ROWS = (5, 6)

# Frame 1's clamps, which stand a pixel proud of its edges: the pixels each
# spans along the top edge and down the sides, in its top half.
CLAMPS_ACROSS = ((16, 26), (133, 143))
CLAMPS_DOWN = ((17, 27),)

# Shades of steel, from art/panel-frame.png, for the hangers.
OUTLINE = (0, 0, 0)
SHINE = (185, 201, 206)
STEEL = (83, 89, 96)
DARK = (42, 47, 51)


def blank(w, h):
    return [[None] * w for _ in range(h)]


def source(frame):
    """Frame 1 made whole: its top half as it is, and its bottom half the top
    half turned over, since Retro Diffusion cut its bottom edge short."""
    half = len(frame) // 2
    top = [[p[:3] if p[3] else None for p in row] for row in frame[:half]]
    w = len(top[0])
    # Each clamp stands a pixel proud, out into the gap.
    for x0, x1 in CLAMPS_ACROSS:
        for x in range(x0, x1 + 1):
            top[PAD - 1][x] = OUTLINE
    for y0, y1 in CLAMPS_DOWN:
        for y in range(y0, y1 + 1):
            top[y][PAD - 1] = top[y][w - PAD] = OUTLINE
    return top + top[::-1]


def cell(img, cx, cy):
    return [row[cx * 8:cx * 8 + 8] for row in img[cy * 8:cy * 8 + 8]]


def display(src):
    """Frame 1's display, what is inside its black outline, found from the
    middle out: True there, None elsewhere, to build frames from as src."""
    w, h = len(src[0]), len(src)
    out, todo = blank(w, h), [(w // 2, h // 2)]
    while todo:
        x, y = todo.pop()
        if not (0 <= x < w and 0 <= y < h) or out[y][x] or src[y][x] in (None, OUTLINE):
            continue
        out[y][x] = True
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    if out[PAD][PAD]:
        raise SystemExit('panels: the display of art/panel-frame.png leaks past its outline')
    return out


def inner(r, c, rows):
    """Whether cell c of body row r is in the inner ring of a frame."""
    return r in (1, rows - 2) and 1 <= c <= COLS - 2 or c in (1, COLS - 2) and 1 <= r <= rows - 2


def frame_image(layout, src):
    """A panel's frame, with its hangers' row on top, as rows of colors;
    None outside it and on the plate."""
    rows = layout['rows']
    src_rows = len(src) // 8
    img = blank(COLS * 8, (rows + 1) * 8)

    def src_row(r, along, start, ring):
        """The source row of body row r, down a side, in the inner ring or not."""
        if r < 4:
            return r
        if r >= rows - 4:
            return src_rows - (rows - r)
        c = along[r - 4]
        if c == '.':
            return INNER_ROW if ring else PLAIN_ROWS[(r - 4 + start) % len(PLAIN_ROWS)]
        return {'B': BOLT_ROWS[0], 'b': BOLT_ROWS[1]}[c]

    def src_col(c, along, start, ring):
        if c < 4 or c >= COLS - 4:
            return c
        ch = along[c - 4]
        if ch == '.':
            return INNER_COL if ring else PLAIN_COLS[(c - 4 + start) % len(PLAIN_COLS)]
        return {'H': HANGER_COL, 'B': BOLT_COLS[0], 'b': BOLT_COLS[1]}[ch]

    # Where each edge starts in its run of plain cells.
    starts = {edge: (layout['start'] + 3 * i) for i, edge in enumerate(('top', 'bottom', 'left', 'right'))}

    for r in range(rows):
        for c in range(COLS):
            top, bottom = r < 2, r >= rows - 2
            side = c < 2 or c >= COLS - 2
            if top or bottom:
                edge = 'top' if top else 'bottom'
                sr = r if top else src_rows - (rows - r)
                sc = src_col(c, layout[edge], starts[edge], inner(r, c, rows))
            elif side:
                edge = 'left' if c < 2 else 'right'
                sr = src_row(r, layout[edge], starts[edge], inner(r, c, rows))
                sc = c
            elif (c in (2, COLS - 3)) and r in (2, rows - 3):
                sr, sc = (2 if r == 2 else src_rows - 3), c  # the plate's rounded corners
            else:
                continue
            block = cell(src, sc, sr)
            for y in range(8):
                for x in range(8):
                    img[8 + r * 8 + y][c * 8 + x] = block[y][x]
    # The hangers: bars up from the top edge, through the gap, to the rail.
    for i, ch in enumerate(layout['top']):
        if ch == 'H':
            x0 = (4 + i) * 8
            for y in range(0, 8 + PAD + 2):
                for dx, color in ((2, OUTLINE), (3, SHINE), (4, STEEL), (5, DARK), (6, OUTLINE)):
                    img[y][x0 + dx] = color
    return img


def tiles_of(img):
    """8x8 cells, row by row, each a tuple of colors."""
    out = []
    for ty in range(len(img) // 8):
        row = []
        for tx in range(len(img[0]) // 8):
            row.append(tuple(img[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8)))
        out.append(row)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write every panel, lit, as a PNG')
    args = parser.parse_args()

    _, _, frame = rgba(os.path.join(HERE, 'panel-frame.png'))
    src = source(frame)
    fw, fh, font = rgba(os.path.join(HERE, 'panel-font.png'))
    font = [[p[:3] for p in row] for row in font]
    content = [tuple(font[y][i * 8 + x] for y in range(8) for x in range(8)) for i in range(fw // 8)]
    glyphs = len(FONT) + 10 + 2
    if len(content) != glyphs:
        raise SystemExit(f'panels: art/panel-font.png has {len(content)} cells, not {glyphs}')
    # The plate's rounded corners are contents too, so they dim with it.
    src_rows = len(src) // 8
    for cx, cy in ((2, 2), (COLS - 3, 2), (2, src_rows - 3), (COLS - 3, src_rows - 3)):
        content.append(tuple(c for row in cell(src, cx, cy) for c in row))
    count = len(content)
    darker = lambda c: tuple(round(v * DIM) for v in c)

    images = [frame_image(layout, src) for layout in LAYOUTS]
    shown = display(src)
    displays = [tiles_of(frame_image(layout, shown)) for layout in LAYOUTS]
    rings, ring_displays, frames, maps = [], [], [], []
    for layout, img, shows in zip(LAYOUTS, images, displays):
        grid = []
        for ty, row in enumerate(tiles_of(img)):
            line = []
            for tx, t in enumerate(row):
                inside = 2 <= tx < COLS - 2 and 2 <= ty - 1 < layout['rows'] - 2
                if inside and all(c is None for c in t):
                    line.append('plate')
                elif all(c is None for c in t):
                    line.append('clear')
                elif t in content:
                    line.append(('content', content.index(t)))
                elif ty and inner(ty - 1, tx, layout['rows']):
                    if t not in rings:
                        rings.append(t)
                        ring_displays.append(shows[ty][tx])
                    line.append(('ring', rings.index(t)))
                else:
                    if t not in frames:
                        frames.append(t)
                    line.append(frames.index(t))
            grid.append(line)
        maps.append(grid)

    # Tile 0 is clear, then the contents and the inner rings lit, then both
    # dim, then the outer rings. The contents dim all over, the inner rings
    # only in their display.
    lit = content + rings
    dim = [tuple(darker(c) for c in t) for t in content] + \
          [tuple(darker(c) if d else c for c, d in zip(t, ds)) for t, ds in zip(rings, ring_displays)]
    tiles = [tuple([None] * 64)] + lit + dim + frames
    if len(tiles) > 256:
        raise SystemExit(f'panels: {len(tiles)} tiles, past 256: {len(rings)} inner ring tiles, twice, '
                         f'and {len(frames)} outer')
    colors = sorted({c for t in tiles for c in t if c is not None})
    if len(colors) > 255:
        raise SystemExit(f'panels: {len(colors)} colors, past 255')
    index = {c: i + 1 for i, c in enumerate(colors)}
    frame_first = 1 + 2 * len(lit)

    data = bytearray()
    palette = [(0, 0, 0, 0)] + [c + (255,) for c in colors] + [(0, 0, 0, 0)] * (255 - len(colors))
    for r, g, b, a in palette:
        data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if a else 0))
    for t in tiles + [tuple([None] * 64)] * (256 - len(tiles)):
        data += bytes(index[c] if c is not None else 0 for c in t)
    for grid in maps:
        for row in range(ROWS):
            for entry in (grid[row] if row < len(grid) else ['clear'] * COLS):
                data.append(0 if entry == 'clear' else 1 if entry == 'plate' else
                            1 + entry[1] if isinstance(entry, tuple) and entry[0] == 'content' else
                            1 + count + entry[1] if isinstance(entry, tuple) else frame_first + entry)
    with open(args.output, 'wb') as f:
        f.write(data)

    font_c = ''.join('\\x10' if c == '\x10' else c for c in FONT)
    # The middle of each hanger's bar, from a panel's left, which the rail's
    # trolleys ride over. Every panel hangs from the same places.
    hangers = {tuple((4 + i) * 8 + 4 for i, ch in enumerate(layout['top']) if ch == 'H') for layout in LAYOUTS}
    if len(hangers) != 1:
        raise SystemExit('panels: the panels hang from different places, and their trolleys would not match')
    hangers = hangers.pop()
    with open(args.header, 'w') as f:
        f.write('/* Made by art/panels.py. The tiles of the upgrade screen\'s panels. */\n\n'
                '#ifndef PANELS_H\n#define PANELS_H\n\n'
                f'#define PANEL_FONT "{font_c}"\n'
                '#define PANEL_TILE_GLYPH 1 /* the plate, then each glyph of PANEL_FONT */\n'
                f'#define PANEL_TILE_SHORT {1 + len(FONT)} /* digits for a cost not yet paid */\n'
                f'#define PANEL_TILE_PIP_ON {1 + len(FONT) + 10}\n'
                f'#define PANEL_TILE_PIP_OFF {2 + len(FONT) + 10}\n'
                f'#define PANEL_TILE_DIM {len(lit)} /* add to a lit tile of the contents or an inner ring */\n'
                f'#define PANEL_TILE_FRAMES {frame_first} /* the first tile of the outer rings, which stay lit */\n'
                f'#define PANEL_TILES {len(tiles)}\n'
                f'#define PANEL_LAYOUTS {len(LAYOUTS)}\n'
                f'#define PANEL_HEIGHTS {{{", ".join(str(l["rows"]) for l in LAYOUTS)}}}\n'
                f'#define PANEL_HANGERS {len(hangers)}\n'
                f'#define PANEL_HANGER_X {{{", ".join(str(x) for x in hangers)}}} /* the middle of each, from a panel\'s left */\n\n'
                '#endif\n')

    print(f'panels: {2 * count} tiles of contents, {2 * len(rings)} of inner rings, {len(frames)} of outer, '
          f'{len(tiles)} of 256; {len(colors)} colors')
    if args.preview:
        out = blank(COLS * 8 * len(images) + 4 * (len(images) - 1), ROWS * 8)
        for i, img in enumerate(images):
            for y, row in enumerate(img):
                for x, c in enumerate(row):
                    out[y][i * (COLS * 8 + 4) + x] = c if c is not None else (PLATE if 16 <= x < 144 and 24 <= y < len(img) - 16 else None)
        rows = [[v for c in row for v in ((c + (255,)) if c else (40, 10, 60, 255))] for row in out]
        write_png(args.preview, len(out[0]), len(out), 6, rows)


if __name__ == '__main__':
    main()
