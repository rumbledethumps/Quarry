#!/usr/bin/env python3
"""Turn a curtain image from Retro Diffusion into a curtain set for a level.

  curtain.py in.png out.bin [--preview out.png]

in.png is 256x240: two rock walls framing a dark shaft down the middle, as
art/style/README.md describes. The shaft goes clear, so each wall keeps the
rock's own edge, and the rock is darkened and cut to 15 colors, the
closest merged, then to ROCK_COLORS, the least used merged, so the row
has room for the sight glass of the energy gauge. The left curtain is the
CURTAIN_W columns left of the middle, and the right curtain the CURTAIN_W
columns right of it.

out.bin is the palette, 16 colors as png2bin.py writes a palette row, then
the 4 colors of the texture behind the playfield, then each curtain as
sprite images: CURTAIN_COLS across and CURTAIN_ROWS down, row by row, each
image packed as png2bin.py packs one. CURTAIN_W and the sizes are those of
src/xram.h. Only the Python standard library is used.

The texture's colors are near grays at the four faint levels of
TEXTURE_LUMA, so the floor of the playfield matches the walls around it.
A color has 5 bits a channel, and at these levels one step of one channel
is a strong tint, so each color is a gray, or a gray a step warmer in the
rock's strongest channel, or in its two strongest: dark grays and browns,
never green or purple.
"""

import argparse
import struct
from collections import Counter, deque

from rd2png import rgba, write_png

# Room to spare, if the level screen runs short of XRAM: on level 1, the
# narrowest, each curtain has 13 columns off the screen behind frame set 1,
# whose post shows 16, and 15 behind set 2. Curtains 87 or 88 wide would
# give back about 3 KB, until a level is narrower than level 1.
CURTAIN_W = 100
CURTAIN_COLS = (64, 36)
CURTAIN_ROWS = (64, 64, 64, 48)
DARKEN = (0.57, 0.6, 0.67)  # red, green and blue, darker and a little cool
TEXTURE_LUMA = (7.3, 10.3, 13.7, 17.4)  # of 255, the four levels of the texture
SHAFT_RUN = 32  # rows of one color down the middle column that are shaft, not rock
ROCK_COLORS = 13  # of the row's 15, two left for the sight glass


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def rgb555(r5, g5, b5):
    """An opaque color, as the VGA takes it, from 5-bit channels."""
    return b5 << 11 | g5 << 6 | 32 | r5


def texture_colors(counts):
    """The 4 colors of the texture, as 5-bit channels, from the colors of
    the rock and how many pixels each has."""
    total = [sum(c[i] * n for c, n in counts.items()) for i in range(3)]
    order = sorted(range(3), key=lambda i: -total[i])  # the rock's channels, strongest first
    candidates = []
    for gray in range(8):
        for steps in range(3):
            c5 = [gray] * 3
            for i in order[:steps]:
                c5[i] += 1
            candidates.append(c5)
    levels = []
    for target in TEXTURE_LUMA:
        above = [c for c in candidates if not levels or luma(c) > luma(levels[-1])]
        levels.append(min(above, key=lambda c: abs(luma(c) * 8 - target)))
    return levels


def clear_shaft(pixels, width, height):
    """The shaft is each color that runs SHAFT_RUN rows or more down the
    middle column, and every pixel of those colors joined to the middle
    column goes clear. Where rock crosses the middle, nothing does."""
    middle = [pixels[y][width // 2][:3] for y in range(height)]
    shaft = set()
    run = 1
    for y in range(1, height + 1):
        if y < height and middle[y] == middle[y - 1]:
            run += 1
            continue
        if run >= SHAFT_RUN:
            shaft.add(middle[y - 1])
        run = 1
    todo = deque((width // 2, y) for y in range(height) if middle[y] in shaft)
    while todo:
        x, y = todo.popleft()
        if 0 <= x < width and 0 <= y < height and pixels[y][x][3] and pixels[y][x][:3] in shaft:
            pixels[y][x] = (0, 0, 0, 0)
            todo.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))


def reduce(counts, n, least_used=False):
    """Merges the two closest colors until n are left, or with least_used,
    the two whose merge moves the fewest pixels the least: their distance
    weighted by the pixels of both. Returns a map from each color to the one
    it became."""
    weight = dict(counts)  # each color now, and its pixels
    members = {c: [c] for c in counts}

    def cost(pq):
        d = sum((x - y) ** 2 for x, y in zip(*pq))
        wa, wb = weight[pq[0]], weight[pq[1]]
        return d * wa * wb / (wa + wb) if least_used else d

    while len(weight) > n:
        keys = list(weight)
        a, b = min(((p, q) for i, p in enumerate(keys) for q in keys[i + 1:]), key=cost)
        wa, wb = weight.pop(a), weight.pop(b)
        merged = tuple(round((x * wa + y * wb) / (wa + wb)) for x, y in zip(a, b))
        old = members.pop(a) + members.pop(b)
        weight[merged] = weight.get(merged, 0) + wa + wb
        members[merged] = members.get(merged, []) + old
    return {c: target for target, olds in members.items() for c in olds}


def tiles(rows, left):
    """The images of a curtain from column left, as bytes."""
    data = bytearray()
    top = 0
    for h in CURTAIN_ROWS:
        x = left
        for w in CURTAIN_COLS:
            for y in range(top, top + h):
                line = rows[y][x:x + w]
                data += bytes(line[i] << 4 | line[i + 1] for i in range(0, w, 2))
            x += w
        top += h
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--preview', help='also write the two curtains as a PNG')
    args = parser.parse_args()
    width, height, pixels = rgba(args.input)
    if (width, height) != (256, 240):
        raise SystemExit(f'curtain: {args.input} is {width}x{height}, not 256x240')
    clear_shaft(pixels, width, height)
    for row in pixels:
        for x, (r, g, b, a) in enumerate(row):
            if a:
                row[x] = (round(r * DARKEN[0]), round(g * DARKEN[1]), round(b * DARKEN[2]), 255)
    counts = Counter(p[:3] for row in pixels for p in row if p[3])
    to = reduce(counts, 15)
    fewer = reduce(Counter(to[p[:3]] for row in pixels for p in row if p[3]), ROCK_COLORS, least_used=True)
    to = {c: fewer[t] for c, t in to.items()}
    colors = sorted(set(to.values()), key=lambda c: 299 * c[0] + 587 * c[1] + 114 * c[2])
    index = {c: colors.index(to[c]) + 1 for c in to}
    rows = [[index[p[:3]] if p[3] else 0 for p in row] for row in pixels]
    palette = [(0, 0, 0, 0)] + [c + (255,) for c in colors]
    palette += [(0, 0, 0, 0)] * (16 - len(palette))
    data = bytearray()
    for r, g, b, a in palette:
        data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if a >= 128 else 0))
    for c5 in texture_colors(Counter(to[p[:3]] for row in pixels for p in row if p[3])):
        data += struct.pack('<H', rgb555(*c5))
    data += tiles(rows, width // 2 - CURTAIN_W) + tiles(rows, width // 2)
    with open(args.output, 'wb') as f:
        f.write(data)
    if args.preview:
        halves = [row[width // 2 - CURTAIN_W:width // 2] + [0] * 8 + row[width // 2:width // 2 + CURTAIN_W]
                  for row in rows]
        write_png(args.preview, 2 * CURTAIN_W + 8, height, 3, halves, palette)


if __name__ == '__main__':
    main()
