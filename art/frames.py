#!/usr/bin/env python3
"""Cut a frame set for the playfield from Retro Diffusion's art, as art/style/README.md describes it.

  frames.py n out.bin [--preview out.png]

art/frames/frame-n.png is a whole frame as Retro Diffusion drew it: a post
down each side and a beam across the top, with a knee brace in each top
corner. Its left post, its beam and the corner where they meet are cut to
the sizes of src/xram.h, each ending on its edge where the ball bounces,
its dark outline with the bright flange just inside. CUTS gives, for each
set, the columns of its post from the outside in and the rows of its beam
from the top down, plain columns or rows of steel left out where the art
is wider than the game's, never a rivet or an edge; then the post's rows
and the beam's columns along their length, and where its brace starts,
just inside the post and under the beam.

The post is two sprite images of 64 rows that alternate down the screen,
128 rows in all, and the beam is pieces 64 wide, the last of them over the
one before it by a multiple of 8, as the playfield's width falls. Retro
Diffusion spaces rivets unevenly, so a post or a beam is one cell of its
art, a rivet and the plate around it, 8 long, repeated: its rivets fall
every 8, and it joins itself at every piece and every overlap. The brace
is behind the ball, in the set's colors at SHADE, without the rock or the
shadows around it, and no brighter than the brightest of the machine on
the right wall, so it never looks like something to bounce off.

out.bin is a frame_set_t of src/xram.h: the set's palette, 16 colors as
png2bin.py writes a palette row, the same colors at SHADE for the brace,
then the post's two halves, the beam, the cap and the brace, each a 4-bit image with
the left pixel of each pair in the high nibble. Only the Python standard
library is used.
"""

import argparse
import os
import struct
from collections import Counter

from curtain import reduce
from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
POST_W, BEAM_H, BRACE = 16, 16, 32
SHADE = 0.4  # the brace's colors, of the set's
DIM = 66  # in the brace, darker than this is rock or shadow, and goes clear

# Each set: its post's columns, its beam's rows, the post's rows down it
# and the beam's columns along it, and its brace's top left.
_GIRDER = list(range(0, 8)) + list(range(10, 18))  # two plain columns of the web out


def _cell(start):
    """8 rows or columns from start, a rivet and the plate after it, 16 times."""
    return [start + i % 8 for i in range(128)]


CUTS = {
    1: (_GIRDER, _GIRDER, _cell(63), _cell(34)[:64], (18, 18)),  # a riveted steel girder
}


def luma(c):
    return (299 * c[0] + 587 * c[1] + 114 * c[2]) // 1000


def cut(n):
    """The set's post, beam, cap and brace, as rows of colors, None clear."""
    cols, rows, post_rows, beam_cols, (bx, by) = CUTS[n]
    _, _, px = rgba(os.path.join(HERE, 'frames', f'frame-{n}.png'))
    px = [[p[:3] for p in row] for row in px]
    post = [[px[y][x] for x in cols] for y in post_rows]
    beam = [[px[y][x] for x in beam_cols] for y in rows]
    cap = [[px[y][x] for x in cols] for y in rows]
    brace = [[px[y][x] if luma(px[y][x]) >= DIM else None for x in range(bx, bx + BRACE)]
             for y in range(by, by + BRACE)]
    assert len(post) == 128 and len(beam[0]) == 64 and len(post[0]) == POST_W and len(beam) == BEAM_H
    return post, beam, cap, brace


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
    for img in pieces:
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
        outer, far = left - POST_W, right + POST_W
        x = outer
        while x + 64 < far:
            put(beam, x, 0)
            x += 64
        put(beam, far - 64, 0)
        put(cap, outer, 0)
        put(cap, right, 0, flip=True)
        write_png(args.preview, w, h, 2, [[v for c in row for v in c] for row in out])


if __name__ == '__main__':
    main()
