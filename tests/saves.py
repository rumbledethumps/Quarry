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
TAG = b'QRY9'
SYM = Symbols(os.path.splitext(rom())[0] + '.sym')
COLORS = SYM['BRICK_COLORS']
NO_NUGGETS = (0,) * COLORS
NO_RANKS = (0,) * SYM['UPGRADES']
NEW_GAME = (NO_NUGGETS, 0, NO_RANKS, 0, 1, 1, 0, 0)  # as read_save() gives it


def read_save(folder):
    """The save, save_t of src/save.c, as (the nuggets of each color, coins,
    upgrade ranks, levels cleared, level picked, levels shown open, talks
    seen, lines of the counts shown), or None, with no file or an empty
    one, as Delete Save leaves it."""
    path = os.path.join(folder, SAVE)
    if not os.path.exists(path) or not os.path.getsize(path):
        return None
    data = open(path, 'rb').read()
    check(len(data) == SYM['SAVE_BYTES'] and data[:4] == TAG, f'the save is a good one: {data!r}')
    colors, upgrades = SYM['BRICK_COLORS'], SYM['UPGRADES']
    values = struct.unpack(f'<{colors}HH{upgrades}B5B', data[4:])
    nuggets, coins = values[:colors], values[colors]
    ranks, rest = values[colors + 1:colors + 1 + upgrades], values[colors + 1 + upgrades:]
    return (nuggets, coins, ranks) + rest


def table(game, name, size):
    """size bytes of the game's RAM from name."""
    return game.ram(name, size).to_bytes(size, 'little')


def nuggets(game):
    """The nuggets of each color, in the game's RAM."""
    return struct.unpack(f'<{COLORS}H', table(game, 'nuggets', 2 * COLORS))


def broken(game):
    """The bricks broken in the level, of each color."""
    bricks = game.ram('brick_count')
    alive, color = table(game, 'brick_alive', bricks), table(game, 'brick_color', bricks)
    return tuple(sum(not a and c == k for a, c in zip(alive, color)) for k in range(COLORS))


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
    check(game.ram('showing') == game.sym['TALK_FOREMAN'], "and the greeting went with the title, for the foreman's")
    print('ok: a new game from the greeting, saved when the level starts')

    # Pausing saves the nuggets, with those still on their way, and holds
    # the game still. Esc again, or Start, carries on. So that a brick
    # breaks at once, whatever the level, every brick breaks at a hit, and
    # the ball, once launched, is put under the lowest brick, flying
    # straight up, with spare balls so play goes on after it falls.
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    bricks, flying = game.ram('brick_count'), game.sym['BALL_FLYING']
    ys = struct.unpack(f'<{bricks}h', table(game, 'brick_y', 2 * bricks))
    x, y = game.ram(f'brick_x+{2 * ys.index(max(ys))}', 2), max(ys)
    game.paused_poke([(f'brick_hits+{i}', 1, 1) for i in range(bricks)] +
                     [('balls', 9, 1), ('ball_x', (x + (game.sym['BRICK_W'] - game.sym['BALL_SIZE']) // 2) << 8, 4),
                      ('ball_y', (y + game.sym['BRICK_H']) << 8, 4), ('ball_vx', 0, 2), ('ball_vy', -600, 2)])
    game.wait('brick', 60)
    game.run(3)
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.run(2)
    check(all(game.shows(w) for w in ['PAUSED', 'RESUME', 'TO THE DRY', 'RESTART', 'MAIN MENU']),
          'the pause menu')
    saved, gone = read_save(folder), broken(game)
    check(saved and saved[0] == gone,
          f'pausing saves a nugget of its color for each broken brick, {saved} for {gone}')
    check(saved[6] == game.sym['TALK_SEEN_FOREMAN'], "and that the foreman's word was seen")
    check(saved[7] == sum(1 << c for c, n in enumerate(gone) if n),
          'and that the lines of the counts of those colors show')
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
    print(f'ok: paused with the nuggets of {gone} saved, and carried on, and Select, P and Pause pause too')

    # The level ends, and that saves too.
    os.remove(os.path.join(folder, SAVE))
    drop = [('balls', 0, 1), ('ball_state', flying, 1), ('ball_y', 225 << 8, 4), ('ball_vx', 0, 2),
            ('ball_vy', 600, 2)]  # the last ball, falling off the bottom
    game.paused_poke(drop)
    game.wait('out of balls', 60)
    game.run(2)
    gone = broken(game)
    check(read_save(folder) and read_save(folder)[0] == gone, f'a level ending saves, {gone} nuggets')

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
    game.menu_choose('REPLAY')
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

    # A purchase on the upgrade screen saves: a ball more, on the BALLS
    # panel, wherever it is on the rail, with nuggets enough of each color
    # it costs, and 20 over. Esc there asks to go back to the title, which
    # has the save's panels now.
    game.ready()
    game.paused_poke(drop)
    game.wait('out of balls', 3000)
    game.menu_choose('TO THE DRY')
    game.talk_ok()
    balls = game.sym['UPGRADE_BALLS']
    picked = game.ram('panel_picked')
    for _ in range(abs(balls - picked)):
        game.tap('right' if balls > picked else 'left')
    check(game.ram('panel_picked') == balls, 'the rail moves to the BALLS panel')
    need = game.cost_in(balls)
    for color, count in enumerate(need):
        if count:
            game.poke(f'nuggets+{2 * color}', count + 20, 2)
    left = tuple(n - need[c] for c, n in enumerate(nuggets(game)))
    bought = tuple(int(u == balls) for u in range(game.sym['UPGRADES']))
    game.tap('enter')
    game.wait('bought balls 1', 10)
    check(read_save(folder)[:3] == (left, 0, bought), 'buying saves the upgrade bought')
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
    check(nuggets(game) == left, 'Continue Game opens the upgrade screen with the nuggets')
    shown = bin(read_save(folder)[7] & ((1 << COLORS) - 1)).count('1')  # of the nuggets' lines, not the coins'
    check(game.shown('XRAM_NUGGET_ICONS', COLORS) == shown, 'and their lines of the counts, as saved')
    check(table(game, 'upgrade_ranks', game.sym['UPGRADES']) == bytes(bought), 'and the upgrade')
    check(game.ram('cursor_on') == game.sym['SHOP_ON_LEVELS'], 'on the level select, coming from the title')
    game.tap('space')
    game.tap('space')  # YES, begin the level
    game.until('game_state', 'STATE_PLAY', 60)
    game.ready()
    check(game.ram('balls') == game.ram('ball_counts+1') - 1,
          'the level has the upgrade, a ball more, with one of them on the sled')
    print(f'ok: came back, and Continue Game brought back {sum(left)} nuggets and a ball more')

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
    check(read_save(folder)[:3] == (left, 0, bought), 'and No keeps the save')

    # With every level cleared and every upgrade bought, the progress says
    # so, when the panels come back.
    tops = table(game, 'ranks', game.sym['UPGRADES'])
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
    check(nuggets(game) == NO_NUGGETS and not game.ram('upgrade_ranks', game.sym['UPGRADES']),
          'and the game is a new one')
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(2)
    check(read_save(folder) == NEW_GAME, 'Start Game saves a new game')
    # The foreman's word holds the level, so no ball has come to the sled yet.
    check(game.ram('showing') == game.sym['TALK_FOREMAN'] and game.ram('balls') == game.ram('ball_counts'),
          "and starts over, with the foreman's word and the balls of a new game")
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
