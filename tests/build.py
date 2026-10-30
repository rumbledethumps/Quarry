#!/usr/bin/env python3
"""Checks how a level builds up as it starts, in the emulator.

  build.py rom.rp6502

Needs a Debug ROM, which logs the game's events. A level opens empty,
under the dwarf's welcome, and builds up as he goes: the sled rises into
place, the bricks are laid bottom row first, left to right, the gauge
fills, with bubbles carried up by the rising fuel, and a ball flies from
the count to land on the sled as it ends, when it can be launched and the
meter comes up. Played again, a hovering sled stays and is the player's at
once, and what is left of the bricks shows until each is laid again. A
lost ball's replacement flies from the count too. Exits 0 when every check
passes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from energy import bubbles, fuel, meter  # noqa: E402
from game import Game, check  # noqa: E402


def bricks_shown(game):
    """The brick sprites on the screen, by index, as {index: (x, y)}."""
    sym = game.sym
    hidden = sym['SPRITE_HIDDEN_Y']
    return {i: (x, y) for i, (x, y, _) in enumerate(game.sprites('XRAM_BRICKS', sym['LEVEL1_BRICKS']))
            if y != hidden}


def rising(game):
    """The top of each bubble rising through the fuel, in px, from RAM, or
    None for one that is not."""
    n = game.sym['BUBBLES']
    ys = game.ram('bubble_y', 2 * n).to_bytes(2 * n, 'little')
    pops = game.ram('bubble_pop', n).to_bytes(n, 'little')
    return [int.from_bytes(ys[2 * i:2 * i + 2], 'little') >> 4 if ys[2 * i] | ys[2 * i + 1] and not pops[i] else None
            for i in range(n)]


def main():
    game = Game()
    sym = game.sym
    steps, rise, paddle_y = sym['TUNE_BUILD_STEPS'], sym['TUNE_RISE_STEPS'], sym['TUNE_PADDLE_Y']
    bricks, balls = sym['LEVEL1_BRICKS'], sym['TUNE_BALLS']
    sled, ball = 'XRAM_SLED_SPRITE', 'XRAM_BALL_SPRITE'
    count = lambda: game.count('XRAM_BALL_DIGITS', sym['BALL_DIGITS'])

    # Under the welcome, the level is empty: no bricks, no sled, no ball,
    # the gauge empty and the meter down. The count shows every ball.
    game.boot()
    game.tap('space')  # START GAME
    game.until('game_state', 'STATE_PLAY')
    game.until('talk_state', 'TALK_READY', 120)
    check(not bricks_shown(game), 'no bricks under the welcome')
    check(game.sprite(sled)[1] >= sym['SCREEN_H'] or game.sprite(sled)[1] == sym['SPRITE_HIDDEN_Y'], 'no sled')
    check(game.sprite(ball)[1] == sym['SPRITE_HIDDEN_Y'], 'no ball')
    check(fuel(game) == 0 and meter(game)[0] == 0, 'the gauge empty, the meter down')
    check(count() == balls, f'the count shows {balls}')
    print('ok: the level is empty under the welcome')

    # As he goes, after his last bubble, it builds up.
    for _ in range(game.ram('to_say')):
        game.tap('space')
        game.until('talk_state', 'TALK_READY', 120)
        check(not game.ram('build_steps'), 'not before his last bubble')
    game.tap('space')  # his last OK
    check(game.ram('talk_state') == sym['TALK_OUT'] and game.ram('build_steps') > 0, 'it builds up as he goes')
    heights, laid, rows, seen, launched = [], [], [], set(), False
    before, rose = None, 0
    while game.ram('building'):
        heights.append(game.sprite(sled)[1])
        shown = bricks_shown(game)
        laid += [i for i in sorted(shown) if i not in laid]
        rows.append(game.ram('rows'))  # the sprites change every step, and may be read part drawn
        seen.update(bubbles(game))
        # Mid fill, a bubble rises with the fuel as well as by itself.
        if before is None and game.ram('build_steps') >= steps // 2:
            before = (rising(game), game.ram('build_steps'))
        elif before and not rose and game.ram('build_steps') >= before[1] + 8:
            took = game.ram('build_steps') - before[1]
            now = rising(game)
            rose = max([a - b for a, b in zip(before[0], now) if a is not None and b is not None] + [0]) / took
        if game.ram('build_steps') == steps // 2 and not launched:
            game.cmd('press space')  # too early to launch
            launched = True
        if game.ram('build_steps') == steps // 2 + 4:
            game.cmd('release space')
        check(len(heights) < 2 * steps + 60, 'the build-up ends')
        game.run(1)
    check(not game.ram('energy_draining') and game.ram('ball_state') == sym['BALL_DOCKED'],
          'it can not be launched before the ball lands')
    check(heights == sorted(heights, reverse=True) and heights[-1] == paddle_y,
          f'the sled rises into place: {heights[:3]} to {heights[-1]}')
    check(paddle_y in heights[:rise + 4], f'in {rise} steps')
    where = {i: xy for i, xy in bricks_shown(game).items()}
    order = sorted(where, key=lambda i: (-where[i][1], where[i][0]))
    check(len(where) == bricks and laid == order, f'the bricks are laid bottom row first, left to right: {laid}')
    game.run(2)
    check(rows == sorted(rows) and fuel(game) == sym['GLASS_H'], f'the gauge fills, to {fuel(game)}')
    check(game.ram('energy', 2) == sym['TUNE_ENERGY'], 'with the energy full')
    check(len(seen) >= 6, f'bubbles rise through the fill: {sorted(seen)}')
    check(rose > 2, f'carried up by the fuel as it rises, {rose:.1f} px a step')
    print(f'ok: the sled rose, {bricks} bricks were laid in order, and the gauge filled')

    # The ball came from the count, which shows one less, and the meter
    # comes up green once it lands.
    check(count() == balls - 1 and game.ram('balls') == balls - 1, 'the ball came out of the count')
    up = sym['METER_RISE']
    game.run((up + 2) * sym['METER_STEPS'])
    check(meter(game) == (up, sym['PADDLE_GREEN']), f'the meter comes up green: {meter(game)}')
    print('ok: the ball came from the count, and the meter came up')

    # A lost ball: the next flies from the count, which drops as it leaves,
    # and the fuel drains the while.
    game.tap('space')
    game.wait('launch', 5)
    game.run(20)
    game.paused_poke([('ball_y', 225 << 8, 4), ('ball_vx', 0, 2), ('ball_vy', 600, 2)])
    game.wait('ball lost', 10)
    game.wait('ball comes', 5)
    check(count() == balls - 2, 'the next ball leaves the count')
    energy = game.ram('energy', 2)
    game.wait('ball landed', 120)
    check(game.ram('energy', 2) < energy, 'the fuel drains while it comes')
    print('ok: a lost ball is replaced from the count')

    # Restart with the sled hovering: the ball goes at once, the sled stays
    # and is the player's, the broken bricks stay gone until they are laid
    # again, the fuel rises only once the fill reaches it, and the meter
    # goes down, to come up again once the ball lands.
    game.tap('space')
    game.wait('brick', 600)
    game.run(3)
    broken = set(range(bricks)) - set(bricks_shown(game))
    check(broken, 'a brick is broken')
    x = game.sprite(sled)[0]
    held = game.ram('rows')
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('down')
    game.tap('down')  # RESTART
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    check(game.sprite(ball)[1] == sym['SPRITE_HIDDEN_Y'], 'Restart: the ball goes at once')
    check(game.sprite(sled) == (x, paddle_y) and game.ram('paddle_state') == sym['PADDLE_HOVER'],
          'the sled stays where it was')
    check(broken - set(bricks_shown(game)), 'the broken bricks stay gone until they are laid')
    game.cmd('press right')
    game.run(6)
    game.cmd('release right')
    check(game.sprite(sled)[0] > x, 'and the sled is the player\'s at once')
    first = []
    while game.ram('building'):
        first.append(game.ram('rows'))
        game.run(1)
    fill_at = held * steps // sym['GLASS_H']
    check(all(r == held for r in first[:fill_at - 6]) and first[-1] == sym['GLASS_H'],
          f'the fuel holds at {held} rows until the fill reaches it, then fills')
    check(meter(game)[0] == 0, 'the meter went down')
    check(bricks_shown(game).keys() == set(range(bricks)), 'every brick is laid again')
    game.run((up + 2) * sym['METER_STEPS'])
    check(meter(game) == (up, sym['PADDLE_GREEN']), 'and comes up green once the ball lands')
    print('ok: Restart keeps the sled, and builds the level up again over what was left')

    # Out of fuel as a ball comes: it chases the falling sled down, and the
    # level ends out of fuel. The menu covers the meter, which goes down
    # under it.
    game.tap('space')
    game.wait('launch', 5)
    game.run(20)
    game.paused_poke([('ball_y', 225 << 8, 4), ('ball_vx', 0, 2), ('ball_vy', 600, 2), ('energy', 30, 2)])
    game.wait('ball comes', 10)
    game.wait('out of energy', 40)
    check(game.ram('ball_state') == sym['BALL_COMING'], 'out of fuel, the ball still comes to the sled')
    game.until('game_state', 'STATE_MENU', 300)
    check(game.shows('OUT OF FUEL'), 'and the level ends out of fuel')
    game.run(2)
    check(meter(game)[0] == 0, 'the meter is down under the menu')
    print('ok: out of fuel, the coming ball chases the sled down')

    # Restart while the sled sputters: it goes at once, and rises.
    game.menu_choose('REPLAY')
    game.ready()
    game.tap('space')
    game.wait('launch', 5)
    game.paused_poke([('energy', 10, 2)])
    game.wait('out of energy', 20)
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('down')
    game.tap('down')  # RESTART
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    game.run(1)
    check(game.ram('paddle_state') == sym['PADDLE_RISING'] and game.sprite(sled)[1] > paddle_y + 20,
          'Restart while the sled sputters: it goes, to rise again')
    game.wait('paddle in place', rise + 10)
    print('ok: and rises')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
