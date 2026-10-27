#!/usr/bin/env python3
"""Turn generated art, such as from Retro Diffusion, into Quarry's PNGs.

  rd2png.py in.png out.png [--palette-out row.png]
      in.png has at most 15 opaque colors, as Retro Diffusion's color
      reducer leaves it. A pixel with alpha under 128 becomes index 0, the
      transparent color, and the opaque colors take indexes 1 to 15,
      darkest first. --palette-out writes the 16 colors as a 16x1 palette
      row, to add to art/palettes.png.

  rd2png.py in.png out.png --palette art/palettes.png --row N
      Maps each opaque pixel to the nearest opaque color of row N of
      art/palettes.png, for art that shares a palette, such as an ore's
      nugget and its brick.

out.png is an indexed PNG that png2bin.py takes. art/style/README.md has
the rest of the steps. Only the Python standard library is used.
"""

import argparse
import struct
import sys
import zlib

from png2bin import PNG_SIGNATURE, read_png


def fail(message):
    sys.exit(f'rd2png: {message}')


def rgba(path):
    """The pixels of a PNG as rows of (r, g, b, a)."""
    width, height, color, rows, plte, trns = read_png(path)

    def pixel(sample):
        if color == 3:
            i = sample[0]
            return plte[i] + (trns[i] if i < len(trns) else 255,)
        if color == 6:
            return sample
        if color == 2:
            return sample + (255,)
        fail(f'{path}: the art must be RGB, RGBA or indexed')

    return width, height, [[pixel(s) for s in row] for row in rows]


def luma(c):
    return 299 * c[0] + 587 * c[1] + 114 * c[2]


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data)))


def write_png(path, width, height, color, rows, colors=None):
    """An 8-bit PNG: indexed with the palette colors, or RGBA."""
    header = struct.pack('>IIBBBBB', width, height, 8, color, 0, 0, 0)
    data = b''.join(b'\0' + bytes(row) for row in rows)
    chunks = chunk(b'IHDR', header)
    if colors:
        chunks += chunk(b'PLTE', b''.join(bytes(c[:3]) for c in colors))
        chunks += chunk(b'tRNS', bytes(c[3] for c in colors))
    chunks += chunk(b'IDAT', zlib.compress(data, 9)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(PNG_SIGNATURE + chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--palette-out', help='write the 16 colors as a 16x1 palette row')
    parser.add_argument('--palette', help='map onto a row of this palette image')
    parser.add_argument('--row', type=int, help='the row of --palette')
    args = parser.parse_args()
    if (args.palette is None) != (args.row is None):
        parser.error('--palette and --row go together')

    width, height, pixels = rgba(args.input)
    if args.palette:
        _, _, rows = rgba(args.palette)
        if not 0 <= args.row < len(rows) or len(rows[args.row]) != 16:
            fail(f'{args.palette} has no 16-color row {args.row}')
        colors = [(0, 0, 0, 0)] + list(rows[args.row][1:])
    else:
        opaque = sorted({p[:3] for row in pixels for p in row if p[3] >= 128}, key=luma)
        if len(opaque) > 15:
            fail(f'{args.input}: {len(opaque)} opaque colors, 15 at most; reduce them first')
        colors = [(0, 0, 0, 0)] + [c + (255,) for c in opaque]
        colors += [(0, 0, 0, 0)] * (16 - len(colors))
    choices = [i for i in range(1, 16) if colors[i][3] >= 128]

    def index(p):
        if p[3] < 128:
            return 0
        return min(choices, key=lambda i: sum((a - b) ** 2 for a, b in zip(p[:3], colors[i][:3])))

    write_png(args.output, width, height, 3, [[index(p) for p in row] for row in pixels], colors)
    if args.palette_out:
        write_png(args.palette_out, 16, 1, 6, [[v for c in colors for v in c]])


if __name__ == '__main__':
    main()
