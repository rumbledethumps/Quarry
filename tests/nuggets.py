#!/usr/bin/env python3
"""Checks broken bricks turning into nuggets that fly to the left panel.

  nuggets.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Reads the sprites and the
text from XRAM. Checks the chunks a brick breaks into, that each nugget
flies a straight line to its line in the panel, the count there, which
shows once the first nugget lands, and that the count lasts from level to
level. Exits 0 when every check passes.
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
    # The gray nugget's line is under the coins' line.
    BRICKS_Y, ICON_X, ICON_Y = sym['TUNE_BRICKS_Y'], sym['ICON_X'], sym['ICON_TOP'] + sym['LINE_H']
    TO_X = sym['NUGGET_TO_X']  # where a nugget lands, in the middle of its icon
    count = lambda: game.count('XRAM_NUGGET_DIGITS', sym['COUNT_DIGITS'])
    BRICKS = sym['LEVEL1_COLS'] * sym['LEVEL1_ROWS']
    HIDDEN_Y = sym['SPRITE_HIDDEN_Y']
    NUGGETS = sym['NUGGETS_MAX']  # in flight at once
    CHUNKS, PER_BREAK = sym['CHUNKS_MAX'], sym['CHUNKS_PER_BREAK']
    game.new_game()
    game.run(5)

    check(game.shown('XRAM_COIN_ICON', 1) == 0 and game.shown('XRAM_NUGGET_ICONS', sym['BRICK_COLORS']) == 0,
          'no line of the counts shows yet, not even the coins')
    flights, bricks, chunks = sym['XRAM_NUGGET_SPRITES'], sym['XRAM_BRICKS'], sym['XRAM_CHUNK_SPRITES']
    check(game.ram('nuggets', 2) == 0, 'no nuggets at the start')

    # A brick breaks: it is gone at once, in gray chunks that fly up and out
    # and fall, and a nugget flies from where it was.
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.wait('brick', 300)
    game.run(1)
    broken = [i for i, (_, y, _) in enumerate(game.sprites(bricks, BRICKS)) if y == HIDDEN_Y]
    check(broken, 'a broken brick is gone at once')
    where = lambda i: (game.ram(f'brick_x+{2 * i}', 2), game.ram(f'brick_y+{2 * i}', 2))
    bx, by = where(broken[0])
    middles = [where(i)[0] + sym['NUGGET_LEFT'] for i in broken]
    pieces = [(x, y) for x, y, _ in game.sprites(chunks, CHUNKS) if y != HIDDEN_Y]
    check(len(pieces) == PER_BREAK * len(broken), f'it breaks into {PER_BREAK} chunks: {pieces}')
    _, _, _, chunk_palette, _, mode = struct.unpack('<hhHHBB', game.xram(chunks, sym['SPRITE_BYTES']))
    check(chunk_palette == sym['XRAM_PALETTE_BRICKS'] and mode & 3 == sym['MODE5_2BPP'],
          'in the 2-bit colors of a gray brick')
    shot = os.path.join(tempfile.mkdtemp(), 'shot.png')
    paths, lit, falls = {}, [], []
    in_flight_count = None
    for frame in range(120):
        flying = [(slot, nx, ny) for slot, (nx, ny, _) in enumerate(game.sprites(flights, NUGGETS))
                  if ny != HIDDEN_Y]
        for slot, nx, ny in flying:
            paths.setdefault(slot, []).append((nx, ny))
        falls.append(game.sprite(chunks)[1])
        if frame < 3:
            # What the screen shows where the brick was: its nugget and its
            # chunks, never the bare floor.
            rows = game.screen(shot)
            floor = rows[150][160]
            lit.append(sum(rows[yy][xx] != floor
                           for yy in range(by, by + sym['BRICK_H']) for xx in range(bx, bx + sym['BRICK_W'])))
        if len(flying) == len(broken) and in_flight_count is None:
            in_flight_count = game.ram('nuggets', 2)
        if game.ram('nuggets', 2) >= len(broken) and frame > sym['CHUNK_STEPS']:
            break
        game.run(1)
    check(min(lit) > 0, f'a nugget takes the place of its brick with no empty frame between: {lit}')
    check(in_flight_count == 0, 'nothing counts while the nuggets are still in flight')
    check(max(y for y in falls if y != HIDDEN_Y) > by + sym['BRICK_H'] and game.shown(chunks, CHUNKS) == 0,
          'the chunks fall, and are gone in time')
    check(paths, 'a nugget flew')
    for slot, path in paths.items():
        x0, y0 = path[0]
        # It may have taken its first step by the first frame it is seen.
        check(any(abs(x0 - m) <= step for m in middles) and
              BRICKS_Y - step <= y0 < BRICKS_Y + sym['LEVEL1_ROWS'] * (sym['BRICK_H'] + sym['LEVEL1_GAP']),
              f'nugget {slot} starts in the middle of a broken brick, at {x0},{y0}')
        for (ax, ay), (cx, cy) in zip(path, path[1:]):
            check(max(abs(cx - ax), abs(cy - ay)) == step,
                  f'nugget {slot} moves {step} px a step, from {ax},{ay} to {cx},{cy}')
            check(abs(cx - TO_X) <= abs(ax - TO_X) and abs(cy - ICON_Y) <= abs(ay - ICON_Y),
                  f'nugget {slot} heads for the panel')
        lx, ly = path[-1]
        check(max(abs(lx - TO_X), abs(ly - ICON_Y)) <= step,
              f'nugget {slot} reaches the panel before it counts, last seen at {lx},{ly}')
        worst = max(off_line(x0, y0, TO_X, ICON_Y, x, y) for x, y in path)
        check(worst < 1, f'nugget {slot} flies a straight line, {worst:.2f} px off it at worst')
        print(f'nugget {slot}: {len(path)} steps from {x0},{y0}, {worst:.2f} px off the line')
    game.run(2)
    landed = game.ram('nuggets', 2)
    check(landed == len(broken), f'each nugget that lands counts, {landed} of {len(broken)}')
    check(game.sprite('XRAM_NUGGET_ICONS') == (ICON_X, ICON_Y - 1) and count() == landed,
          'and its line of the counts shows them')
    check(game.shown('XRAM_COIN_ICON', 1) == 0, "the coins' line waits for the first clear")

    # The count lasts into the next level, and keeps counting there.
    game.wait('ball lost', 3000)
    game.paused_poke([('balls', 0, 1), ('ball_state', 1, 1)])
    game.wait('out of balls', 600)
    before = game.ram('nuggets', 2)
    game.menu_choose('REPLAY')
    game.run(5)
    check(game.ram('nuggets', 2) == before, 'the count lasts into the next level')
    check(count() == before, 'the count shows it')

    # The chunks' sprites go round, so a break with too few left after the
    # last takes the oldest, from the first.
    game.paused_poke([('chunk_next', CHUNKS - 2, 1)])
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.wait('brick', 600)
    game.run(1)
    shown = [y != HIDDEN_Y for _, y, _ in game.sprites(chunks, CHUNKS)]
    check(shown[-2:] == [True, True] and shown[:PER_BREAK - 2] == [True] * (PER_BREAK - 2),
          f'a break takes the last two sprites and the first {PER_BREAK - 2}')
    game.wait('nugget landed', 600)
    game.run(1)
    after = game.ram('nuggets', 2)
    check(after > before, 'and keeps counting')
    check(count() == after, 'the count shows the new count')
    print(f'counted {before} in the first level, {after} after a nugget in the next')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
