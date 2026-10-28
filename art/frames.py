#!/usr/bin/env python3
"""Cut a frame set for the playfield from Retro Diffusion's art, as art/style/README.md describes it.

  frames.py n out.bin [--preview out.png]

A frame set's art is in art/frames/: frame-n.png, a whole frame as Retro
Diffusion drew it, a post down each side and a beam across the top with a
knee brace in each top corner, and for some sets the post and the beam
drawn again as strips that repeat, frame-n-post.png and frame-n-beam.png.
CUTS gives each piece's image and its columns and rows: the post's from
the outside in, then down it, and the beam's along it, then from the top
down. Each ends on its edge where the ball bounces, its dark outline with
the bright flange just inside. Plain columns or rows of steel are left out
where the art is wider than the game's, or repeated where it is narrower,
never a rivet, a brace or an edge. A post shows 16 or 20 columns, from its
inside, and None for its first columns leaves them clear; the frame lays
itself out by how many show. A set drawn on green has its gaps clear, so
the rock shows through: a pixel clearly greener than gray is a gap, and
the rest are turned to the cool gray of steel, each as bright as it was,
so no green or rusty brown is left in it.

The post is two sprite images of 64 rows that alternate down the screen,
128 rows in all. The beam is pieces 64 wide from the left post, and the
last is as wide as what is left, a multiple of 8, so the beam's first 8,
16 and on to 56 columns come too, each an image. So a post must repeat
every 128 rows, or 64, and a beam every 64 columns. Retro Diffusion spaces
rivets unevenly, so a girder's post or beam is one cell of its art, a
rivet and the plate around it, 8 long, repeated; a strip drawn to repeat
is used as it is. The brace is behind the ball, in the set's colors at
SHADE, without the rock or the shadows around it, and no brighter than the
brightest of the machine on the right wall, so it never looks like
something to bounce off.

out.bin is a frame_set_t of src/xram.h: the set's palette, 16 colors as
png2bin.py writes a palette row, the same colors at SHADE for the brace,
how many of the post's columns show and a spare byte, then the post's two
halves, the beam, its ends, the cap and the brace,
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
POST_W, BEAM_H, BRACE = 20, 16, 32
SHADE = 0.4  # the brace's colors, of the set's
DIM = 66  # in the brace, darker than this is rock or shadow, and goes clear

# Each set: for each piece, its image, then its columns and its rows.
_GIRDER = list(range(0, 8)) + list(range(10, 18))  # two plain columns of the web out
_TRUSS = [8] + list(range(7, 26))  # its outer chord a column wider, to show 20


def _cell(start):
    """8 rows or columns from start, a rivet and the plate after it, 16 times."""
    return [start + i % 8 for i in range(128)]


CUTS = {
    1: {  # a riveted steel girder, showing 16
        'on green': False,
        'post': ('frame-1.png', [None] * 4 + _GIRDER, _cell(63)),
        'beam': ('frame-1.png', _cell(34)[:64], _GIRDER),
        'cap': ('frame-1.png', [None] * 4 + _GIRDER, _GIRDER),
        'brace': ('frame-1.png', range(18, 18 + BRACE), range(18, 18 + BRACE)),
    },
    2: {  # an open truss of welded bars with X bracing, showing 20; its beam's
        # top chord is off the top of the screen, and its uprights are 3 wide
        'on green': True,
        'post': ('frame-2.png', _TRUSS, [55 + i % 16 for i in range(128)]),
        'beam': ('frame-2.png', ([37, 38, 38, 38] + list(range(39, 51))) * 4, list(range(7, 23))),
        'cap': ('frame-2.png', _TRUSS, list(range(7, 23))),
        'brace': ('frame-2.png', range(26, 26 + BRACE), range(23, 23 + BRACE)),
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
    assert len(post) == 128 and len(post[0]) == POST_W and len(beam) == BEAM_H and len(beam[0]) == 64
    assert len(cap) == BEAM_H and len(cap[0]) == POST_W
    return post, beam, cap, brace


def shows(n):
    """How many of the set's post's columns show, from its inside."""
    cols = CUTS[n]['post'][1]
    count = sum(1 for x in cols if x is not None)
    assert count % 4 == 0, f'set {n} shows {count} columns, not a multiple of 4'
    return count


def machine_luma():
    """The brightest the machine on the right wall gets: art/machine.png, in
    the sled row, as the shade row shows it."""
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    sled, shade = palettes[4], palettes[7]
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
    parser.add_argument('--preview', help='also write the frame around a stage 1 playfield, at its size')
    args = parser.parse_args()

    pieces = cut(args.n)
    counts = Counter(c for img in pieces for row in img for c in row if c)
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
    for img in [post, beam] + [[row[:w] for row in beam] for w in range(8, 64, 8)] + [cap, brace]:
        data += packed(img, index)
    with open(args.output, 'wb') as f:
        f.write(data)
    print(f'frame {args.n}: {len(colors)} colors, the brace at {brightest}, the machine at {machine}')

    if args.preview:
        # A stage 1 playfield, 120 wide, its frame drawn as src/frame.c lays it.
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
        for y in range(0, h, 64):
            half = post[y % 128:y % 128 + 64]
            put(half, left - POST_W, y)
            put(half, right, y, flip=True)
        outer, far = left - shows(args.n), right + shows(args.n)
        for x in range(outer, far, 64):
            put([row[:far - x] for row in beam], x, 0)
        put(cap, left - POST_W, 0)
        put(cap, right, 0, flip=True)
        write_png(args.preview, w, h, 2, [[v for c in row for v in c] for row in out])


if __name__ == '__main__':
    main()
