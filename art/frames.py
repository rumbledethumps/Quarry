#!/usr/bin/env python3
"""Cut a frame set for the playfield from its art, as art/style/README.md describes it.

  frames.py n out.bin [--preview out.png]

A frame set's art is art/frames/frame-n.png: a whole frame as Retro
Diffusion drew it, a post down each side and a beam across the top with a
knee brace in each top corner, or a sheet of a post, a beam and a brace
drawn by hand. CUTS gives each piece's columns and rows: the post's from
the outside in, then down it, and the beam's along it, then from the top
down. Each ends on its edge where the ball bounces, its dark outline with
bright steel just inside. Plain columns or rows of steel are left out
where the art is wider than the game's, or repeated where it is narrower,
never a rivet, a brace or an edge. A post shows up to 20 columns, from
its inside, and None for its first columns leaves them clear; the
curtains tuck under it by how many show. A set drawn on green has its
gaps clear, so the rock shows through: a pixel clearly greener than gray
is a gap, and the rest are turned to the cool gray of steel, each as
bright as it was, so no green or rusty brown is left in it.

The post is one sprite image 48 rows tall, down the screen again and
again, and the beam pieces 48 wide from the left post, then if a
playfield leaves half a piece, an end piece of its first 24 columns. A
playfield is a multiple of 24 wide, so a post or a beam repeats every 8,
12, 16 or 24 and joins itself at every piece, and one that repeats every
12 or 24 fits a whole number of times between the posts of any level, so
it ends the same at both. Retro Diffusion spaces rivets unevenly, so a
girder's post or beam is one cell of its art, a rivet and the plate
around it, 8 long, repeated. The brace is behind the ball, in the set's
colors at SHADE, without the rock or the shadows around it, and no
brighter than the brightest of the machine on the right wall, so it
never looks like something to bounce off.

out.bin is a frame_set_t of src/xram.h: the set's palette, 16 colors as
png2bin.py writes a palette row, the same colors at SHADE for the brace,
how many of the post's columns show and a spare byte, then the post, the
beam, its end piece, the cap and the brace,
each a 4-bit image with the left pixel of each pair in the high nibble. Only the Python standard
library is used.
"""

import argparse
import os
import struct
from collections import Counter

from curtain import reduce
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
POST_W, POST_H, BEAM_W, BEAM_H, BRACE = 20, 48, 48, 16, 32
SHADE = 0.4  # the brace's colors, of the set's
DIM = 66  # in the brace, darker than this is rock or shadow, and goes clear
SLED_ROW, SHADE_ROW = 4, 7  # of art/palettes.png

# Each set: for each piece, its image, then its columns and its rows.
_GIRDER = list(range(0, 8)) + list(range(10, 18))  # two plain columns of the web out


def _cell(start):
    """8 rows or columns from start, a rivet and the plate after it, 6 times."""
    return [start + i % 8 for i in range(48)]


CUTS = {
    1: {  # a riveted steel girder, showing 16
        'on green': False,
        'post': ('frame-1.png', [None] * 4 + _GIRDER, _cell(63)),
        'beam': ('frame-1.png', _cell(34), _GIRDER),
        'cap': ('frame-1.png', [None] * 4 + _GIRDER, _GIRDER),
        'brace': ('frame-1.png', range(18, 18 + BRACE), range(18, 18 + BRACE)),
    },
    2: {  # an open truss of welded bars with X bracing, showing 18, drawn by hand, a 12 px
        # bay of it 4 times over; the beam is the tower laid on its side, its
        # top chord off the top of the screen, from half an upright to half an
        # upright; the brace is the gusset Retro Diffusion drew for its truss
        'on green': True,
        'post': ('frame-2.png', [None] * 2 + list(range(18)), list(range(48))),
        'beam': ('frame-2.png', list(range(24, 72)), list(range(2, 18))),
        'cap': ('frame-2.png', [None] * 2 + list(range(18)), list(range(16))),
        'brace': ('frame-2.png', range(24, 24 + BRACE), range(24, 24 + BRACE)),
    },
}


def luma(c):
    return (299 * c[0] + 587 * c[1] + 114 * c[2]) // 1000


def green(c):
    return c[1] - max(c[0], c[2]) > 40


