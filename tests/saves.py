#!/usr/bin/env python3
"""Checks the title screen, the pause menu and the save, in the emulator.

  saves.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Every run of the emulator
here keeps its saves in a folder of the test's own. Reads the save file
itself, and the menus from the text cells in XRAM. Exits 0 when every
check passes.
"""

import os
import struct

from game import Game, check, rom, save_dir

SAVE = 'quarry.save'
TAG = b'QRY2'
TITLE_ITEMS = ['RESUME', 'NEW GAME']
PICKED = 0x1E  # MODE1_BG_FG(BOX_FILL, PICK_COLOR)
DIM = 0x14     # MODE1_BG_FG(BOX_FILL, DIM_COLOR)


def read_save(folder):
    """The save as (nuggets, coins, upgrade levels, stages cleared, stage
    picked), or None."""
    path = os.path.join(folder, SAVE)
    if not os.path.exists(path):
        return None
    data = open(path, 'rb').read()
    check(len(data) == 12 and data[:4] == TAG, f'the save is a good one: {data!r}')
    nuggets, coins, width, speed, cleared, picked = struct.unpack('<HHBBBB', data[4:])
    return nuggets, coins, (width, speed), cleared, picked


class Title:
    """Reads the title menu, title_menu in src/main.c, where src/menu.c draws
    it: no title line, so its items start a row under its top edge, each in
    a frame ITEM_ROWS tall, 2 columns in from the box, with its text centered
    a row down."""

    def __init__(self, game):
        self.game = game
        center, top = game.ram('title_menu'), game.ram('title_menu+1')
        rows = [top + 1 + i * game.sym['ITEM_ROWS'] for i in range(len(TITLE_ITEMS))]
        self.frames = {item: (center - game.sym['MENU_COLS'] // 2 + 2, row)
                       for item, row in zip(TITLE_ITEMS, rows)}
        self.texts = {item: (center - len(item) // 2, row + 1) for item, row in zip(TITLE_ITEMS, rows)}
        check(game.text(*self.texts['NEW GAME'], 8) == 'NEW GAME', 'the title menu is up')

    def picked(self):
        picks = [item for item, cell in self.frames.items() if self.game.color(*cell) == PICKED]
        check(len(picks) == 1, f'one item of the title menu is picked: {picks}')
        return picks[0]

    def resume_dim(self):
        return self.game.color(*self.texts['RESUME']) == DIM


def main():
    folder = save_dir()

    # A first run, with no save: Resume is grayed out and can't be picked,
    # and New Game starts at once.
    game = Game()
    game.boot()
    title = Title(game)
    check(title.resume_dim(), 'Resume is grayed out with no save')
    check(title.picked() == 'NEW GAME', 'New Game is picked')
    game.tap('up')
    check(title.picked() == 'NEW GAME', 'up from New Game stays, as Resume cannot be picked')
    check(read_save(folder) is None, 'no save yet')
    game.new_game()
    check(read_save(folder) == (0, 0, (0, 0), 0, 1), 'a stage starting saves a new game')
    print('ok: a new game, saved when the stage starts')

    # Pausing saves the nuggets, with those still on their way, and holds
    # the game still. Esc again, or Start, carries on.
    game.tap('space')
    game.wait('brick', 600)
    game.run(3)
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.run(2)
    check(all(game.shows(w) for w in ['PAUSED', 'RESUME', 'UPGRADES', 'RESTART', 'MAIN MENU']),
          'the pause menu')
    broken = game.sym['STAGE1_COLS'] * game.sym['STAGE1_ROWS'] - game.ram('bricks_left')
    saved = read_save(folder)
    check(saved and saved[0] == broken, f'pausing saves a nugget for each broken brick, {saved} for {broken}')
    ball = 'XRAM_BALL_SPRITE'
    where, energy = game.sprite(ball), game.ram('energy', 2)
    game.run(30)
    check(game.sprite(ball) == where and game.ram('energy', 2) == energy, 'nothing moves while paused')
    game.tap('escape')
    game.until('game_state', 'STATE_PLAY', 10)
    game.run(10)
    check(game.sprite(ball) != where, 'Esc again carries on')
    check(not game.shows('PAUSED'), 'the pause menu is gone')
    game.cmd('pad 0 connect')
    game.tap('pad 0 start')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('space')  # Resume
    game.until('game_state', 'STATE_PLAY', 10)
    for control in ['pad 0 select', 'p', 'pause']:
        game.tap(control)
        game.until('game_state', 'STATE_PAUSE', 10)
        game.tap('space')
        game.until('game_state', 'STATE_PLAY', 10)
    print(f'ok: paused with {broken} nuggets saved, and carried on, and Select, P and Pause pause too')

    # The stage ends, and that saves too.
    os.remove(os.path.join(folder, SAVE))
    game.poke('balls', 0)
    game.wait('out of balls', 3000)
    game.run(2)
    broken = game.sym['STAGE1_COLS'] * game.sym['STAGE1_ROWS'] - game.ram('bricks_left')
    check(read_save(folder) and read_save(folder)[0] == broken, f'a stage ending saves, {broken} nuggets')

    # Esc does nothing on the menu when a stage ends. Replay plays the stage
    # again, which saves, with its curtains and texture as they were.
    game.run(70)
    game.tap('escape')
    game.run(5)
    check(game.ram('game_state') == game.sym['STATE_MENU'] and not game.shows('PAUSED'),
          'Esc does nothing on the menu')
    os.remove(os.path.join(folder, SAVE))
    cave = game.ram('curtain_set'), game.xram('XRAM_TEXTURE_CONFIG', 8)
    game.menu_choose('REPLAY', wait=False)
    check(read_save(folder) is not None, 'the stage starting saves')
    check((game.ram('curtain_set'), game.xram('XRAM_TEXTURE_CONFIG', 8)) == cave,
          'the stage played again keeps its curtains and its texture')

    # Restart from the pause menu starts the stage over, and keeps them too.
    game.paused_poke([('bricks_left', 3, 1)])
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('down')
    game.tap('down')  # RESTART
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    check(game.ram('bricks_left') == game.sym['STAGE1_COLS'] * game.sym['STAGE1_ROWS'],
          'Restart starts the stage over')
    check((game.ram('curtain_set'), game.xram('XRAM_TEXTURE_CONFIG', 8)) == cave,
          'with its curtains and texture')
    print('ok: Replay and Restart')

    # A purchase on the upgrade screen saves. Esc there asks to go back to
    # the title, where Resume can be picked now.
    game.paused_poke([('balls', 0, 1), ('ball_state', 1, 1)])
    game.wait('out of balls', 3000)
    game.menu_choose('UPGRADES')
    game.poke('nuggets', 20, 2)
    left = 20 - game.ram('width_costs', 2)  # after the first width
    game.tap('enter')
    game.wait('bought width 1', 10)
    check(read_save(folder)[:3] == (left, 0, (1, 0)), 'buying saves the upgrade bought')
    game.tap('escape')
    check(game.shows('RETURN TO TITLE?'), 'Esc asks to go back to the title')
    game.tap('space')  # YES
    game.until('game_state', 'STATE_TITLE', 60)
    game.run(5)
    title = Title(game)
    check(not title.resume_dim() and title.picked() == 'RESUME', 'Resume is there now, and picked')
    game.close()

    # Another run, as when the player comes back: Resume brings back the
    # nuggets and the upgrade.
    game = Game()
    game.boot()
    game.run(3)
    title = Title(game)
    check(title.picked() == 'RESUME', 'Resume is picked when the player comes back')

    # Left and right don't move a menu. On the title, Shift and right or left
    # switch the curtains, and with Shift, down doesn't move the menu.
    for key in ['right', 'left']:
        game.tap(key)
        check(title.picked() == 'RESUME', f'{key} does not move the menu')
    sets, shown = game.sym['CURTAIN_SETS'], game.ram('curtain_set')
    palette = game.xram('XRAM_PALETTE_CURTAIN', 32)
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('curtain_set') == (shown + 1) % sets, 'Shift and right show the next curtains')
    check(sets == 1 or game.xram('XRAM_PALETTE_CURTAIN', 32) != palette, 'with their own colors')
    game.tap('left')
    check(game.ram('curtain_set') == shown, 'Shift and left show the ones before')
    game.tap('left')
    check(game.ram('curtain_set') == (shown - 1) % sets, 'and go on around')
    game.tap('down')
    game.cmd('release lshift')
    check(title.picked() == 'RESUME', 'with Shift, down does not move the menu')
    print(f'ok: left and right leave the menu, and Shift switches the {sets} curtain sets')
    game.tap('space')
    game.until('game_state', 'STATE_SHOP', 120)
    check(game.ram('nuggets', 2) == left, 'Resume opens the upgrade screen with the nuggets')
    check(game.ram('upgrade_levels') == 1, 'and the upgrade')
    game.tap('down')
    game.tap('space')
    game.tap('space')  # YES, begin the stage
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(2)
    check(game.ram('paddle_width') == game.ram('widths+1'), 'the stage has the upgrade, on the paddle')
    print(f'ok: came back, and Resume brought back {left} nuggets and a wider paddle')

    # Main Menu from the pause menu goes to the title. New Game over a save
    # asks first. No leaves the save, Yes starts over.
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    for _ in range(3):
        game.tap('down')  # MAIN MENU
    game.tap('space')
    game.until('game_state', 'STATE_TITLE', 60)
    game.tap('down')   # NEW GAME
    game.tap('space')
    game.until('game_state', 'STATE_CONFIRM', 10)
    check(game.shows('START OVER?'), 'it asks to start over')
    game.tap('space')  # NO, picked first
    game.until('game_state', 'STATE_TITLE', 10)
    check(read_save(folder)[:3] == (left, 0, (1, 0)), 'No leaves the save')
    game.tap('space')  # NEW GAME, picked after No
    game.until('game_state', 'STATE_CONFIRM', 10)
    game.tap('up')     # YES
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(2)
    check(read_save(folder) == (0, 0, (0, 0), 0, 1), 'Yes replaces the save with a new game')
    check(game.ram('nuggets', 2) == 0 and game.ram('paddle_width') == game.ram('widths'),
          'and starts over')
    print('ok: New Game asked first, and No kept the save')
    game.close()

    # A save that isn't one is no save.
    open(os.path.join(folder, SAVE), 'wb').write(b'NOPE, not a save')
    game = Game()
    game.boot()
    check(Title(game).resume_dim(), 'a bad save file is no save')
    game.close()
    print('ok: a bad save is ignored')

    # The web player keeps its saves between visits.
    page = os.path.join(os.path.dirname(os.path.dirname(rom())), 'web', 'quarry', 'index.html')
    check("db: 'rumbledethumps-quarry'" in open(page).read(), 'the web player keeps its saves')
    print('PASS')


if __name__ == '__main__':
    main()
