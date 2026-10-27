#!/usr/bin/env python3
"""Checks the energy bar and running out of energy, in the emulator.

  energy.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The energy is poked low
to skip ahead. Reads the colors of the bar and the smoke from screenshots,
and the flames and the tilt of the falling paddle from their sprites.
Exits 0 when every check passes.
"""

import os
import tempfile

from game import Game, check

# The colors of the fx palette, in art/palettes.png.
COLORS = {'full': (0xd9, 0xb9, 0x5e), 'low': (0xe0, 0x78, 0x2a), 'empty': (0x1d, 0x36, 0x4d)}
SMOKE = [(0x51, 0x5a, 0x62), (0x8c, 0x94, 0x9a)]


def nearest(rgb, palette):
    return min(palette, key=lambda k: sum((a - b) ** 2 for a, b in zip(rgb, palette[k])))


def bar(game, shot):
    """The segments of the bar, top to bottom, as 'full', 'low' or 'empty'."""
    sym = game.sym
    rows = game.screen(shot)
    x = game.sprite('XRAM_ENERGY_SPRITES')[0] + 14
    return [nearest(rows[sym['ENERGY_Y'] + sym['BAR_PIECE_H'] * (1 + i) + 1][x], COLORS)
            for i in range(sym['ENERGY_SEGMENTS'])]


def smoke_pixels(game, shot, x0, x1, y0, y1):
    rows = game.screen(shot)
    return sum(1 for y in range(y0, y1) for x in range(x0, x1)
               if any(sum(abs(a - b) for a, b in zip(rows[y][x], c)) < 24 for c in SMOKE))


def main():
    shot = os.path.join(tempfile.mkdtemp(), 'shot.png')
    game = Game()
    sym = game.sym
    bar_segments = sym['ENERGY_SEGMENTS']
    game.new_game()
    game.run(5)

    full = game.ram('energy', 2)
    check(full == sym['TUNE_ENERGY'], 'the energy starts full')
    check(bar(game, shot) == ['full'] * bar_segments, 'the bar starts full and yellow')
    x, y = game.px('paddle_x'), game.px('paddle_y')
    pieces, flames = 'XRAM_PADDLE_SPRITES', 'XRAM_FLAME_SPRITES'
    check(game.sprite(pieces) == (x, y), 'the paddle is where it is in RAM')
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

    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.run(60)
    drained = full - game.ram('energy', 2)
    drain = sym['TUNE_ENERGY_DRAIN']
    check(55 * drain <= drained <= 65 * drain,
          f'energy drains {drain} a step after the launch, drained {drained} in 60')
    print(f'drained {drained} in 60 steps after the launch')

    low = sym['TUNE_ENERGY_LOW']
    game.paused_poke([('energy', low + 20, 2)])
    game.wait('energy low', 30)
    game.run(2)
    segments = bar(game, shot)
    lit = -(-low // -(-full // bar_segments))
    check(segments == ['empty'] * (bar_segments - lit) + ['low'] * lit,
          f'a low bar has {lit} orange segments: {segments}')
    print(f'low bar: {segments.count("low")} orange segments')

    # Out of energy: the flames sputter and the player loses control.
    game.paused_poke([('energy', 30, 2)])
    game.wait('out of energy', 40)
    check(game.ram('paddle_state') == sym['PADDLE_SPUTTER'], 'the paddle sputters')
    x = game.px('paddle_x')
    game.cmd('press right')
    lit = 0
    for _ in range(20):
        game.run()
        lit += game.shown(flames, 2)
    game.cmd('release right')
    check(game.px('paddle_x') == x, 'the paddle does not move while it sputters')
    check(0 < lit < 40, f'the flames flicker while they sputter, lit {lit} of 40')
    check(bar(game, shot) == ['empty'] * bar_segments, 'the bar is empty')

    # A puff of smoke, and the paddle falls and tilts.
    game.wait('paddle falls', sym['TUNE_SPUTTER_STEPS'])
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
    check(game.ram('game_state') != sym['STATE_PLAY'], 'the stage ends')
    check(game.shows('OUT OF ENERGY'), 'out of energy is shown')
    print(f'puff of {puff} smoke pixels, then the paddle fell off the screen')

    # Play plays again, with a full bar.
    game.menu_choose('PLAY')
    game.run(5)
    check(game.ram('energy', 2) == full, 'the energy is full again')
    check(game.ram('energy_draining') == 0, 'it waits for the first launch again')
    check(game.ram('paddle_state') == sym['PADDLE_HOVER'], 'the paddle hovers again')
    check(bar(game, shot) == ['full'] * bar_segments, 'the bar is full again')

    # Out of energy with the ball on the paddle: the ball goes down with it,
    # and launch does nothing.
    game.paused_poke([('energy', 10, 2), ('energy_draining', 1, 1)])
    game.wait('out of energy', 20)
    game.cmd('press space')
    game.run(4)
    game.cmd('release space')
    check(game.ram('balls') == sym['TUNE_BALLS'], 'no launch once out of energy')
    game.wait('paddle falls', sym['TUNE_SPUTTER_STEPS'])
    ball = 'XRAM_BALL_SPRITE'
    game.run(15)
    middle = game.sprites(pieces, 2)[1][1]
    check(game.sprite(ball)[1] == middle - 8, 'the ball rides the middle of the tilted paddle')
    game.wait('paddle gone', 120)
    game.run(2)
    check(game.shows('OUT OF ENERGY'), 'out of energy is shown again')

    # The stage clears while the paddle falls: it still falls off the screen.
    game.menu_choose('PLAY')
    game.run(5)
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.paused_poke([('energy', 5, 2)])
    game.wait('paddle falls', sym['TUNE_SPUTTER_STEPS'] + 10)
    check(game.ram('ball_state') == sym['BALL_FLYING'], 'the ball is still in flight')
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
