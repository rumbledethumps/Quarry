#!/usr/bin/env python3
"""Checks the menu when a stage ends and the upgrade screen, in the emulator.

  upgrades.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The nugget count is poked
to buy with. Reads the menus from the text cells in XRAM, and the panels
from their own text cells. Exits 0 when every check passes.
"""

import os
import sys

from game import SPRITE, Game, check

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art'))
from panels import FONT  # noqa: E402

END_ITEMS = ['UPGRADES', 'REPLAY', 'MAIN MENU']
PICKED = 0x1E  # MODE1_BG_FG(BOX_FILL, PICK_COLOR), the frame of the item picked


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
    sym = game.sym
    tune = tuning(game)
    game.cmd('pad 0 connect')
    game.new_game()
    game.run(5)

    def end_picked():
        """The item picked on the menu when a stage ends, end_menu in
        src/main.c: a title, then each item in a frame ITEM_ROWS tall."""
        center, top = game.ram('end_menu'), game.ram('end_menu+1')
        col = center - sym['MENU_COLS'] // 2 + 2
        picks = [item for i, item in enumerate(END_ITEMS)
                 if game.color(col, top + 3 + i * sym['ITEM_ROWS']) == PICKED]
        check(len(picks) == 1, f'one item of the menu is picked: {picks}')
        return picks[0]

    def panel_tiles(p, row):
        """The tiles inside panel p, on a row of its map."""
        cols, left = sym['PANEL_MAP_COLS'], p * sym['PANEL_PITCH'] + sym['PANEL_BORDER']
        return game.xram(sym['XRAM_PANELS'] + row * cols + left, sym['PANEL_INSIDE'])

    def panel(p, row):
        """The text inside panel p, on a row of its map: each tile of the
        font, lit or dim, as its character, and the short digits as digits."""
        dim, text = sym['PANEL_TILE_DIM'], ''
        for t in panel_tiles(p, row):
            i = (t - 1) % dim
            text += FONT[i] if i < len(FONT) else str(i - len(FONT)) if i < len(FONT) + 10 else '?'
        return text.strip()

    def panel_lit(p):
        """Whether panel p's contents are lit: its plate a lit tile."""
        return panel_tiles(p, sym['TITLE_ROW'])[0] <= sym['PANEL_TILE_DIM']

    def settle():
        game.run(40)

    # The stage ends: the menu, with UPGRADES picked, takes no choice for a
    # moment.
    game.tap('space')
    game.poke('balls', 0)
    game.wait('out of balls', 3000)
    game.run(2)
    check(game.ram('game_state') == sym['STATE_MENU'], 'the menu opens when the stage ends')
    check(all(game.shows(w) for w in ['CHOOSE'] + END_ITEMS), 'it shows CHOOSE and its items')
    check(end_picked() == 'UPGRADES', 'UPGRADES is picked')
    game.tap('space')
    game.run(10)
    check(game.ram('game_state') == sym['STATE_MENU'], 'a choice right away is not taken')
    game.run(60)

    # Every up and down key moves the pick, no left or right key does, the
    # menu doesn't wrap, and keypad 0, which only launches, does not choose.
    for key in ['down', 'up', 's', 'w', 'kp2', 'kp8', 'pad 0 down', 'pad 0 up']:
        was = end_picked()
        game.tap(key)
        check(end_picked() != was, f'{key} moves the pick')
    for key in ['right', 'left', 'd', 'a', 'kp6', 'kp4', 'pad 0 right', 'pad 0 left']:
        was = end_picked()
        game.tap(key)
        check(end_picked() == was, f'{key} does not move the pick')
    game.tap('up')
    check(end_picked() == 'UPGRADES', 'up from the first stays: the menu does not wrap')
    for _ in END_ITEMS:
        game.tap('down')
    check(end_picked() == 'MAIN MENU', 'down from the last stays')
    game.tap('up')
    game.tap('up')
    print('ok: up and down move the pick, without wrapping, and left and right do not')
    game.tap('kp0')
    check(game.ram('game_state') == sym['STATE_MENU'], 'keypad 0 does not choose')

    # The upgrade screen, with no nuggets: a panel for each upgrade, the
    # first lit in the middle, and nothing to buy.
    game.poke('nuggets', 0, 2)
    game.menu_choose('UPGRADES', wait=False)
    game.run(20)  # past the flicker of the panel in the middle
    check(game.ram('panel_picked') == 0 and game.ram('cursor_on') == sym['ON_RAIL'],
          'it opens on the rail, with the first panel picked')
    check(panel(0, sym['TITLE_ROW']) == 'WIDER SLED' and panel(1, sym['TITLE_ROW']) == 'FASTER SLED',
          'the panels show their titles')
    widths = tune['TUNE_WIDTHS']
    check(panel(0, sym['EFFECT_ROW']) == f'{widths[0]} \x10 {widths[1]} PX', 'and what the next width is')
    check(panel(0, sym['COST_ROW']) == str(tune['TUNE_WIDTH_COSTS'][0]), 'and what it costs')
    check(panel_lit(0) and not panel_lit(1), 'the middle panel is lit and the next one dim')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram('upgrade_levels', 2) == 0, 'no upgrade without the nuggets')

    # Right slides the panels left, the next one lit in the middle, and the
    # picture slides with its panel. At the last panel, right does nothing.
    picture = game.sprite(f'XRAM_MENU_SPRITES')[0]
    game.tap('right')
    settle()
    check(game.ram('panel_picked') == 1 and game.ram('panel_scroll', 2) == sym['PANEL_STEP'],
          'right slides the next panel to the middle')
    check(game.sprite(f'XRAM_MENU_SPRITES')[0] == picture - sym['PANEL_STEP'],
          'the picture slides with its panel')
    check(panel_lit(1) and not panel_lit(0), 'and it is lit, the one it left dim')
    for _ in range(sym['PANELS']):
        game.tap('right')
    check(game.ram('panel_picked') == sym['PANELS'] - 1, 'right stops at the last panel')
    for _ in range(sym['PANELS']):
        game.tap('left')
    settle()
    check(game.ram('panel_picked') == 0 and game.ram('panel_scroll', 2) == 0, 'and left at the first')
    print('ok: the panels slide')

    # The cheats of a debug build: on the rail, Shift and right or left raise
    # or lower the upgrade picked, for nothing, and repeat while held.
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('upgrade_levels') == 1 and game.ram('nuggets', 2) == 0,
          'Shift and right raises the width, for nothing')
    game.tap('left')
    check(game.ram('upgrade_levels') == 0, 'Shift and left lowers it')
    game.cmd('press right')
    game.run(sym['SHIFT_DELAY'] + 2 * sym['SHIFT_REPEAT'] + 2)
    game.cmd('release right')
    check(game.ram('upgrade_levels') >= 3, 'held, it repeats')
    game.cmd('press left')
    game.run(sym['SHIFT_DELAY'] + sym['SHIFT_REPEAT'] * sym['UPGRADE_LEVELS_MAX'])
    game.cmd('release left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram('upgrade_levels') == 0, 'and back down to none')
    print('ok: the upgrade cheats')

    # With nuggets: every level of width, each at its cost, then MAX. The
    # count shows what is left.
    have = 200
    game.poke('nuggets', have, 2)
    for level, cost in enumerate(tune['TUNE_WIDTH_COSTS'], 1):
        game.tap('space')
        game.wait(f'bought width {level}', 10)
        have -= cost
        check(game.ram('nuggets', 2) == have, f'width {level} costs {cost}')
    check(game.count('XRAM_NUGGET_DIGITS', sym['COUNT_DIGITS']) == have, 'the count shows what is left')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram('nuggets', 2) == have, 'nothing more to buy at the top level')
    check(panel(0, sym['COST_ROW']) == 'MAX', 'the top level shows MAX')
    print('ok: bought every width')

    # A level of speed, on the next panel.
    game.tap('right')
    game.tap('space')
    game.wait('bought speed 1', 10)
    have -= tune['TUNE_SPEED_COSTS'][0]
    check(game.ram('nuggets', 2) == have, 'speed 1 costs its cost')

    # Down goes to the stages, where only the open ones can be picked.
    game.tap('down')
    check(game.ram('cursor_on') == sym['ON_STAGES'], 'down moves the cursor to the stages')
    game.tap('right')
    check(game.ram('stage_picked') == 1, 'stage 2 is locked until stage 1 is cleared')

    # On the stages, Shift and right opens the next stage, with its unlock,
    # and another cuts that short and opens the one after. Shift and left
    # locks them again.
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('stages_cleared') == 1 and game.ram('unlocking') == 2,
          'Shift and right opens stage 2, to unlock')
    game.tap('right')
    check(game.ram('stages_shown') == 2 and game.ram('unlocking') == 3,
          'another cuts the unlock short, and opens stage 3')
    game.tap('left')
    game.tap('left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram('stages_cleared') == 0 and game.ram('unlocking') == 0 and
          game.ram('stage_picked') == 1 and game.ram('stages_shown') == 1, 'Shift and left locks them again')
    print('ok: the stage cheats')

    # Esc asks to go back to the title, and Esc again doesn't.
    game.tap('escape')
    check(game.shows('RETURN TO TITLE?'), 'Esc asks to go back to the title')
    game.tap('escape')
    check(not game.shows('RETURN TO TITLE?'), 'Esc again does not')

    # The button on a stage asks to begin it, with YES picked, and YES plays
    # it with the paddle upgraded.
    game.tap('space')
    check(game.shows('BEGIN LEVEL 1?'), 'the button asks to begin the stage')
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    game.run(2)
    width, speed = widths[-1], tune['TUNE_SPEEDS'][1]
    check(game.ram('paddle_width') == width, f'the paddle is {width} px wide now')
    check(game.ram('paddle_speed', 2) == speed, f'and moves {speed} a step')
    size = (8 // 4 - 1) << 4 | ((width + 3) // 4 - 1)  # MODE5_SIZE(SLED_IMAGE_W(width), 8)
    check(game.sizes('XRAM_SLED_SPRITE', 1)[0] == size, f'the sled shows {width} px wide')
    jets = game.ram(f'jets+{len(tune["TUNE_WIDTH_COSTS"])}')
    check(game.shown('XRAM_JET_SPRITES', sym['JETS_MAX']) == jets, f'with its {jets} jets')
    check(game.ram('nuggets', 2) == have, 'the nuggets left are kept')
    # Short of the wall: the steps it takes from the middle of the playfield.
    x = game.px('paddle_x')
    steps = min(20, (x - game.ram('play_left', 2)) * 256 // speed)
    game.cmd('press left')
    game.run(steps)
    game.cmd('release left')
    moved = x - game.px('paddle_x')
    check(abs(moved - (steps - 1) * speed / 256) <= speed / 256 + 1,
          f'the paddle moves at its new speed, {moved} px in {steps} steps')
    print(f'ok: a {width} px paddle moving {speed / 256} px a step')

    # The first clear of stage 1 earns a coin and opens stage 2, which the
    # upgrade screen picks. Clearing it again earns nothing.
    def clear():
        game.tap('space')
        game.run(20)
        game.paused_poke([('bricks_left', 0, 1)])
        game.wait('stage cleared', 10)
        game.run(2)

    clear()
    check(game.ram('coins', 2) == 1 and game.ram('stages_cleared') == 1, 'a coin for clearing stage 1')
    check(game.count('XRAM_COIN_DIGITS', sym['COUNT_DIGITS']) == 1, 'the count shows it')
    game.menu_choose('REPLAY')
    clear()
    check(game.ram('coins', 2) == 1, 'no coin for clearing it again')
    game.menu_choose('UPGRADES')
    game.run(5)
    check(game.ram('stage_picked') == 2, 'the upgrade screen picks stage 2, just opened')
    lock = sym['XRAM_MENU_SPRITES'] + (sym['PANELS'] * sym['PANEL_SPRITES'] + 4) * SPRITE
    check(game.ram('unlocking') == 2 and game.shown(lock, 2) == 2, 'and its lock shows, to break')
    check(game.shown(lock + 2 * SPRITE, 4) == 4, 'with padlocks on the 4 carts locked after it')
    game.wait('unlocked 2', 200)
    check(game.ram('stages_shown') == 2 and game.ram('unlocking') == 0, 'the lock breaks, and stage 2 shows open')
    game.tap('down')
    game.tap('space')
    check(game.shows('BEGIN LEVEL 2?'), 'and asks to begin stage 2')
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    check(game.ram('bricks_left') == (sym['STAGE1_COLS'] + 1) * sym['STAGE1_ROWS'],
          'stage 2 is a column wider')
    game.close()
    print('ok: a coin for the first clear, and the next stage')
    print('PASS')


if __name__ == '__main__':
    main()
