#!/usr/bin/env python3
"""Checks the energy bar and running out of energy, in the emulator.

  energy.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The energy is poked low
to skip ahead. Reads the colors of the bar and the smoke from screenshots,
and the flames and the tilt of the falling paddle from their sprites.
Exits 0 when every check passes.
"""

import os
import re
import sys
import tempfile

from game import STATE_PLAY, Game, check

# Where the bar is drawn, from src/play.c and src/energy.c.
BAR_X, BAR_Y, SEGMENTS, PIECE_H = 270, 26, 12, 4
COLORS = {'full': (0xd9, 0xb9, 0x5e), 'low': (0xe0, 0x78, 0x2a), 'empty': (0x1d, 0x36, 0x4d)}
SMOKE = [(0x51, 0x5a, 0x62), (0x8c, 0x94, 0x9a)]


def tuning():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'tuning.h')
    return {m.group(1): int(m.group(2)) for m in
            re.finditer(r'#define (TUNE_\w+) (\d+)', open(path).read())}


def nearest(rgb, palette):
    return min(palette, key=lambda k: sum((a - b) ** 2 for a, b in zip(rgb, palette[k])))


def bar(game, shot):
    """The segments of the bar, top to bottom, as 'full', 'low' or 'empty'."""
    rows = game.screen(shot)
    x = BAR_X + 14
    return [nearest(rows[BAR_Y + PIECE_H * (1 + i) + 1][x], COLORS) for i in range(SEGMENTS)]


def smoke_pixels(game, shot, x0, x1, y0, y1):
    rows = game.screen(shot)
    return sum(1 for y in range(y0, y1) for x in range(x0, x1)
               if any(sum(abs(a - b) for a, b in zip(rows[y][x], c)) < 24 for c in SMOKE))


def main():
    rom = sys.argv[1]
    tune = tuning()
    shot = os.path.join(tempfile.mkdtemp(), 'shot.png')
    game = Game(rom)
    game.new_game()
    game.run(5)

    full = game.ram('energy', 2)
    check(full == tune['TUNE_ENERGY'], 'the energy starts full')
    check(bar(game, shot) == ['full'] * SEGMENTS, 'the bar starts full and yellow')
    x, y = game.px('paddle_x'), game.px('paddle_y')
    pieces = game.sprite_at(x, y)
    flames = game.sprite_at(x, y + 8)
    images = set()
    for _ in range(30):
        game.run()
        left, right = game.sprites(flames, 2)
        check(left[1] == right[1] == y + 8, 'both flames burn under the paddle')
        images.add(left[2])
        images.add(right[2])
    check(len(images) == 3, f'the flames burn through 3 frames, saw {len(images)}')
    game.run(90)
    check(game.ram('energy', 2) == full, 'no energy drains before the first launch')

    game.send('press space')
    game.wait('launch', 5)
    game.send('release space')
    game.run(60)
    drained = full - game.ram('energy', 2)
    drain = tune['TUNE_ENERGY_DRAIN']
    check(55 * drain <= drained <= 65 * drain,
          f'energy drains {drain} a step after the launch, drained {drained} in 60')
    print(f'drained {drained} in 60 steps after the launch')

    low = tune['TUNE_ENERGY_LOW']
    game.paused_poke([('energy', low + 20, 2)])
    game.wait('energy low', 30)
    game.run(2)
    segments = bar(game, shot)
    lit = -(-low // -(-full // SEGMENTS))
    check(segments == ['empty'] * (SEGMENTS - lit) + ['low'] * lit,
          f'a low bar has {lit} orange segments: {segments}')
    print(f'low bar: {segments.count("low")} orange segments')

    # Out of energy: the flames sputter and the player loses control.
    game.paused_poke([('energy', 30, 2)])
    game.wait('out of energy', 40)
    check(game.ram('paddle_state') == 1, 'the paddle sputters')
    x = game.px('paddle_x')
    game.send('press right')
    lit = 0
    for _ in range(20):
        game.run()
        lit += sum(fy != -64 for _, fy, _ in game.sprites(flames, 2))
    game.send('release right')
    check(game.px('paddle_x') == x, 'the paddle does not move while it sputters')
    check(0 < lit < 40, f'the flames flicker while they sputter, lit {lit} of 40')
    check(bar(game, shot) == ['empty'] * SEGMENTS, 'the bar is empty')

    # A puff of smoke, and the paddle falls and tilts.
    game.wait('paddle falls', tune['TUNE_SPUTTER_STEPS'])
    top = game.px('paddle_y')
    game.run(6)
    puff = smoke_pixels(game, shot, x - 4, x + 32, top - 8, top + 16)
    check(puff > 10, f'a puff of smoke where the paddle gave up, {puff} pixels')
    game.run(10)
    ys = [py for _, py, _ in game.sprites(pieces, 3)]
    check(ys[0] < ys[1] < ys[2], f'the falling paddle tilts, the right end lower: {ys}')
    check(game.shown(flames, 2) == 0, 'no flames on a falling paddle')
    check(game.px('paddle_y') > top + 4, 'the paddle falls')
    game.wait('paddle gone', 120)
    game.run(2)
    check(game.ram('game_state') != STATE_PLAY, 'the stage ends')
    check(game.shows('OUT OF ENERGY'), 'out of energy is shown')
    print(f'puff of {puff} smoke pixels, then the paddle fell off the screen')

    # Play plays again, with a full bar.
    game.menu_choose('PLAY')
    game.run(5)
    check(game.ram('energy', 2) == full, 'the energy is full again')
    check(game.ram('energy_draining') == 0, 'it waits for the first launch again')
    check(game.ram('paddle_state') == 0, 'the paddle hovers again')
    check(bar(game, shot) == ['full'] * SEGMENTS, 'the bar is full again')

    # Out of energy with the ball on the paddle: the ball goes down with it,
    # and launch does nothing.
    game.paused_poke([('energy', 10, 2), ('energy_draining', 1, 1)])
    game.wait('out of energy', 20)
    game.send('press space')
    game.run(4)
    game.send('release space')
    check(game.ram('balls') == 5, 'no launch once out of energy')
    game.wait('paddle falls', tune['TUNE_SPUTTER_STEPS'])
    ball = game.sprite_at(game.px('ball_x'), game.px('ball_y'))
    game.run(15)
    middle = game.sprites(pieces, 2)[1][1]
    check(game.sprite(ball)[1] == middle - 8, 'the ball rides the middle of the tilted paddle')
    game.wait('paddle gone', 120)
    game.run(2)
    check(game.shows('OUT OF ENERGY'), 'out of energy is shown again')

    # The stage clears while the paddle falls: it still falls off the screen.
    game.menu_choose('PLAY')
    game.run(5)
    game.send('press space')
    game.wait('launch', 5)
    game.send('release space')
    game.paused_poke([('energy', 5, 2)])
    game.wait('paddle falls', tune['TUNE_SPUTTER_STEPS'] + 10)
    check(game.ram('ball_state') == 1, 'the ball is still in flight')
    game.paused_poke([('bricks_left', 0, 1)])
    game.wait('stage cleared', 5)
    game.wait('paddle gone', 120)
    game.run(2)
    check(game.shown(pieces, 3) == 0, 'the paddle fell off after the stage cleared')
    check(game.shows('STAGE CLEAR'), 'stage clear is shown')
    print('cleared while falling: the paddle still fell off the screen')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
