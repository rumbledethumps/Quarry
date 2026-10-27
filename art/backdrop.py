#!/usr/bin/env python3
"""Build the upgrade screen's backdrop, as art/style/README.md describes it.

  backdrop.py out.bin out.h [--preview out.png]

The backdrop is art/backdrop.png, a workshop wall from Retro Diffusion,
320x240, on plane 0 behind everything, in three bands of 16x16 tiles, each
with a palette of its own: the top, the ceiling's truss, in 15 colors; the
middle, plain wall behind the panels, in 4 grays at 2 bits a pixel; and the
bottom, the machinery along the floor, in 15 colors, with the red and the
yellow. Everything is darkened, and a little cool, so the steel of the
panels and the carts stands out in front of it.

The middle's grays are the nearest of the top's and the bottom's colors to
what it needs, so the bands join without a seam. The cells of the middle
that are always behind the panel in the middle, when the panels are still,
are plain wall, one tile: they only show in the gaps between panels as
they slide. That is worked out from PANEL_Y in src/xram.h and the panels'
heights in art/panels.py.

The two cogs at the left of the floor turn, all the time: they are drawn
here, over the art's own, and GEAR_FRAMES frames of them, a tooth apart in
all, are sprites over the bottom band. Each frame is the pixels that
change, and clear where nothing does. The box and the plate in front of
the cogs stay in front.

The steam drawn in art/backdrop.png comes and goes: it is painted out, and
STEAM_FRAMES sprites of it, from its own pixels, grow from the vent, then
thin out and go.

out.bin is each band in turn, top to bottom: its palette, 16 colors for a
4-bit band or 4 for the 2-bit one, as png2bin.py writes a palette row, its
tiles, the left pixel of each byte in its high bits, and its map, a byte a
cell, row by row. Then the sprites, 4-bit in the bottom band's palette:
each frame of the cogs, in two sprites, top and bottom, then each frame of
the steam. out.h gives the sizes and the places. Only the Python standard
library is used.
"""

import argparse
import math
import os
import re
import struct
from collections import Counter

from curtain import reduce
from panels import COLS as PANEL_COLS, LAYOUTS, PAD
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
DARKEN = (0.58, 0.6, 0.66)  # red, green and blue, darker and a little cool
W, H, TILE = 320, 240, 16
COLS = W // TILE
# The bands: the scanline each starts at, its bits a pixel, and its colors.
BANDS = ((0, 4, 15), (32, 2, 4), (128, 4, 15))
# The steam drawn in the art, painted out: a box around it, and the
# lightness past which a pixel in it is steam.
STEAM_BOX = (80, 180, 100, 208)
STEAM_LUMA = 110
STEAM_FRAMES = 5  # growing, whole, then thinning
# The cogs: the middle, the radius to the tips of the teeth, the teeth, and
# how they look inside: spokes, or a disc with rings. They mesh, so they
# turn opposite ways.
GEARS = (dict(x=0, y=158, radius=22, teeth=11, spokes=6, turn=1),
         dict(x=16, y=199, radius=21, teeth=10, spokes=0, turn=-1))
GEAR_FRAMES = 4
FRONT = ((23, 130, 52, 169), (0, 204, 48, 224))  # the box and the plate in front of the cogs
# The cogs' colors, from the art: outline, the dark behind them and in
# their holes, a shade, the steel, and its highlight.
OUTLINE, BEHIND, SHADE, STEEL, LIGHT = (8, 8, 12), (23, 23, 28), (49, 51, 55), (73, 79, 81), (110, 118, 120)


def define(name):
    """A number #defined in src/xram.h."""
    with open(os.path.join(HERE, '..', 'src', 'xram.h')) as f:
        return int(re.search(rf'#define {name} (\d+)', f.read()).group(1))


def luma(c):
    return (299 * c[0] + 587 * c[1] + 114 * c[2]) // 1000


def paint_out_steam(art):
    """Each pixel of steam takes the color of the nearest pixel left of it
    that isn't steam."""
    x0, y0, x1, y1 = STEAM_BOX
    for y in range(y0, y1):
        for x in range(x0, x1):
            if luma(art[y][x]) > STEAM_LUMA:
                left = x - 1
                while left > 0 and luma(art[y][left]) > STEAM_LUMA:
                    left -= 1
                art[y][x] = art[y][left]


