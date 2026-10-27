#!/usr/bin/env python3
"""Draw the pieces of the play screen, as art/style/README.md describes them.

  screen.py

Writes art/post.png, art/beam.png, art/cap.png, art/brace.png,
art/machine.png, art/digits.png, art/energy.png and art/copyright.png. Run it after a change
to the drawing here, then touch up any of them by hand.

The frame is a post on each side of the playfield and the cap beam across
the top. The inner face of a post and the underside of the beam are where
the ball bounces, so each is a bright line. Each piece is drawn for the left
side, and the right side shows it with MODE5_HFLIP. The braces and the
machine stand behind the ball. The digits are 6x8 with a 1 px outline, in
8x12 sprites. The energy gauge is a placeholder until its redesign.

The frame, the machine and the digits use the sled row of art/palettes.png,
and the gauge the fx row.
"""

import os

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_ROW, SLED_ROW, FX_ROW = 0, 4, 2
CREDIT = 7  # the pale steel of the main row

# The sled row, by index.
OUT, G0, TAIL, G1, Y1, G2, RED, G3, ORANGE, Y2, Y3, Y4, Y5, CREAM = range(1, 15)


def grid(w, h):
    return [[0] * w for _ in range(h)]


def post():
    """A 64-row stretch of the left post, the inner face on the right, with a
    hydraulic section."""
    rows = grid(8, 64)
    faces = [OUT, G0, Y1, Y3, Y3, Y4, Y3, Y5]
    piston = [OUT, G0, G1, G2, G3, G3, G2, Y5]
    for y in range(64):
        rows[y] = list(piston if 40 <= y < 56 else faces)
        if y in (39, 56):
            rows[y] = [OUT] * 7 + [Y5]  # the collars of the piston
    for y in (8, 24):
        rows[y][3] = Y1  # bolts
    return rows


def beam():
    """64 columns of the cap beam, which repeat every 8."""
    rows = grid(64, 16)
    plain = {0: OUT, 1: G1, 2: G2, 3: G1, 4: OUT, 11: OUT, 12: G1, 13: G0, 14: Y3, 15: Y5}
    for y in range(16):
        for x in range(64):
            rows[y][x] = plain[y] if y in plain else (OUT if (x + y) % 8 < 4 else Y3)
    return rows


def cap():
    """The bracket over the left post, where the beam ends."""
    rows = grid(8, 16)
    for y in range(16):
        for x in range(8):
            rows[y][x] = OUT if y == 0 or x == 0 else (G2 if x == 1 else G1)
        rows[y][7] = Y5  # the inner face of the post runs up to the corner
    rows[15] = [OUT] + [Y5] * 7  # and the underside of the beam runs over it
    for y in (4, 11):
        rows[y][4] = G3  # bolts
    return rows


def brace():
    """A 45 degree knee brace from the left post up to the beam, with a
    bolted plate at each end."""
    rows = grid(32, 32)
    shades = {-3: OUT, -2: G3, -1: G2, 0: G2, 1: G1, 2: G0, 3: OUT}
    for y in range(32):
        for x in range(32):
            d = x + y - 31
            if d in shades:
                rows[y][x] = shades[d]
    for px, py in ((0, 25), (25, 0)):
        for y in range(py, py + 7):
            for x in range(px, px + 7):
                edge = x in (px, px + 6) or y in (py, py + 6)
                rows[y][x] = OUT if edge else G1
        rows[py + 3][px + 3] = G3
    return rows


def machine():
    """A machine bolted to the inside of the right wall, drawn here for the
    left wall: its brackets on the left, against the post."""
    rows = grid(24, 40)
    for y in range(2, 38):
        for x in range(2, 22):
            edge = x in (2, 21) or y in (2, 37)
            rows[y][x] = OUT if edge else (Y3 if y < 8 else G1)
    for x in range(4, 20, 4):
        rows[4][x] = OUT  # the hazard marks on its lid
        rows[5][x + 1] = OUT
    for y in range(12, 26, 2):
        for x in range(6, 18):
            rows[y][x] = G0  # its vents
    for y in range(29, 34):
        for x in range(5, 13):
            rows[y][x] = OUT if y in (29, 33) or x in (5, 12) else G0
    rows[31][7], rows[31][8] = ORANGE, Y4  # a readout
    for y in (30, 31):
        rows[y][17] = rows[y][18] = RED  # the lamp, which the game lights
    for py in (6, 30):
        for y in range(py, py + 4):
            rows[y][0], rows[y][1] = OUT, G2  # brackets against the wall
    return rows


