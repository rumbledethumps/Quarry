#!/usr/bin/env python3
"""Checks the title screen, the pause menu and the save, in the emulator.

  saves.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Every run of the emulator
here keeps its saves in a folder of the test's own. Reads the save file
itself, the menus from their map in XRAM, and the title's panels from
theirs. Exits 0 when every check passes.
"""

import os
import re
import struct
import sys

from game import Game, check, rom, save_dir

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from rp6502 import Symbols  # noqa: E402

SAVE = 'quarry.save'
TAG = b'QRY6'
SYM = Symbols(os.path.splitext(rom())[0] + '.sym')
NO_RANKS = (0,) * SYM['UPGRADES']
NEW_GAME = (0, 0, NO_RANKS, 0, 1, 1, 0, 0)  # as read_save() gives it


def read_save(folder):
    """The save, save_t of src/save.c, as (gray nuggets, coins, upgrade
    ranks, levels cleared, level picked, levels shown open, talks seen,
    lines of the counts shown), or None, with no file or an empty one, as
    Delete Save leaves it."""
    path = os.path.join(folder, SAVE)
    if not os.path.exists(path) or not os.path.getsize(path):
        return None
    data = open(path, 'rb').read()
    check(len(data) == SYM['SAVE_BYTES'] and data[:4] == TAG, f'the save is a good one: {data!r}')
    colors, upgrades = SYM['BRICK_COLORS'], SYM['UPGRADES']
    values = struct.unpack(f'<{colors}HH{upgrades}B5B', data[4:])
    nuggets, coins = values[:colors], values[colors]
    ranks, rest = values[colors + 1:colors + 1 + upgrades], values[colors + 1 + upgrades:]
    return (nuggets[0], coins, ranks) + rest


class Title:
    """Reads the title's menu on its panels, from src/title.c: CONTINUE GAME
    and DELETE SAVE with a save, and the progress, or with none, START GAME
    alone, and the item picked, from src/menu.c."""

    def __init__(self, game):
        self.game = game
        check(game.ram('game_state') == game.sym['STATE_TITLE'], 'the title is up')

    def saved(self):
        """Whether the title is the one of a save."""
        panels = self.game.title_panels()
        check(panels in ('SAVE', 'START'), f'the title has the panels of a save, or of none, not {panels}')
        return panels == 'SAVE'

    def picked(self):
        items = ['CONTINUE GAME', 'DELETE SAVE'] if self.saved() else ['START GAME']
        return items[self.game.ram('picked')]

    def greeting(self):
        """Whether the dwarf's greeting is up."""
        game = self.game
        return game.ram('talk_state') != game.sym['TALK_OFF'] and game.ram('showing') == game.sym['TALK_GREENHORN']