def gear_pixels(gear, angle):
    """A cog turned angle radians: {(x, y): color} over its disc and a
    little past it, BEHIND where it has a gap."""
    cx, cy, r = gear['x'] + 0.5, gear['y'] + 0.5, gear['radius']
    root, rim, hub = r - 5, r - 8, 4.5
    out = {}

    def solid(x, y):
        dx, dy = x + 0.5 - cx, y + 0.5 - cy
        d = math.hypot(dx, dy)
        if d >= r:
            return False
        if d < root:
            return True
        t = ((math.atan2(dy, dx) - angle) * gear['teeth'] / (2 * math.pi)) % 1
        return t < 0.55 - 0.15 * (d - root) / (r - root)

    def hole(x, y):
        """Between the spokes, or the groove of a disc."""
        dx, dy = x + 0.5 - cx, y + 0.5 - cy
        d = math.hypot(dx, dy)
        if gear['spokes']:
            if not hub + 1 < d < rim:
                return False
            a = (math.atan2(dy, dx) - angle) * gear['spokes'] / (2 * math.pi)
            return abs(a - round(a)) * 2 * math.pi / gear['spokes'] * d > 1.6
        return rim - 1 <= d < rim + 1 or hub <= d < hub + 1

    for y in range(int(cy - r - 2), int(cy + r + 3)):
        for x in range(int(cx - r - 2), int(cx + r + 3)):
            if not solid(x, y):
                if math.hypot(x + 0.5 - cx, y + 0.5 - cy) < r + 2:
                    out[x, y] = BEHIND
                continue
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            edge = not all(solid(x + a, y + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                out[x, y] = OUTLINE
            elif hole(x, y):
                out[x, y] = BEHIND
            elif not solid(x - 1, y - 1) or (math.hypot(dx, dy) < hub and dx + dy < -1):
                out[x, y] = LIGHT  # lit from the upper left
            elif not solid(x + 1, y + 1) or math.hypot(dx, dy) >= root:
                out[x, y] = SHADE
            else:
                out[x, y] = STEEL
    return out


def gears_frame(art, f):
    """The art with the cogs drawn over it, frame f, a tooth in
    GEAR_FRAMES, the box and the plate kept in front."""
    out = [row[:] for row in art]
    for gear in GEARS:
        angle = gear['turn'] * f * 2 * math.pi / gear['teeth'] / GEAR_FRAMES
        for (x, y), c in gear_pixels(gear, angle).items():
            if 0 <= x < W and 0 <= y < H and not any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in FRONT):
                out[y][x] = c
    return out


def steam_frames(art):
    """The steam's pixels, painted out of art, as STEAM_FRAMES images of the
    steam box: growing from the vent at its foot, then thinning out, None
    where it is clear."""
    x0, y0, x1, y1 = STEAM_BOX
    puff = {(x, y): art[y][x] for y in range(y0, y1) for x in range(x0, x1) if luma(art[y][x]) > STEAM_LUMA}
    vent = min(puff, key=lambda p: (-p[1], p[0]))
    reach = max(math.hypot(x - vent[0], y - vent[1]) for x, y in puff)
    frames = []
    for f in range(STEAM_FRAMES):
        grow = min(1, (f + 1) / 3)
        thin = max(0, f - 2)  # 1 and 2: it leaves the vent, rises and thins
        img = [[None] * (x1 - x0) for _ in range(y1 - y0)]
        for (x, y), c in puff.items():
            d = math.hypot(x - vent[0], y - vent[1]) / reach
            if d > grow or d < 0.3 * thin:
                continue
            if thin == 1 and (x + y) % 2 or thin == 2 and (x % 2 or y % 2):
                continue
            if y - y0 - thin >= 0:
                img[y - y0 - thin][x - x0] = c
        frames.append(img)
    return frames


def hidden_cells():
    """The cells always behind the panel in the middle while the panels are
    still: inside its frame, of the shortest panel."""
    left = (W - PANEL_COLS * 8) // 2 + PAD
    right = left + PANEL_COLS * 8 - 2 * PAD
    top = define('PANEL_Y') + 8 + PAD  # under the row of hangers
    bottom = define('PANEL_Y') + 8 + min(layout['rows'] for layout in LAYOUTS) * 8 - PAD
    return {(tx, ty) for ty in range(H // TILE) for tx in range(COLS)
            if left <= tx * TILE and (tx + 1) * TILE <= right and top <= ty * TILE and (ty + 1) * TILE <= bottom}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('header')
    parser.add_argument('--preview', help='also write the backdrop as it shows, as a PNG')
    args = parser.parse_args()

    width, height, pixels = rgba(os.path.join(HERE, 'backdrop.png'))
    if (width, height) != (W, H):
        raise SystemExit(f'backdrop: art/backdrop.png is {width}x{height}, not {W}x{H}')
    art = [[p[:3] for p in row] for row in pixels]
    steam = steam_frames(art)
    paint_out_steam(art)
    darker = lambda c: tuple(round(v * d) for v, d in zip(c, DARKEN))
    cogs = [[[darker(c) for c in row] for row in gears_frame(art, f)] for f in range(GEAR_FRAMES)]
    art = cogs[0]
    steam = [[[darker(c) if c else None for c in row] for row in img] for img in steam]

    # Each band's colors: the top's and the bottom's first, then the middle's
    # grays from them.
    ends = (0, len(BANDS) - 1)
    maps = {}
    spans = [(top, BANDS[i + 1][0] if i + 1 < len(BANDS) else H) for i, (top, _, _) in enumerate(BANDS)]
    for i in ends:
        top, bottom = spans[i]
        maps[i] = reduce(Counter(c for row in art[top:bottom] for c in row), BANDS[i][2])
    pool = set(maps[ends[0]].values()) | set(maps[ends[1]].values())
    for i in range(len(BANDS)):
        if i in ends:
            continue
        top, bottom = spans[i]
        grays = reduce(Counter(c for row in art[top:bottom] for c in row), BANDS[i][2])
        snap = {g: min(pool, key=lambda q: sum((a - b) ** 2 for a, b in zip(q, g))) for g in set(grays.values())}
        maps[i] = {c: snap[g] for c, g in grays.items()}

    hidden = hidden_cells()
    data = bytearray()
    sizes = []
    shown = [[None] * W for _ in range(H)]
    for i, (top, bits, n) in enumerate(BANDS):
        bottom = spans[i][1]
        to = maps[i]
        colors = sorted(set(to.values()), key=luma)
        if bits == 4:  # index 0 stays clear, for sprites that share the palette
            palette = [None] + colors
        else:
            palette = colors
        palette += [None] * ((1 << bits) - len(palette))
        index = {c: palette.index(to[c]) for c in to}
        plain = Counter(index[art[y][x]] for tx, ty in hidden if top <= ty * TILE < bottom
                        for y in range(ty * TILE, (ty + 1) * TILE) for x in range(tx * TILE, (tx + 1) * TILE))
        tiles, grid = [], []
        if plain:  # the wall behind the middle panel, tile 0
            tiles.append(tuple([plain.most_common(1)[0][0]] * TILE * TILE))
        for ty in range(top // TILE, bottom // TILE):
            line = []
            for tx in range(COLS):
                if (tx, ty) in hidden:
                    t = tiles[0]
                else:
                    t = tuple(index[art[ty * TILE + y][tx * TILE + x]] for y in range(TILE) for x in range(TILE))
                if t not in tiles:
                    tiles.append(t)
                line.append(tiles.index(t))
                for y in range(TILE):
                    for x in range(TILE):
                        shown[ty * TILE + y][tx * TILE + x] = palette[t[y * TILE + x]]
            grid.append(line)
        if len(tiles) > 256:
            raise SystemExit(f'backdrop: {len(tiles)} tiles in the band at {top}, past 256')
        for c in palette:
            r, g, b = c or (0, 0, 0)
            data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))
        per = 8 // bits
        for t in tiles:
            for k in range(0, len(t), per):
                byte = 0
                for p in t[k:k + per]:
                    byte = byte << bits | p
                data += bytes([byte])
        for line in grid:
            data += bytes(line)
        sizes.append((top, bits, len(tiles), len(grid)))
        last = (palette, to)

    # The sprites, in the bottom band's palette.
    palette, to = last
    nearest = {}

    def pen(c):
        if c is None:
            return 0
        if c not in nearest:
            nearest[c] = palette.index(to[c]) if c in to else \
                min(range(1, len(palette)), key=lambda i: palette[i] and sum((a - b) ** 2 for a, b in zip(palette[i], c)))
        return nearest[c]

    def image(rows):
        return b''.join(bytes(row[x] << 4 | row[x + 1] for x in range(0, len(row), 2)) for row in rows)

    moving = {(x, y) for f in range(1, GEAR_FRAMES) for y in range(H) for x in range(W) if cogs[f][y][x] != cogs[0][y][x]}
    gx0 = min(x for x, _ in moving) // 4 * 4
    gx1 = (max(x for x, _ in moving) // 4 + 1) * 4
    gy0 = min(y for _, y in moving) // 4 * 4
    gy1 = (max(y for _, y in moving) // 4 + 1) * 4
    split = gy0 + (gy1 - gy0) // 8 * 4  # two sprites, as one can be 64 rows at most
    sprites = bytearray()
    for f in range(GEAR_FRAMES):
        for a, b in ((gy0, split), (split, gy1)):
            sprites += image([[pen(cogs[f][y][x]) if (x, y) in moving else 0 for x in range(gx0, gx1)]
                              for y in range(a, b)])
    for img in steam:
        sprites += image([[pen(c) for c in row] for row in img])
    data += sprites
    with open(args.output, 'wb') as f:
        f.write(data)

    names = ('TOP', 'MIDDLE', 'BOTTOM')
    with open(args.header, 'w') as f:
        f.write('/* Made by art/backdrop.py. The upgrade screen\'s backdrop. */\n\n'
                '#ifndef BACKDROP_H\n#define BACKDROP_H\n\n'
                f'#define BACKDROP_COLS {COLS}\n')
        for name, (top, bits, tiles, rows) in zip(names, sizes):
            f.write(f'#define BACKDROP_{name}_Y {top}\n'
                    f'#define BACKDROP_{name}_BPP {bits}\n'
                    f'#define BACKDROP_{name}_TILES {tiles}\n'
                    f'#define BACKDROP_{name}_ROWS {rows}\n')
        sx, sy, sx1, sy1 = STEAM_BOX
        f.write(f'#define BACKDROP_GEARS_X {gx0} /* the cogs\' two sprites, one over the other */\n'
                f'#define BACKDROP_GEARS_Y {gy0}\n'
                f'#define BACKDROP_GEARS_W {gx1 - gx0}\n'
                f'#define BACKDROP_GEARS_H1 {split - gy0}\n'
                f'#define BACKDROP_GEARS_H2 {gy1 - split}\n'
                f'#define BACKDROP_GEAR_FRAMES {GEAR_FRAMES}\n'
                f'#define BACKDROP_STEAM_X {sx}\n'
                f'#define BACKDROP_STEAM_Y {sy}\n'
                f'#define BACKDROP_STEAM_W {sx1 - sx}\n'
                f'#define BACKDROP_STEAM_H {sy1 - sy}\n'
                f'#define BACKDROP_STEAM_FRAMES {STEAM_FRAMES}\n'
                f'#define BACKDROP_SPRITE_BYTES {len(sprites)}\n'
                '\n#endif\n')
    print('backdrop: ' + ', '.join(f'{tiles} tiles of {bits} bits from {top}' for top, bits, tiles, _ in sizes)
          + f', {len(sprites)} bytes of sprites; {len(data)} bytes')

    if args.preview:
        # The backdrop as it shows, then each frame of the cogs and the
        # steam beside each other, four times as big.
        rows = [[v for c in row for v in (c + (255,))] for row in shown]
        write_png(args.preview, W, H, 6, rows)
        strip = []
        for y in range(gy0, gy1):
            line = []
            for f in range(GEAR_FRAMES):
                line += [cogs[f][y][x] for x in range(gx0, gx1)] + [(255, 255, 255)] * 2
            if y - gy0 < STEAM_BOX[3] - STEAM_BOX[1]:
                for img in steam:
                    line += [c or (40, 10, 60) for c in img[y - gy0]] + [(255, 255, 255)] * 2
            strip.append(line)
        width = max(len(line) for line in strip)
        strip = [line + [(255, 255, 255)] * (width - len(line)) for line in strip]
        big = [[v for c in line for _ in range(4) for v in c + (255,)] for line in strip for _ in range(4)]
        write_png(args.preview.replace('.png', '-frames.png'), width * 4, len(strip) * 4, 6, big)


if __name__ == '__main__':
    main()
