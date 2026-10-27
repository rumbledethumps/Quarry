#!/usr/bin/env python3
"""Checks the end-of-stage menu and the upgrade screen, in the emulator.

  upgrades.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The nugget count is poked
to buy with. Reads the menus from the text cells in XRAM. Exits 0 when
every check passes.
"""

from game import Game, check

# The menu over the playfield, from src/menu.c: the frame of UPGRADES, then
# of PLAY. A picked frame is gold on the box fill.
UPGRADES_FRAME, PLAY_FRAME = (14, 14), (14, 17)
PICKED, UNPICKED = 0x1E, 0x11  # MODE1_BG_FG(BOX_FILL, PICK_COLOR or BOX_FILL)
COUNT_CELL = (19, 1)           # the count in the upgrade screen's top bar
SPEED_COST_CELL = (26, 12)     # the cost in the SPEED box, from src/shop.c
DIM, BRIGHT = 0x14, 0x19       # MODE1_BG_FG(BOX_FILL, DIM_COLOR or TEXT_COLOR)


def tuning(game):
    """The upgrade tables of src/upgrades.c, from RAM."""
    width_levels, speed_levels = game.sym['WIDTH_LEVELS'], game.sym['SPEED_LEVELS']
    table = lambda name, count, size: [game.ram(f'{name}+{i * size}', size) for i in range(count)]
    return {'TUNE_WIDTHS': table('widths', width_levels + 1, 1),
            'TUNE_WIDTH_COSTS': table('width_costs', width_levels, 2),
            'TUNE_SPEEDS': table('speeds', speed_levels + 1, 2),
            'TUNE_SPEED_COSTS': table('speed_costs', speed_levels, 2)}