DIGITS = {
    '0': ['.####.', '##..##', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
    '1': ['..##..', '.###..', '..##..', '..##..', '..##..', '..##..', '..##..', '.####.'],
    '2': ['.####.', '##..##', '....##', '...##.', '..##..', '.##...', '##....', '######'],
    '3': ['#####.', '....##', '....##', '.####.', '....##', '....##', '....##', '#####.'],
    '4': ['##..##', '##..##', '##..##', '######', '....##', '....##', '....##', '....##'],
    '5': ['######', '##....', '##....', '#####.', '....##', '....##', '##..##', '.####.'],
    '6': ['.####.', '##....', '##....', '#####.', '##..##', '##..##', '##..##', '.####.'],
    '7': ['######', '....##', '....##', '...##.', '..##..', '..##..', '..##..', '..##..'],
    '8': ['.####.', '##..##', '##..##', '.####.', '##..##', '##..##', '##..##', '.####.'],
    '9': ['.####.', '##..##', '##..##', '##..##', '.#####', '....##', '....##', '.####.'],
}


def digit(ch):
    """An 8x12 sprite: the 6x8 digit at 1, 1, the top half bright, and a
    1 px outline all around."""
    rows = grid(8, 12)
    on = {(1 + x, 1 + y) for y, line in enumerate(DIGITS[ch]) for x, c in enumerate(line) if c == '#'}
    for x, y in on:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                rows[y + dy][x + dx] = OUT
    for x, y in on:
        rows[y][x] = Y5 if y <= 4 else CREAM
    return rows


def gauge():
    """The placeholder energy gauge, in the fx row: the top, a full, a low and
    an empty segment, and the bottom, 8x8 each."""
    DARK, EMPTY, STEEL, PALE, FULL, LIGHT, LOW = 1, 2, 4, 5, 11, 12, 13
    pieces = []
    for kind in ('top', 'full', 'low', 'empty', 'bottom'):
        rows = grid(8, 8)
        for y in range(8):
            rows[y] = [DARK, STEEL] + [EMPTY] * 4 + [STEEL, DARK]
        if kind in ('full', 'low'):
            for y in range(7):
                rows[y][2:6] = [LIGHT if kind == 'full' and y == 0 else FULL if kind == 'full' else LOW] * 4
        if kind == 'top':
            rows[0] = [DARK] * 8
            rows[1] = rows[2] = [DARK] + [PALE] * 6 + [DARK]
            rows[3] = [DARK] + [STEEL] * 6 + [DARK]
        if kind == 'bottom':
            rows[4] = [DARK] + [STEEL] * 6 + [DARK]
            rows[5] = rows[6] = [DARK] + [PALE] * 6 + [DARK]
            rows[7] = [DARK] * 8
        pieces.append(rows)
    return [[c for piece in pieces for c in piece[y]] for y in range(8)]


def copyright():
    """The copyright sign, 8x8, in the main row, the color of the credit."""
    lines = ['..####..', '.#....#.', '#..##..#', '#.#....#', '#.#....#', '#..##..#', '.#....#.',
             '..####..']
    return [[CREDIT if c == '#' else 0 for c in line] for line in lines]


def strip(frames):
    return [[c for frame in frames for c in frame[y]] for y in range(len(frames[0]))]


def main():
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    main_, sled, fx = palettes[MAIN_ROW], palettes[SLED_ROW], palettes[FX_ROW]
    for name, rows, colors in (
        ('post', post(), sled), ('beam', beam(), sled), ('cap', cap(), sled),
        ('brace', brace(), sled), ('machine', machine(), sled),
        ('digits', strip([digit(c) for c in '0123456789']), sled), ('energy', gauge(), fx),
        ('copyright', copyright(), main_),
    ):
        write_png(os.path.join(HERE, f'{name}.png'), len(rows[0]), len(rows), 3, rows, colors)


if __name__ == '__main__':
    main()
