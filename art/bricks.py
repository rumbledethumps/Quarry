#!/usr/bin/env python3
"""Draw the bricks, their cracks and chunks, the nuggets and the coin.

  bricks.py

Writes the ball's row and the brick rows of art/palettes.png, and
art/brick.png, art/cracks.png, art/chunks.png, art/nugget.png,
art/nugget-icon.png, art/coin.png, art/ball.png and art/ball-icon.png. Run it
after a change to the drawing here. Every piece is drawn here, by rule, and
nothing is touched up by hand.

The bricks are plain colors, in the order of COLORS, picked to be told
apart with any kind of color blindness and to stay clear of the white
ball. Each color is a row of art/palettes.png, which every piece but the
coin shares, so one image of each serves every color:

  1 to 3   the brick's light, face and dark, for the brick and its chunks
  4 to 6   the nugget's outline, its deep shadow and its highlight
  8 to 11  the cracks' clear, black, lip and the brick's dark: a crack
           sprite's palette starts at 8, BRICK_CRACK_COLORS of src/xram.h

A brick is 24x8, 2 bits a pixel, with no gap of its own: a 1 px bevel all
round, lit from the upper left. Its cracks are sprites over it, 16x8 at 2
bits, in CRACK_SETS sets of CRACK_STATES, a state for each step of a brick
more broken, each the last with more: a crack starts at an edge, through
its bevel, FIRST_PIXELS long, and grows wider and deeper with each state,
to reach the other edge at the last, and a second beside it starts once
the brick is SECOND_CRACK broken and grows faster, to reach the other
edge at the last too: from the same edge in half the sets, and from the
opposite one in the rest. They are black with a gray lip where the light
catches the edge under them, and the game flips them either way.
The chunks are 8x8 at 2 bits, CHUNKS of them, rough lumps of the brick's
colors that fly when it breaks. The nugget is a sphere 7 px across, with
an outline, as it flies, and 10 px across beside its count, as tall as
the outlined digits, and the coin is the same big circle in the gold of
the sled row, beveled, with a hole in the middle, square or diamond, as
HOLE says. The ball is a sphere as the nuggets are, a very bright white,
8 px across as it is in play and as big as the digits by its count.
"""

import math
import os
import random

from rd2png import rgba, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
BALL_ROW = 0   # the main row of art/palettes.png, the ball's
BRICK_ROW = 1  # the first brick row
SLED_ROW = 8   # the sled row, which the coin uses

# The colors of the bricks, in the order of BRICK_GRAY and on in
# src/bricks.h.
COLORS = [(180, 180, 180), (235, 105, 121), (24, 137, 47), (44, 172, 255), (207, 187, 22)]
OUTLINE = (16, 19, 28)  # near-black navy, the sled row's outline
CRACK, LIP = (34, 34, 40), (150, 150, 158)

W, H = 24, 8
CRACK_W = 16
CRACK_SETS = 6
CRACK_STATES = 10
SECOND_CRACK = 0.41  # how broken a brick is when its second crack starts: 59% left
CRACK_SEED = 2  # picks the cracks' shapes, all their sets at once
CHUNKS = 16
ICON_D, ICON_SIZE = 10, 12  # the icons of the counts, as tall as the outlined digits
HOLE = 'square'  # or 'diamond'

# The brick row, by index.
LIGHT, FACE, DARK, EDGE, DEEP, SHINE = range(1, 7)

# The ball's row: a sphere shaded as the nuggets are, but a very bright
# white, by the same indexes.
BALL = {SHINE: (255, 255, 255), LIGHT: (246, 246, 250), FACE: (226, 228, 234), DARK: (170, 174, 186),
        DEEP: (118, 124, 140), EDGE: OUTLINE}
CRACK_COLORS = 8
SPLIT, LIPPED = 1, 2  # in a crack image, as the palette from CRACK_COLORS

# The sled row, by index, for the coin.
OUT, Y1, Y2, Y3, Y4, Y5 = 1, 5, 10, 11, 12, 13


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def palette(color):
    """The 16 colors of a brick's row."""
    row = [(0, 0, 0, 0)] * 16
    shades = {LIGHT: mix(color, (255, 255, 255), 0.45), FACE: color, DARK: mix(color, (0, 0, 0), 0.45),
              EDGE: OUTLINE, DEEP: mix(color, (0, 0, 0), 0.7), SHINE: mix(color, (255, 255, 255), 0.8),
              CRACK_COLORS + SPLIT: CRACK, CRACK_COLORS + LIPPED: LIP,
              CRACK_COLORS + 3: mix(color, (0, 0, 0), 0.45)}
    for i, c in shades.items():
        row[i] = c + (255,)
    return row


def brick():
    """The bevel: light along the top and the left, dark along the bottom
    and the right, and the face where the two meet at the corners."""
    img = [[FACE] * W for _ in range(H)]
    for x in range(W):
        img[0][x], img[H - 1][x] = LIGHT, DARK
    for y in range(H):
        img[y][0], img[y][W - 1] = LIGHT, DARK
    img[0][W - 1] = img[H - 1][0] = FACE
    return img


