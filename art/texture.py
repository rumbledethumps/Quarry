#!/usr/bin/env python3
"""Draw the texture behind the playfield, as art/style/README.md describes it.

  texture.py out.bin [--preview out.png]

Two octaves of Perlin noise, cut into four levels of equal area, at 2 bits
a pixel: 320x240, four pixels to a byte, the leftmost in the high bits. The
noise repeats across and down, so the bitmap wraps, and each stage can show
it from a new place. The colors are the first four of the texture row of
art/palettes.png.
"""

import argparse
import math
import os
import random

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
WIDTH, HEIGHT = 320, 240
TEXTURE_ROW = 5  # the texture row of art/palettes.png
SEED = 7


def perlin(rng, cells_x, cells_y):
    """Noise for every pixel, from a grid of random gradients that wraps."""
    grads = [[(math.cos(a), math.sin(a))
              for a in (rng.uniform(0, 2 * math.pi) for _ in range(cells_x))]
             for _ in range(cells_y)]
    cw, ch = WIDTH / cells_x, HEIGHT / cells_y
    fade = lambda t: t * t * t * (t * (t * 6 - 15) + 10)
    out = []
    for y in range(HEIGHT):
        row = []
        gy = y / ch
        y0 = int(gy)
        fy = gy - y0
        for x in range(WIDTH):
            gx = x / cw
            x0 = int(gx)
            fx = gx - x0

            def dot(cx, cy):
                g = grads[(y0 + cy) % cells_y][(x0 + cx) % cells_x]
                return g[0] * (fx - cx) + g[1] * (fy - cy)

            u, v = fade(fx), fade(fy)
            a = dot(0, 0) + u * (dot(1, 0) - dot(0, 0))
            b = dot(0, 1) + u * (dot(1, 1) - dot(0, 1))
            row.append(a + v * (b - a))
        out.append(row)
    return out


def texture():
    """The rows of the texture, color indexes 0 to 3."""
    rng = random.Random(SEED)
    big, small = perlin(rng, 4, 3), perlin(rng, 10, 8)
    values = [[big[y][x] + 0.4 * small[y][x] for x in range(WIDTH)] for y in range(HEIGHT)]
    flat = sorted(v for row in values for v in row)
    cuts = [flat[len(flat) * k // 4] for k in (1, 2, 3)]
    return [[sum(v > c for c in cuts) for v in row] for row in values]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('output')
    parser.add_argument('--preview', help='also write the texture as a PNG')
    args = parser.parse_args()
    rows = texture()
    data = bytes(r[x] << 6 | r[x + 1] << 4 | r[x + 2] << 2 | r[x + 3]
                 for r in rows for x in range(0, WIDTH, 4))
    with open(args.output, 'wb') as f:
        f.write(data)
    if args.preview:
        _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
        write_png(args.preview, WIDTH, HEIGHT, 3, rows, palettes[TEXTURE_ROW][:4])


if __name__ == '__main__':
    main()
