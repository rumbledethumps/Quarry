#!/usr/bin/env python3
"""Draw the pieces of the play screen, as art/style/README.md describes them.

  screen.py

Writes art/machine.png, art/digits.png, art/energy.png and
art/cursor.png. Run it after a change to the drawing here, then touch up
any of them by hand. The frame of the playfield comes from art/frames.py.

The machine is drawn for the left wall, stands behind the ball, and the
right wall shows it with MODE5_HFLIP. The digits are 6x8 with a 1 px
outline, in 8x12 sprites. The energy gauge is a placeholder until its
redesign.

The machine and the digits use the sled row of art/palettes.png, the
gauge the fx row, and the cursor the holo row. The coin is drawn by
art/bricks.py. The cursor is one corner of the holographic outline of the
upgrade screen and the menus, and MODE5_HFLIP and MODE5_VFLIP turn it for
the other three.
"""

import os

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
SLED_ROW, FX_ROW, HOLO_ROW = 8, 6, 12

# The sled row, by index.
OUT, G0, TAIL, G1, Y1, G2, RED, G3, ORANGE, Y2, Y3, Y4, Y5, CREAM = range(1, 15)


def grid(w, h):
    return [[0] * w for _ in range(h)]


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


def cursor(n=11, size=12):
    """The top left corner of the cursor, size x size, in the holo row: a
    bright bracket whose arms fade out. It is drawn at 8 px below, and its
    lines are stretched along their length to n px across, each pixel the
    color at the same place along the line, so it keeps its fade and its
    taper, the inner line shorter than the outer."""
    shape = ['44444321',
             '4333210.',
             '43......',
             '42......',
             '31......',
             '21......',
             '1.......']
    g = [[0 if c == '.' else int(c) for c in line] for line in shape]
    lines = (([g[0][x] for x in range(8)], 0, 0, 0, 8),            # outer, across
             ([g[y][0] for y in range(7)], 0, 0, 1, 7),            # outer, down
             ([g[1][x] for x in range(1, 6)], 1, 1, 0, 5),         # inner, across
             ([g[y][1] for y in range(1, 6)], 1, 1, 1, 5))         # inner, down
    img = [[0] * size for _ in range(size)]
    for line, x, y, down, length in lines:
        stretched = round(n * length / 8)
        for s in range(stretched):
            c = line[s * len(line) // stretched]
            if down:
                img[y + s][x] = c
            else:
                img[y][x + s] = c
    return img


def strip(frames):
    return [[c for frame in frames for c in frame[y]] for y in range(len(frames[0]))]


def main():
    _, _, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    sled, fx, holo = palettes[SLED_ROW], palettes[FX_ROW], palettes[HOLO_ROW]
    for name, rows, colors in (
        ('machine', machine(), sled),
        ('digits', strip([digit(c) for c in '0123456789']), sled), ('energy', gauge(), fx),
        ('cursor', cursor(), holo),
    ):
        write_png(os.path.join(HERE, f'{name}.png'), len(rows[0]), len(rows), 3, rows, colors)


if __name__ == '__main__':
    main()