def crack(rng, left, right, down):
    """A crack within columns left to right, its pixels in the order it
    grows: from the top edge down to the bottom, or the bottom up to the
    top, through both bevels, wandering across, and now and then a step
    sideways, with a short branch off it here and there, each coming a
    little after the crack has passed it, and its mouth at the edge it
    started from opening as it goes, to 3 wide."""
    x, dy = rng.randint(left, right), 1 if down else -1
    y = 0 if down else H - 1
    keyed = [(0, (x, y))]
    while 0 < y + dy < H - 1 or y + dy in (0, H - 1):
        x = max(left, min(right, x + rng.choice((-1, 0, 0, 1))))
        y += dy
        keyed.append((len(keyed), (x, y)))
        if y in (0, H - 1):
            break
        if rng.random() < 0.3:
            x = max(left, min(right, x + rng.choice((-1, 1))))
            keyed.append((len(keyed), (x, y)))
    path = len(keyed)
    for at in (path // 3, 2 * path // 3):
        bx, by = keyed[at][1]
        side = rng.choice((-1, 1))
        for j, (px, py) in enumerate(((bx + side, by + dy), (bx + 2 * side, by + dy))):
            if 0 < px < CRACK_W - 1 and 0 < py < H - 1:
                keyed.append((at + 1.5 + j, (px, py)))
    # Its mouth, where it started, opens as it grows: a pixel to one side
    # of where it started, then one beside it a row in, then one to the
    # other side, 3 wide at the edge by the end.
    (mx, my), (nx, ny) = keyed[0][1], keyed[1][1]
    side = rng.choice((-1, 1))
    for when, (px, py) in ((0.35, (mx + side, my)), (0.6, (nx + side, ny)), (0.85, (mx - side, my))):
        if 0 < px < CRACK_W - 1:
            keyed.append((when * path, (px, py)))
    order = []
    for _, p in sorted(keyed, key=lambda kp: kp[0]):
        if p not in order:
            order.append(p)
    return order


FIRST_PIXELS = 3  # of a crack, the state it shows


def grown(order, state, states):
    """The pixels of a crack at its state, from 1 to its states: its first
    FIRST_PIXELS at once, then the rest by even steps, all of it at the
    last."""
    if state < 1:
        return []
    return order[:FIRST_PIXELS + math.ceil((state - 1) * (len(order) - FIRST_PIXELS) / max(1, states - 1))]


def crack_set(seed):
    """The CRACK_STATES states of a set, a brick more and more broken: one
    crack starts at an edge at the first state, and grows to the other
    edge, wider and deeper, by the last; a second, beside it, starts at the
    state that holds SECOND_CRACK broken, and grows faster, to reach the
    other edge at the last too. In the first half of the sets they start
    from the same edge, and in the rest from opposite edges. Each is black,
    with a gray lip under it where the light catches the edge. A crack too
    short to grow with every state is drawn again."""
    rng = random.Random(CRACK_SEED * 1000 + seed)
    begins = math.ceil(CRACK_STATES * SECOND_CRACK)
    opposite = seed >= CRACK_SETS // 2
    later = CRACK_STATES - begins + 1
    first = second = []
    while len(first) < FIRST_PIXELS + CRACK_STATES - 1:
        first = crack(rng, 3, 6, True)
    while len(second) < FIRST_PIXELS + later - 1:
        second = crack(rng, 9, 12, not opposite)
    states = []
    for state in range(1, CRACK_STATES + 1):
        img = [[0] * CRACK_W for _ in range(H)]
        cracks = grown(first, state, CRACK_STATES) + grown(second, state - begins + 1, later)
        for x, y in cracks:
            img[y][x] = SPLIT
        for x, y in cracks:
            if 0 < y + 1 < H - 1 and not img[y + 1][x]:
                img[y + 1][x] = LIPPED
        states.append(img)
    return states


def chunk(seed):
    """A rough lump, its edges lit like the brick: light where the top or
    the left is open, dark where the bottom or the right is."""
    rng = random.Random(1000 + seed)
    size = rng.uniform(2.3, 3.5)
    sides = rng.randint(5, 7)
    turn = rng.uniform(0, math.tau)
    corners = []
    for k in range(sides):
        a = turn + k * math.tau / sides + rng.uniform(-0.3, 0.3)
        r = size * rng.uniform(0.6, 1.0)
        corners.append((3.5 + r * math.cos(a), 3.5 + r * math.sin(a)))

    def inside(px, py):
        hit = False
        for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
            if (y0 > py) != (y1 > py) and px < x0 + (py - y0) * (x1 - x0) / (y1 - y0):
                hit = not hit
        return hit

    solid = [[inside(x + 0.5, y + 0.5) for x in range(8)] for y in range(8)]
    at = lambda x, y: 0 <= x < 8 and 0 <= y < 8 and solid[y][x]
    img = [[0] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            if solid[y][x]:
                if not at(x, y + 1) or not at(x + 1, y):
                    img[y][x] = DARK
                elif not at(x, y - 1) or not at(x - 1, y):
                    img[y][x] = LIGHT
                else:
                    img[y][x] = FACE
    return img


def circle(d, size, round_off=0.2):
    """The pixels of a circle d across, at the top left of a sprite size
    square, and where its middle is: the inside, and the ring of its edge,
    the pixels with a side open. Its radius is round_off less than half of
    d, which rounds the pixels of its edge best for each d."""
    mid = d / 2
    solid = {(x, y) for y in range(size) for x in range(size)
             if (x + 0.5 - mid) ** 2 + (y + 0.5 - mid) ** 2 <= (mid - round_off) ** 2}
    edge = {(x, y) for x, y in solid
            if any((x + ax, y + ay) not in solid for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    return solid - edge, edge, mid - 0.5


def nugget(d=7, size=8, round_off=0.2):
    """A sphere lit from the upper left, in the brick row's shades: 7
    across as it flies, and as big as the digits beside its count. The
    ball is the same, in its own row."""
    inside, edge, mid = circle(d, size, round_off)
    img = [[0] * size for _ in range(size)]
    light = (-0.55, -0.6, 0.58)
    for x, y in edge:
        img[y][x] = EDGE
    for x, y in inside:
        nx, ny = (x - mid) / mid, (y - mid) / mid
        nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
        lit = nx * light[0] + ny * light[1] + nz * light[2]
        img[y][x] = SHINE if lit > 0.95 else LIGHT if lit > 0.75 else FACE if lit > 0.4 else DARK if lit > 0.1 else DEEP
    return img


def coin(d=ICON_D, size=ICON_SIZE):
    """The same circle, as big as the digits, beveled: its rim lit on the
    upper left and shaded on the lower right, and the hole in the middle
    the other way round, as it is cut in. The hole is clear, inside an
    outline of its own."""
    inside, edge, mid = circle(d, size)
    img = [[0] * size for _ in range(size)]
    for x, y in edge:
        img[y][x] = OUT
    half = d / 5
    hole = {(x, y) for x, y in inside
            if (max(abs(x - mid), abs(y - mid)) if HOLE == 'square' else abs(x - mid) + abs(y - mid)) <= half}
    near = lambda x, y, ring: any((x + ax, y + ay) in ring for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    for x, y in hole:
        if any((x + ax, y + ay) not in hole for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            img[y][x] = OUT  # the hole is outlined, as the coin is
    for x, y in inside - hole:
        toward = (x - mid) + (y - mid)  # below 0 faces the light
        if near(x, y, edge):
            img[y][x] = Y4 if toward < 0 else Y1 if toward > 0 else Y3
        elif near(x, y, hole):
            img[y][x] = Y1 if toward < 0 else Y5 if toward > 0 else Y2
        else:
            img[y][x] = Y3
    return img


def sheet(images, across):
    """Images side by side, across to a row, and rows down."""
    w, h = len(images[0][0]), len(images[0])
    rows = []
    for top in range(0, len(images), across):
        for y in range(h):
            rows.append([c for img in images[top:top + across] for c in img[y]] +
                        [0] * (w * (across - len(images[top:top + across]))))
    return rows


def main():
    _, count, palettes = rgba(os.path.join(HERE, 'palettes.png'))
    rows = [palette(c) for c in COLORS]
    palettes[BRICK_ROW:BRICK_ROW + len(COLORS)] = rows
    palettes[BALL_ROW] = [BALL[i] + (255,) if i in BALL else (0, 0, 0, 0) for i in range(16)]
    write_png(os.path.join(HERE, 'palettes.png'), 16, count, 6,
              [[v for c in row for v in c] for row in palettes])
    gray = rows[0]
    cracks = [img for s in range(CRACK_SETS) for img in crack_set(s)]
    crack_colors = gray[CRACK_COLORS:CRACK_COLORS + 4] + [(0, 0, 0, 0)] * 12
    for name, img, colors in (('brick', brick(), gray), ('cracks', sheet(cracks, CRACK_STATES), crack_colors),
                              ('chunks', sheet([chunk(i) for i in range(CHUNKS)], CHUNKS), gray),
                              ('nugget', nugget(), gray), ('nugget-icon', nugget(ICON_D, ICON_SIZE), gray),
                              ('coin', coin(), palettes[SLED_ROW]),
                              ('ball', nugget(8, 8, 0), palettes[BALL_ROW]),
                              ('ball-icon', nugget(ICON_D, ICON_SIZE), palettes[BALL_ROW])):
        write_png(os.path.join(HERE, f'{name}.png'), len(img[0]), len(img), 3, img, colors)


if __name__ == '__main__':
    main()