def gray(c):
    """c as the cool gray of steel, as bright as it was."""
    v = luma(c)
    return (min(255, v * 94 // 100), min(255, v * 99 // 100), min(255, v * 106 // 100))


def cut(n):
    """The set's post, beam, cap and brace, as rows of colors, None clear."""
    images = {}

    def piece(name, clear):
        path, cols, rows = CUTS[n][name]
        if path not in images:
            _, _, px = rgba(os.path.join(HERE, 'frames', path))
            images[path] = [[p[:3] for p in row] for row in px]
        px = images[path]
        tint = gray if CUTS[n]['on green'] else (lambda c: c)
        return [[None if x is None or clear(px[y][x]) else tint(px[y][x]) for x in cols] for y in rows]

    gap = green if CUTS[n]['on green'] else (lambda c: False)
    post = piece('post', gap)
    beam = piece('beam', gap)
    cap = piece('cap', gap)
    brace = piece('brace', lambda c: gap(c) or luma(c) < DIM)
    assert len(post) == POST_H and len(post[0]) == POST_W and len(beam) == BEAM_H and len(beam[0]) == BEAM_W
    assert len(cap) == BEAM_H and len(cap[0]) == POST_W
    return post, beam, cap, brace


def shows(n):
    """How many of the set's post's columns show, from its inside."""
    cols = CUTS[n]['post'][1]
    return sum(1 for x in cols if x is not None)


def machine_luma():
    """The brightest the machine on the right wall gets: art/machine.png, in
    the sled row, as the shade row shows it."""
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    sled, shade = palettes[SLED_ROW], palettes[SHADE_ROW]
    _, _, img = rgba(os.path.join(HERE, 'machine.png'))
    shown = {shade[sled.index(p)][:3] for row in img for p in row if p[3]}
    return max(luma(c) for c in shown)


def packed(img, index):
    return bytes(index.get(row[x], 0) << 4 | index.get(row[x + 1], 0)
                 for row in img for x in range(0, len(row), 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('n', type=int)
    parser.add_argument('output')
    parser.add_argument('--preview', help='also write the frame around a level 1 playfield, at its size')
    args = parser.parse_args()

    pieces = cut(args.n)
    # The colors weighed as a post of 128 rows and a beam of 64 columns
    # would weigh them, the girder's rivet cells 16 and 8 times over.
    counts = Counter()
    for img, weight in zip(pieces, (8, 4, 3, 3)):
        for row in img:
            for c in row:
                if c:
                    counts[c] += weight
    to = reduce(counts, 15)
    colors = sorted(set(to.values()), key=luma)
    index = {c: colors.index(to[c]) + 1 for c in to}
    shade = [tuple(int(v * SHADE) for v in c) for c in colors]
    brace_colors = {to[c] for row in pieces[3] for c in row if c}
    brightest = max(luma(shade[colors.index(c)]) for c in brace_colors)
    machine = machine_luma()
    if brightest >= machine:
        raise SystemExit(f'frames.py: the brace of set {args.n} reaches {brightest}, '
                         f'as bright as the machine, {machine}; lower SHADE')

    data = bytearray()
    for pal in (colors, shade):
        for c in [None] + pal + [None] * (15 - len(pal)):
            r, g, b = c or (0, 0, 0)
            data += struct.pack('<H', (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3) | (32 if c else 0))
    data += bytes([shows(args.n), 0])
    post, beam, cap, brace = pieces
    end = [row[:BEAM_W // 2] for row in beam]
    for img in (post, beam, end, cap, brace):
        data += packed(img, index)
    with open(args.output, 'wb') as f:
        f.write(data)
    print(f'frame {args.n}: {len(colors)} colors, the brace at {brightest}, the machine at {machine}')

    if args.preview:
        # A level 1 playfield, 120 wide, its frame drawn as src/frame.c lays it.
        left, right, w, h = POST_W + 4, POST_W + 124, 2 * POST_W + 128, 240
        out = [[(20, 22, 28)] * w for _ in range(h)]

        def put(img, x0, y0, flip=False, dim=False):
            for y, row in enumerate(img):
                for x, c in enumerate(reversed(row) if flip else row):
                    if c and 0 <= x0 + x < w and 0 <= y0 + y < h:
                        k = to[c]
                        out[y0 + y][x0 + x] = shade[colors.index(k)] if dim else k
        post, beam, cap, brace = pieces
        put(brace, left, BEAM_H, dim=True)
        put(brace, right - BRACE, BEAM_H, flip=True, dim=True)
        for y in range(0, h, POST_H):
            put(post, left - POST_W, y)
            put(post, right, y, flip=True)
        for x in range(left, right, BEAM_W):
            put(beam if right - x >= BEAM_W else end, x, 0)
        put(cap, left - POST_W, 0)
        put(cap, right, 0, flip=True)
        write_png(args.preview, w, h, 2, [[v for c in row for v in c] for row in out])


if __name__ == '__main__':
    main()