def main():
    folder = save_dir()

    # A first run, with no save: the title has START GAME alone, and the
    # dwarf's greeting, who has no OK and stays while the menu takes the
    # input, with the cursor round START GAME. It starts at once.
    game = Game()
    game.boot()
    game.run(60)
    title = Title(game)
    check(not title.saved() and title.picked() == 'START GAME', 'Start Game alone with no save')
    check(title.greeting() and game.ram('talk_state') == game.sym['TALK_WAIT'], 'and the dwarf greets, and stays')
    check(game.shown('XRAM_CURSOR_SPRITES', 4) == 4, 'with the cursor round Start Game')
    image = lambda: game.xram('XRAM_DWARF_IMAGES', game.sym['DWARF_BYTES'])
    was = image()
    game.run(game.sym['TAPE_STEPS'] * 3)
    check(image() == was, 'nothing writes over him while he stays, such as the tape of a menu')
    game.tap('up')
    game.tap('down')
    check(title.picked() == 'START GAME' and title.greeting(), 'up and down stay on it, and he stays')
    check(read_save(folder) is None, 'no save yet')
    game.new_game()
    check(read_save(folder) == NEW_GAME, 'a level starting saves a new game')
    check(game.ram('showing') == game.sym['TALK_WELCOME'], "and the greeting went with the title, for level 1's")
    print('ok: a new game from the greeting, saved when the level starts')

    # Pausing saves the nuggets, with those still on their way, and holds
    # the game still. Esc again, or Start, carries on.
    game.tap('space')
    game.wait('brick', 600)
    game.run(3)
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.run(2)
    check(all(game.shows(w) for w in ['PAUSED', 'RESUME', 'THE DRY', 'RESTART', 'MAIN MENU']),
          'the pause menu')
    broken = game.sym['LEVEL1_BRICKS'] - game.ram('bricks_left')
    saved = read_save(folder)
    check(saved and saved[0] == broken, f'pausing saves a nugget for each broken brick, {saved} for {broken}')
    welcome = 1 << game.sym['TALK_WELCOME'] - 1
    check(saved[6] == welcome, "and that the dwarf's welcome was seen")
    check(saved[7] == 1 << game.sym['BRICK_GRAY'], "and that the gray nuggets' line of the counts shows")
    ball = 'XRAM_BALL_SPRITE'
    tape = f'XRAM_MENU_PALETTE+{game.sym["MENU_TAPE"] * 2}'
    where, energy = game.sprite(ball), game.ram('energy', 2)
    game.run(30)
    check(game.sprite(ball) == where and game.ram('energy', 2) == energy, 'nothing moves while paused')
    stripes = game.xram(tape, 8)
    game.run(game.sym['TAPE_STEPS'] * 2)  # two places of four, so never all the way round
    check(game.xram(tape, 8) != stripes, 'but the caution tape marches')
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

    # The level ends, and that saves too.
    os.remove(os.path.join(folder, SAVE))
    game.paused_poke([('balls', 0, 1), ('ball_y', 225 << 8, 4), ('ball_vx', 0, 2), ('ball_vy', 600, 2)])
    game.wait('out of balls', 60)
    game.run(2)
    broken = game.sym['LEVEL1_BRICKS'] - game.ram('bricks_left')
    check(read_save(folder) and read_save(folder)[0] == broken, f'a level ending saves, {broken} nuggets')

    # Esc does nothing on the menu when a level ends. Replay plays the level
    # again, which saves, with its curtains, texture and frame as they were.
    game.run(70)
    game.tap('escape')
    game.run(5)
    check(game.ram('game_state') == game.sym['STATE_MENU'] and not game.shows('PAUSED'),
          'Esc does nothing on the menu')
    os.remove(os.path.join(folder, SAVE))
    def look():
        """The level's curtain set, its texture's place, and its frame set's colors."""
        return game.ram('curtain_set'), game.xram('XRAM_TEXTURE_CONFIG', 8), game.xram('XRAM_FRAME_PALETTE', 32)
    cave = look()
    game.menu_choose('REPLAY', wait=False)
    game.wait('level 1 start', 30)  # logged once it has saved
    check(read_save(folder) is not None, 'the level starting saves')
    check(look() == cave, 'the level played again keeps its curtains, its texture and its frame')

    # Restart from the pause menu starts the level over, and keeps them too.
    game.paused_poke([('bricks_left', 3, 1)])
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.tap('down')
    game.tap('down')  # RESTART
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    check(game.ram('bricks_left') == game.sym['LEVEL1_BRICKS'],
          'Restart starts the level over')
    check(look() == cave, 'with its curtains, texture and frame')
    print('ok: Replay and Restart')

    # A purchase on the upgrade screen saves. Esc there asks to go back to
    # the title, which has the save's panels now.
    game.ready()
    game.paused_poke([('balls', 0, 1), ('ball_state', 1, 1), ('ball_y', 225 << 8, 4), ('ball_vx', 0, 2),
                      ('ball_vy', 600, 2)])
    game.wait('out of balls', 3000)
    game.menu_choose('THE DRY')
    game.talk_ok()
    game.poke('nuggets', 20, 2)
    left = 20 - game.ram('width_costs', 2)  # after the first width
    game.tap('enter')
    game.wait('bought width 1', 10)
    check(read_save(folder)[:3] == (left, 0, (1,) + NO_RANKS[1:]), 'buying saves the upgrade bought')
    game.tap('escape')
    check(game.shows('RETURN TO TITLE?'), 'Esc asks to go back to the title')
    game.tap('space')  # YES
    game.until('game_state', 'STATE_TITLE', 60)
    game.run(5)
    title = Title(game)
    check(title.saved() and title.picked() == 'CONTINUE GAME', 'Continue Game is there now, picked')
    check(re.fullmatch(r'PROGRESS ( \d|\d\d)%', game.progress()),
          f'with the progress, a space more under 10%, so it centers: {game.progress()!r}')
    check(not title.greeting(), 'and no dwarf')
    game.close()

    # Another run, as when the player comes back: Continue Game brings back
    # the nuggets and the upgrade.
    game = Game()
    game.boot()
    game.run(3)
    title = Title(game)
    check(title.picked() == 'CONTINUE GAME', 'Continue Game is picked when the player comes back')

    # Left and right don't move a menu. On the title, Shift and right or left
    # switch the curtains, and with Shift, down doesn't move the menu.
    for key in ['right', 'left']:
        game.tap(key)
        check(title.picked() == 'CONTINUE GAME', f'{key} does not move the menu')
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
    check(title.picked() == 'CONTINUE GAME', 'with Shift, down does not move the menu')
    print(f'ok: left and right leave the menu, and Shift switches the {sets} curtain sets')
    game.tap('space')
    game.until('game_state', 'STATE_SHOP', 120)
    check(game.ram('nuggets', 2) == left, 'Continue Game opens the upgrade screen with the nuggets')
    check(game.shown('XRAM_NUGGET_ICONS', game.sym['BRICK_COLORS']) == 1, 'and their line of the counts')
    check(game.ram('upgrade_ranks') == 1, 'and the upgrade')
    check(game.ram('cursor_on') == game.sym['SHOP_ON_LEVELS'], 'on the level select, coming from the title')
    game.tap('space')
    game.tap('space')  # YES, begin the level
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(2)
    check(game.ram('paddle_width') == game.ram('widths+1'), 'the level has the upgrade, on the paddle')
    print(f'ok: came back, and Continue Game brought back {left} nuggets and a wider paddle')

    # Main Menu from the pause menu goes to the title. Delete Save asks
    # first, in the panels' place, with No picked. Esc and No keep the save.
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    for _ in range(3):
        game.tap('down')  # MAIN MENU
    game.tap('space')
    game.until('game_state', 'STATE_TITLE', 60)
    game.run(2)
    asked = lambda: game.shows('DELETE SAVE?') and game.title_panels() is None
    game.tap('down')   # DELETE SAVE
    game.tap('space')
    check(asked() and game.ram('picked') == 1, 'Delete Save asks first, in place of the panels, No picked')
    game.tap('escape')
    check(not game.shows('DELETE SAVE?') and title.picked() == 'DELETE SAVE', 'Esc is No')
    game.tap('space')  # DELETE SAVE, picked after Esc
    check(asked(), 'it asks again')
    game.tap('space')  # NO, picked first
    check(not game.shows('DELETE SAVE?') and title.picked() == 'DELETE SAVE', 'No goes back to the panels')
    check(read_save(folder)[:3] == (left, 0, (1,) + NO_RANKS[1:]), 'and No keeps the save')

    # With every level cleared and every upgrade bought, the progress says
    # so, when the panels come back.
    tops = game.ram('ranks', game.sym['UPGRADES']).to_bytes(game.sym['UPGRADES'], 'little')
    game.poke('levels_cleared', game.sym['LEVELS'])
    for u, top in enumerate(tops):
        game.poke(f'upgrade_ranks+{u}', top)
    game.tap('space')  # DELETE SAVE
    game.tap('space')  # NO
    check(game.progress() == '100% COMPLETE!', f'at 100%: {game.progress()!r}')

    # Yes deletes it, and the title of none comes at once, with no game
    # started: Start Game, and the dwarf.
    game.tap('space')  # DELETE SAVE, picked after No
    game.tap('up')     # YES
    game.cmd('press space')
    game.wait('deleted', 10)
    game.cmd('release space')
    check(read_save(folder) is None, 'Yes deletes the save')
    game.run(2)
    check(not game.shows('DELETE SAVE?') and not title.saved() and title.picked() == 'START GAME',
          'and the panels of none come at once')
    check(game.ram('game_state') == game.sym['STATE_TITLE'], 'and no game starts')
    game.run(30)
    check(title.greeting() and game.shown('XRAM_CURSOR_SPRITES', 4) == 4,
          'and the dwarf greets the player, with the cursor round Start Game')
    check(game.ram('nuggets', 2) == 0 and game.ram('upgrade_ranks') == 0, 'and the game is a new one')
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(2)
    check(read_save(folder) == NEW_GAME, 'Start Game saves a new game')
    check(game.ram('showing') == game.sym['TALK_WELCOME'] and game.ram('paddle_width') == game.ram('widths'),
          'and starts over, with the welcome')
    print('ok: Delete Save asked first, Esc and No kept the save, and Yes deleted it')
    game.close()

    # A save that isn't one is no save.
    open(os.path.join(folder, SAVE), 'wb').write(b'NOPE, not a save')
    game = Game()
    game.boot()
    game.run(5)
    check(not Title(game).saved(), 'a bad save file is no save')
    game.close()
    print('ok: a bad save is ignored')

    # The web player keeps its saves between visits.
    page = os.path.join(os.path.dirname(os.path.dirname(rom())), 'web', 'quarry', 'index.html')
    check("db: 'rumbledethumps-quarry'" in open(page).read(), 'the web player keeps its saves')
    print('PASS')


if __name__ == '__main__':
    main()
