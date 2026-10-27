#!/usr/bin/env python3
"""Checks broken bricks turning into nuggets that fly to the left panel.

  nuggets.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Reads the sprites and the
text from XRAM. Checks the break frames, that each nugget flies a straight
line to its line in the panel, the count there, and that the count lasts
from stage to stage. Exits 0 when every check passes.
"""

import os
import tempfile

from game import SPRITE, Game, check

ICON_Y = 16  # the white line of the panel, from src/nuggets.c
COUNT_ROW = 2
BREAK_SIZE = 0x35  # MODE5_SIZE(24, 16)


def off_line(x0, y0, x1, y1, x, y):
    """How far x, y is from the line through x0, y0 and x1, y1, in pixels."""
    dx, dy = x1 - x0, y1 - y0
    return abs(dy * (x - x0) - dx * (y - y0)) / max(1, (dx * dx + dy * dy) ** 0.5)


def main():
    game = Game()
    sym = game.sym
    step = sym['TUNE_NUGGET_SPEED']
    BRICKS_Y, ICON_X, COUNT_COL = sym['TUNE_BRICKS_Y'], sym['ICON_X'], sym['COUNT_COL']
    BRICKS = sym['STAGE1_COLS'] * sym['STAGE1_ROWS']
    HIDDEN_Y = sym['SPRITE_HIDDEN_Y']
    NUGGETS = sym['NUGGETS_MAX']  # in flight at once
    game.new_game()
    game.run(5)

    check(game.text(32, 2, 6) == 'ENERGY', 'the right panel is up')
    check(game.sprite('XRAM_NUGGET_ICONS') == (ICON_X, ICON_Y), 'the nugget icon is in the panel')
    flights = sym['XRAM_NUGGET_SPRITES']
    bricks = sym['XRAM_BRICKS']
    check(game.ram('nuggets', 2) == 0, 'no nuggets at the start')
    check(game.text(COUNT_COL, COUNT_ROW, 5) == '0    ', 'the panel shows 0')

    # A brick breaks: its sprite shows two break frames, then it is gone and
    # a nugget flies from where it was.
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.wait('brick', 300)
    game.run(1)
    sizes = game.sizes(bricks, BRICKS)
    broken = [i for i, s in enumerate(sizes) if s == BREAK_SIZE]
    check(broken, 'a broken brick shows its break')
    first = bricks + broken[0] * SPRITE
    bx = game.sprites(first, 1)[0][0]
    middles = [game.sprites(bricks + i * SPRITE, 1)[0][0] + 8 for i in broken]
    by = game.sprites(first, 1)[0][1] + 4
    shot = os.path.join(tempfile.mkdtemp(), 'shot.png')
    images, paths, lit = [], {}, []
    in_flight_count = None
    for frame in range(120):
        x, y, image = game.sprites(first, 1)[0]
        if y != HIDDEN_Y and image not in images:
            images.append(image)
        flying = [(slot, nx, ny) for slot, (nx, ny, _) in enumerate(game.sprites(flights, NUGGETS))
                  if ny != HIDDEN_Y]
        for slot, nx, ny in flying:
            paths.setdefault(slot, []).append((nx, ny))
        if frame < 12:
            # What the screen shows where the brick was: its break, then
            # its nugget, never the bare floor between.
            rows = game.screen(shot)
            floor = rows[150][160]
            lit.append(sum(rows[yy][xx] != floor
                           for yy in range(by, by + 8) for xx in range(bx, bx + 24)))
        if len(flying) == len(broken) and in_flight_count is None:
            in_flight_count = game.ram('nuggets', 2)
        if game.ram('nuggets', 2) >= len(broken) and frame > 20:
            break
        game.run(1)
    check(min(lit) > 0, f'a nugget takes the place of its brick with no empty frame between: {lit}')
    check(in_flight_count == 0, 'nothing counts while the nuggets are still in flight')
    check(len(images) == 2, f'the break shows 2 frames, saw {len(images)}')
    check(game.sprites(first, 1)[0][1] == HIDDEN_Y, 'the broken brick is gone after its break')
    check(paths, 'a nugget flew')
    for slot, path in paths.items():
        x0, y0 = path[0]
        check(x0 in middles and BRICKS_Y <= y0 < BRICKS_Y + 5 * 8,
              f'nugget {slot} starts in the middle of a broken brick, at {x0},{y0}')
        for (ax, ay), (cx, cy) in zip(path, path[1:]):
            check(max(abs(cx - ax), abs(cy - ay)) == step,
                  f'nugget {slot} moves {step} px a step, from {ax},{ay} to {cx},{cy}')
            check(abs(cx - ICON_X) <= abs(ax - ICON_X) and abs(cy - ICON_Y) <= abs(ay - ICON_Y),
                  f'nugget {slot} heads for the panel')
        lx, ly = path[-1]
        check(max(abs(lx - ICON_X), abs(ly - ICON_Y)) <= step,
              f'nugget {slot} reaches the panel before it counts, last seen at {lx},{ly}')
        worst = max(off_line(x0, y0, ICON_X, ICON_Y, x, y) for x, y in path)
        check(worst < 1, f'nugget {slot} flies a straight line, {worst:.2f} px off it at worst')
        print(f'nugget {slot}: {len(path)} steps from {x0},{y0}, {worst:.2f} px off the line')
    game.run(2)
    landed = game.ram('nuggets', 2)
    check(landed == len(broken), f'each nugget that lands counts, {landed} of {len(broken)}')
    check(game.text(COUNT_COL, COUNT_ROW, 5) == f'{landed:<5}', 'the panel shows the count')

    # The count lasts into the next stage, and keeps counting there.
    game.wait('ball lost', 3000)
    game.paused_poke([('balls', 0, 1), ('ball_state', 1, 1)])
    game.wait('out of balls', 600)
    before = game.ram('nuggets', 2)
    game.menu_choose('PLAY')
    game.run(5)
    check(game.ram('nuggets', 2) == before, 'the count lasts into the next stage')
    check(game.text(COUNT_COL, COUNT_ROW, 5) == f'{before:<5}', 'the panel shows it')
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.wait('nugget landed', 600)
    game.run(1)
    after = game.ram('nuggets', 2)
    check(after > before, 'and keeps counting')
    check(game.text(COUNT_COL, COUNT_ROW, 5) == f'{after:<5}', 'the panel shows the new count')
    print(f'counted {before} in the first stage, {after} after a nugget in the next')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
