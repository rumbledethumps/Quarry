#!/usr/bin/env python3
"""Checks broken bricks turning into nuggets that fly to the left panel.

  nuggets.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Reads the sprites and the
text from XRAM. Breaks the lowest brick of level 1, whatever the level is
like, by putting the ball in flight under it. Checks the chunks a brick
breaks into, that each nugget flies a straight line to its color's line in
the panel, the count there, which shows once the first nugget lands, and
that the count lasts from level to level. Exits 0 when every check passes.
"""

import os
import struct
import tempfile

from game import Game, check


def off_line(x0, y0, x1, y1, x, y):
    """How far x, y is from the line through x0, y0 and x1, y1, in pixels."""
    dx, dy = x1 - x0, y1 - y0
    return abs(dy * (x - x0) - dx * (y - y0)) / max(1, (dx * dx + dy * dy) ** 0.5)


def main():
    game = Game()
    sym = game.sym
    step = sym['TUNE_NUGGET_SPEED']
    icon = lambda c: sym['XRAM_NUGGET_ICONS'] + c * sym['SPRITE_BYTES']
    TO_X = sym['NUGGET_TO_X']  # where a nugget lands, in the middle of its icon
    count = lambda c: game.count(sym['XRAM_NUGGET_DIGITS'] + c * sym['COUNT_DIGITS'] * sym['SPRITE_BYTES'],
                                 sym['COUNT_DIGITS'])
    have = lambda c: game.ram(f'nuggets+{2 * c}', 2)
    COLORS = range(sym['BRICK_COLORS'])
    BRICKS, BRICK_W, BRICK_H, BALL = sym['LEVEL1_BRICKS'], sym['BRICK_W'], sym['BRICK_H'], sym['BALL_SIZE']
    HIDDEN_Y = sym['SPRITE_HIDDEN_Y']
    NUGGETS = sym['NUGGETS_MAX']  # in flight at once
    CHUNKS, PER_BREAK = sym['CHUNKS_MAX'], sym['CHUNKS_PER_BREAK']
    flights, bricks, chunks = sym['XRAM_NUGGET_SPRITES'], sym['XRAM_BRICKS'], sym['XRAM_CHUNK_SPRITES']
    where = lambda i: (game.ram(f'brick_x+{2 * i}', 2), game.ram(f'brick_y+{2 * i}', 2))
    lowest = lambda: max(range(BRICKS), key=lambda i: where(i)[1])

    def break_brick(i, pokes=()):
        """Breaks brick i, the lowest, with nothing under it: the ball is put
        in flight a brick's height below it, rising a quarter px a step, the
        brick takes one hit to break, and the sled goes to the wall away from
        the ball, so the ball, falling as slowly after, breaks nothing else."""
        x, y = where(i)
        x += (BRICK_W - BALL) // 2
        left, right = game.ram('play_left', 2, signed=True), game.ram('play_right', 2, signed=True)
        sled = left if x - left > right - x else right - game.ram('paddle_width')
        game.paused_poke([('ball_state', sym['BALL_FLYING'], 1), ('ball_x', x << 8, 4),
                          ('ball_y', y + 2 * BRICK_H << 8, 4), ('ball_vx', 0, 2), ('ball_vy', -64, 2),
                          (f'brick_hits+{i}', 1, 1), ('paddle_x', sled << 8, 4), *pokes])
        game.wait('brick', 120)
        game.run(1)

    game.new_game()
    game.run(5)

    check(game.shown('XRAM_COIN_ICON', 1) == 0 and game.shown(icon(0), len(COLORS)) == 0,
          'no line of the counts shows yet, not even the coins')
    check(all(have(c) == 0 for c in COLORS), 'no nuggets at the start')

    # A brick breaks: it is gone at once, in chunks of its color that fly up
    # and out and fall, and a nugget flies from where it was. It is made the
    # last color, whatever the level's are, so its nugget has the farthest
    # line to reach.
    color = COLORS[-1]
    # Each color's line is under the coins' line, in the order of the colors.
    TO_Y = sym['ICON_TOP'] + (color + 1) * sym['LINE_H']
    i = lowest()
    break_brick(i, [(f'brick_color+{i}', color, 1)])
    broken = [j for j, (_, y, _) in enumerate(game.sprites(bricks, BRICKS)) if y == HIDDEN_Y]
    check(broken == [i], f'the brick is gone at once, and no other: {broken}')
    bx, by = where(i)
    sx, sy = bx + sym['NUGGET_LEFT'], by  # where its nugget starts
    pieces = [(x, y) for x, y, _ in game.sprites(chunks, CHUNKS) if y != HIDDEN_Y]
    check(len(pieces) == PER_BREAK, f'it breaks into {PER_BREAK} chunks: {pieces}')
    _, _, _, chunk_palette, _, mode = struct.unpack('<hhHHBB', game.xram(chunks, sym['SPRITE_BYTES']))
    # Each color's palette is 16 colors of 2 bytes, after the one before.
    check(chunk_palette == sym['XRAM_PALETTE_BRICKS'] + 32 * color and mode & 3 == sym['MODE5_2BPP'],
          'in the 2-bit colors of a brick of its color')
    shot = os.path.join(tempfile.mkdtemp(), 'shot.png')
    area = lambda rows: [rows[yy][xx] for yy in range(by, by + BRICK_H) for xx in range(bx, bx + BRICK_W)]
    paths, shots, falls = {}, [], []
    in_flight_count = None
    for frame in range(120):
        flying = [(slot, nx, ny) for slot, (nx, ny, _) in enumerate(game.sprites(flights, NUGGETS))
                  if ny != HIDDEN_Y]
        for slot, nx, ny in flying:
            paths.setdefault(slot, []).append((nx, ny))
        falls.append(game.sprite(chunks)[1])
        if frame < 3:
            shots.append(area(game.screen(shot)))
        if flying and in_flight_count is None:
            in_flight_count = have(color)
        if have(color) and frame > sym['CHUNK_STEPS']:
            break
        game.run(1)
    check(in_flight_count == 0, 'nothing counts while the nugget is still in flight')
    check(max(y for y in falls if y != HIDDEN_Y) > by + BRICK_H and game.shown(chunks, CHUNKS) == 0,
          'the chunks fall, and are gone in time')
    # What the screen shows where the brick was, in its first frames: its
    # nugget and its chunks, never the bare floor that shows there now.
    bare = area(game.screen(shot))
    lit = [sum(a != b for a, b in zip(s, bare)) for s in shots]
    check(min(lit) > 0, f'a nugget takes the place of its brick with no empty frame between: {lit}')
    check(len(paths) == 1, f'one nugget flew: {sorted(paths)}')
    for slot, path in paths.items():
        x0, y0 = path[0]
        # It may have taken its first step by the first frame it is seen.
        check(abs(x0 - sx) <= step and abs(y0 - sy) <= step,
              f'nugget {slot} starts in the middle of the broken brick, at {x0},{y0}, not {sx},{sy}')
        for (ax, ay), (cx, cy) in zip(path, path[1:]):
            check(max(abs(cx - ax), abs(cy - ay)) == step,
                  f'nugget {slot} moves {step} px a step, from {ax},{ay} to {cx},{cy}')
            check(abs(cx - TO_X) <= abs(ax - TO_X) and abs(cy - TO_Y) <= abs(ay - TO_Y),
                  f'nugget {slot} heads for its line of the panel')
        lx, ly = path[-1]
        check(max(abs(lx - TO_X), abs(ly - TO_Y)) <= step,
              f'nugget {slot} reaches its line before it counts, last seen at {lx},{ly}')
        worst = max(off_line(x0, y0, TO_X, TO_Y, x, y) for x, y in path)
        check(worst < 1, f'nugget {slot} flies a straight line, {worst:.2f} px off it at worst')
        print(f'nugget {slot}: {len(path)} steps from {x0},{y0}, {worst:.2f} px off the line')
    game.run(2)
    landed = have(color)
    check(landed == 1 and all(not have(c) for c in COLORS if c != color),
          f'the nugget that lands counts in its color, {landed}')
    check(game.sprite(icon(color)) == (sym['ICON_X'], TO_Y - 1) and count(color) == landed and
          game.shown(icon(0), len(COLORS)) == 1, 'and its line of the counts shows it, and no other line')
    check(game.shown('XRAM_COIN_ICON', 1) == 0, "the coins' line waits for the first clear")

    # The count lasts into the next level, and keeps counting there. With
    # the count of balls emptied, the ball sent off the bottom of the screen
    # is the last, and losing it ends the level.
    game.paused_poke([('balls', 0, 1), ('ball_y', sym['SCREEN_H'] - 1 << 8, 4), ('ball_vy', 600, 2)])
    game.wait('out of balls', 120)
    before = have(color)
    game.menu_choose('REPLAY')
    game.ready()
    check(have(color) == before, 'the count lasts into the next level')
    check(count(color) == before, 'the count shows it')

    # The chunks' sprites go round, so a break with too few left after the
    # last takes the oldest, from the first. The brick is its own color this
    # time, and its nugget counts in that color's line.
    i = lowest()
    mine = game.ram(f'brick_color+{i}')
    kept = have(mine)
    break_brick(i, [('chunk_next', CHUNKS - 2, 1)])
    shown = [y != HIDDEN_Y for _, y, _ in game.sprites(chunks, CHUNKS)]
    check(shown[-2:] == [True, True] and shown[:PER_BREAK - 2] == [True] * (PER_BREAK - 2),
          f'a break takes the last two sprites and the first {PER_BREAK - 2}')
    game.wait('nugget landed', 600)
    game.run(1)
    after = have(mine)
    check(after == kept + 1, 'and keeps counting')
    check(count(mine) == after, 'the count shows the new count')
    print(f'counted {before} of color {color} in the first level, then {after} of color {mine} in the next')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