def main():
    game = Game()
    tune = tuning(game)
    bricks = game.sym['STAGE1_COLS'] * game.sym['STAGE1_ROWS']
    game.cmd('pad 0 connect')
    game.new_game()
    game.run(5)

    def color(cell):
        return game.color(*cell)

    def picked():
        up, play = color(UPGRADES_FRAME), color(PLAY_FRAME)
        check({up, play} == {PICKED, UNPICKED}, f'one item of the menu is picked: {up:02X} {play:02X}')
        return 'UPGRADES' if up == PICKED else 'PLAY'

    # The stage ends: the menu shows how, with UPGRADES picked, and it takes
    # no choice for a moment.
    game.tap('space')
    game.poke('balls', 0)
    game.wait('out of balls', 3000)
    game.run(2)
    check(game.ram('game_state') == game.sym['STATE_MENU'], 'the menu opens when the stage ends')
    check(game.shows('OUT OF BALLS') and game.shows('UPGRADES') and game.shows('PLAY'),
          'the menu shows how the stage ended, UPGRADES and PLAY')
    check(picked() == 'UPGRADES', 'UPGRADES is picked')
    game.tap('space')
    game.run(10)
    check(game.ram('game_state') == game.sym['STATE_MENU'], 'a choice right away is not taken')
    game.run(60)

    # Every menu key moves the pick, and keypad 0, which only launches,
    # does not choose.
    for key in ['down', 'up', 's', 'w', 'kp2', 'kp8', 'right', 'left', 'd', 'a',
                'pad 0 down', 'pad 0 up']:
        was = picked()
        game.tap(key)
        check(picked() != was, f'{key} moves the pick')
    print('ok: every menu key moves the pick')
    game.tap('kp0')
    check(game.ram('game_state') == game.sym['STATE_MENU'], 'keypad 0 does not choose')

    # Upgrades, with no nuggets: nothing to buy.
    game.poke('nuggets', 0, 2)
    game.menu_choose('UPGRADES', wait=False)
    game.run(5)
    check(game.ram('game_state') == game.sym['STATE_SHOP'], 'UPGRADES opens the upgrade screen')
    for word in ['UPGRADES', 'WIDTH', 'SPEED', 'WIDER PADDLE', 'BUY', 'BACK']:
        check(game.shows(word), f'the upgrade screen shows {word}')
    check(game.text(*COUNT_CELL, 5) == '0    ', 'it shows 0 nuggets')
    game.tap('enter')  # WIDTH, to BUY
    game.tap('enter')  # BUY
    game.cmd('expect-not "bought"')
    check(game.ram('upgrade_levels', 2) == 0, 'no upgrade without the nuggets')
    check(game.shows('NOT ENOUGH NUGGETS'), 'it says there are not nuggets enough')

    # With nuggets enough for one: after buying it, the other shows it can't
    # be bought either.
    first = tune['TUNE_WIDTH_COSTS'][0]
    game.poke('nuggets', first + tune['TUNE_SPEED_COSTS'][0] - 1, 2)
    game.tap('up')    # SPEED
    game.tap('left')  # WIDTH
    check(color(SPEED_COST_CELL) == BRIGHT, 'SPEED shows it can be bought')
    game.tap('enter')  # to BUY
    game.tap('enter')
    game.wait('bought width 1', 10)
    check(color(SPEED_COST_CELL) == DIM, 'after buying WIDTH, SPEED shows it cannot be bought')

    # With nuggets: every level of width, each at its cost, then no more.
    have = 200
    game.poke('nuggets', have, 2)
    for level, cost in list(enumerate(tune['TUNE_WIDTH_COSTS'], 1))[1:]:
        game.tap('enter')
        game.wait(f'bought width {level}', 10)
        have -= cost
        check(game.ram('nuggets', 2) == have, f'width {level} costs {cost}')
        check(game.text(*COUNT_CELL, 5) == f'{have:<5}', 'the count shows what is left')
    game.tap('enter')
    game.cmd('expect-not "bought"')
    check(game.ram('nuggets', 2) == have, 'nothing more to buy at the top level')
    check(game.shows('MAX'), 'the top level shows MAX')
    print(f'ok: bought every width')

    # One level of speed, then BACK.
    game.tap('up')     # SPEED
    game.tap('enter')  # to BUY
    game.tap('enter')
    game.wait('bought speed 1', 10)
    have -= tune['TUNE_SPEED_COSTS'][0]
    check(game.ram('nuggets', 2) == have, 'speed 1 costs its cost')
    game.tap('down')   # BACK
    game.tap('enter')
    game.wait('upgrades closed', 10)
    game.run(5)

    # The next stage is set up behind the menu, with the paddle upgraded,
    # and PLAY picked.
    check(game.ram('game_state') == game.sym['STATE_MENU'], 'BACK goes back to the menu')
    check(picked() == 'PLAY', 'PLAY is picked')
    width, speed = tune['TUNE_WIDTHS'][-1], tune['TUNE_SPEEDS'][1]
    check(game.ram('paddle_width') == width, f'the paddle is {width} px wide now')
    check(game.ram('paddle_speed', 2) == speed, f'and moves {speed} a step')
    size = (8 // 4 - 1) << 4 | (width // 4 - 1)  # MODE5_SIZE(width, 8)
    check(game.sizes('XRAM_SLED_SPRITE', 1)[0] == size, f'the sled shows {width} px wide')
    jets = game.ram(f'jets+{len(tune["TUNE_WIDTH_COSTS"])}')
    check(game.shown('XRAM_JET_SPRITES', game.sym['JETS_MAX']) == jets, f'with its {jets} jets')
    check(game.ram('bricks_left') == bricks and game.ram('balls') == game.sym['TUNE_BALLS'],
          'a fresh stage')
    game.menu_choose('PLAY', wait=False, picked='PLAY')
    check(game.ram('game_state') == game.sym['STATE_PLAY'], 'PLAY plays')
    check(not game.shows('UPGRADES') and not game.shows('OUT OF BALLS'), 'the menu is gone')
    check(game.ram('nuggets', 2) == have, 'the nuggets left are kept')
    x = game.px('paddle_x')
    game.cmd('press left')
    game.run(20)
    game.cmd('release left')
    moved = x - game.px('paddle_x')
    check(abs(moved - 19 * speed / 256) <= speed / 256 + 1,
          f'the paddle moves at its new speed, {moved} px in 20 steps')
    print(f'ok: a {width} px paddle moving {speed / 256} px a step')

    # Clearing stage 1, the only stage, plays stage 1 again.
    game.tap('space')
    game.run(20)
    game.paused_poke([('bricks_left', 0, 1)])
    game.wait('stage cleared', 10)
    game.run(2)
    check(game.shows('STAGE CLEAR'), 'the menu shows STAGE CLEAR')
    game.menu_choose('PLAY')
    game.run(5)
    check(game.ram('game_state') == game.sym['STATE_PLAY'] and game.ram('bricks_left') == bricks,
          'Play starts stage 1 again, the only stage')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
