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
TAG = b'QRY1'
# The title menu, from src/main.c and src/menu.c: no title line, so its
# items start a row under the top edge, at row 13, each 3 rows tall.
TITLE_FRAMES = {'RESUME': (14, 13), 'NEW GAME': (14, 16), 'EXIT': (14, 19)}
NEW_GAME_TEXT = (16, 17)
RESUME_TEXT = (17, 14)
PICKED = 0x1E  # MODE1_BG_FG(BOX_FILL, PICK_COLOR)
DIM = 0x14     # MODE1_BG_FG(BOX_FILL, DIM_COLOR)


def read_save(folder):
    """The save as (nuggets, upgrade levels, stages unlocked), or None."""
    path = os.path.join(folder, SAVE)
    if not os.path.exists(path):
        return None
    data = open(path, 'rb').read()
    check(len(data) == 9 and data[:4] == TAG, f'the save is a good one: {data!r}')
    nuggets, width, speed, stages = struct.unpack('<HBBB', data[4:])
    return nuggets, (width, speed), stages


class Title:
    """Reads the title menu."""

    def __init__(self, game):
        self.game = game
        check(game.text(*NEW_GAME_TEXT, 8) == 'NEW GAME', 'the title menu is up')

    def color(self, cell):
        return self.game.color(*cell)

    def picked(self):
        picks = [item for item, cell in TITLE_FRAMES.items() if self.color(cell) == PICKED]
        check(len(picks) == 1, f'one item of the title menu is picked: {picks}')
        return picks[0]

    def resume_dim(self):
        return self.color(RESUME_TEXT) == DIM


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
    check(title.picked() == 'EXIT', 'up from New Game skips Resume, to Exit')
    game.tap('down')
    check(title.picked() == 'NEW GAME', 'and back')
    check(read_save(folder) is None, 'no save yet')
    game.new_game()
    check(read_save(folder) == (0, (0, 0), 1), 'a stage starting saves a new game')
    print('ok: a new game, saved when the stage starts')

    # Pausing saves the nuggets, with those still on their way, and holds
    # the game still. Esc again, or Start, carries on.
    game.tap('space')
    game.wait('brick', 600)
    game.run(3)
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.run(2)
    check(game.shows('PAUSED') and game.shows('CONTINUE') and game.shows('EXIT'), 'the pause menu')
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
    game.tap('space')  # Continue
    game.until('game_state', 'STATE_PLAY', 10)
    print(f'ok: paused with {broken} nuggets saved, and carried on')

    # The stage ends, and that saves too.
    os.remove(os.path.join(folder, SAVE))
    game.poke('balls', 0)
    game.wait('out of balls', 3000)
    game.run(2)
    broken = game.sym['STAGE1_COLS'] * game.sym['STAGE1_ROWS'] - game.ram('bricks_left')
    check(read_save(folder) and read_save(folder)[0] == broken, f'a stage ending saves, {broken} nuggets')

    # Pausing over the end-of-stage menu and the upgrade screen puts each
    # back, as it was.
    game.run(70)
    game.tap('down')  # PLAY
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('escape')
    game.until('game_state', 'STATE_MENU', 10)
    check(game.shows('UPGRADES') and not game.shows('PAUSED'), 'the end-of-stage menu is back')
    os.remove(os.path.join(folder, SAVE))
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 60)
    check(read_save(folder) is not None, 'PLAY was still picked, and the stage starting saves')
    game.paused_poke([('balls', 0, 1), ('ball_state', 1, 1)])
    game.wait('out of balls', 3000)
    game.menu_choose('UPGRADES')
    game.poke('nuggets', 20, 2)
    game.tap('enter')  # WIDTH, to BUY
    game.tap('enter')  # BUY
    game.wait('bought width 1', 10)
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 30)
    game.run(2)
    check(read_save(folder)[:2] == (14, (1, 0)), 'pausing saves the upgrade bought')
    rows = game.screen(os.path.join(folder, 'shot.png'))
    box = [rows[y][x] for y in range(11 * 8 + 4, 21 * 8 - 4) for x in range(12 * 8 + 4, 28 * 8 - 4)]
    nugget = (0xd0, 0xd0, 0xd8)  # the light face of a white nugget, in palettes.bricks
    check(not any(all(abs(a - b) < 24 for a, b in zip(p, nugget)) for p in box),
          'no picture of the upgrade screen shows in the pause menu')
    game.tap('escape')
    game.until('game_state', 'STATE_SHOP', 30)
    game.run(5)
    check(game.shows('WIDER PADDLE') and not game.shows('PAUSED'), 'the upgrade screen is back')
    print('ok: paused over the end-of-stage menu and the upgrade screen')

    # Exit from the pause menu goes to the title screen, where Resume can be
    # picked now.
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 30)
    game.tap('down')
    game.tap('space')
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
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 120)
    game.run(2)
    check(game.ram('nuggets', 2) == 14, 'Resume brings back the nuggets')
    check(game.ram('upgrade_levels') == 1 and game.ram('paddle_width') == 32,
          'and the upgrade, on the paddle')
    print('ok: came back, and Resume brought back 14 nuggets and a wider paddle')

    # New Game over a save asks first. No leaves the save, Yes starts over.
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('down')
    game.tap('space')
    game.until('game_state', 'STATE_TITLE', 60)
    game.tap('down')   # NEW GAME
    game.tap('space')
    game.until('game_state', 'STATE_CONFIRM', 10)
    check(game.shows('START OVER?'), 'it asks to start over')
    game.tap('space')  # NO, picked first
    game.until('game_state', 'STATE_TITLE', 10)
    check(read_save(folder)[:2] == (14, (1, 0)), 'No leaves the save')
    game.tap('space')  # NEW GAME, picked after No
    game.until('game_state', 'STATE_CONFIRM', 10)
    game.tap('up')     # YES
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(2)
    check(read_save(folder) == (0, (0, 0), 1), 'Yes replaces the save with a new game')
    check(game.ram('nuggets', 2) == 0 and game.ram('paddle_width') == 24, 'and starts over')
    print('ok: New Game asked first, and No kept the save')
    game.close()

    # A save that isn't one is no save.
    open(os.path.join(folder, SAVE), 'wb').write(b'NOPE, not a save')
    game = Game()
    game.boot()
    check(Title(game).resume_dim(), 'a bad save file is no save')

    # Exit leaves the game.
    game.tap('down')   # EXIT
    game.cmd('press space')
    game.cmd('wait exit 60')
    game.cmd('expect exit 0')
    game.close()
    print('ok: a bad save is ignored, and Exit leaves')

    # The web player keeps its saves between visits.
    page = os.path.join(os.path.dirname(os.path.dirname(rom())), 'web', 'quarry', 'index.html')
    check("db: 'rumbledethumps-quarry'" in open(page).read(), 'the web player keeps its saves')
    print('PASS')


if __name__ == '__main__':
    main()
