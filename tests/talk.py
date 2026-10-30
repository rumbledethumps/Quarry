#!/usr/bin/env python3
"""Checks the dwarves' talks in the emulator: the foreman's at the start of a
new game, his bubbles one after another, the committeeman's coin for a
first clear before the menu, on the right, and on the upgrade screen, the
first unlock's and the screen's, one after the other while the unlock goes
on. Then the test keys that bring in each talk.

  talk.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Reads where the dwarf and
his bubble stand from the talk in XRAM, and the menus' and the dwarves' art
from menus.bin and dwarves.bin beside the ROM's folder. Exits 0 when every
check passes.
"""

import os
import struct
import tempfile

from game import Game, check, rom

DWARF = '<hhBB'  # dwarf_head_t of src/xram.h, then its pieces
PIECE = '<hhHBB'
BUBBLE = '<hhBBBBBBBB'  # bubble_head_t
PAPER = (250, 246, 234)  # the bubble's, in art/talk.py
FILL = (2, 13, 26)       # inside a menu, in art/menus.py


def near(rgb, color):
    """Whether a pixel of the screen is the color, as the VGA's 5 bits a
    channel show it."""
    return all(abs(a - b) <= 8 for a, b in zip(rgb, color))


def heads(game):
    """The dwarf's head, with his pieces, and his bubble's, as they are in
    XRAM."""
    pieces = game.sym['DWARF_PIECES']
    data = game.xram('XRAM_TALK_DWARF', struct.calcsize(DWARF) + pieces * struct.calcsize(PIECE))
    dwarf_x, dwarf_y, count, _ = struct.unpack_from(DWARF, data)
    parts = [struct.unpack_from(PIECE, data, struct.calcsize(DWARF) + i * struct.calcsize(PIECE))
             for i in range(count)]
    bubble = struct.unpack(BUBBLE, game.xram('XRAM_TALK_BUBBLE', struct.calcsize(BUBBLE)))
    return (dwarf_x, dwarf_y, parts), bubble


def main():
    game = Game()
    sym = game.sym
    shot = os.path.join(tempfile.mkdtemp(), 'talk.png')
    game.boot()
    game.tap('space')  # START GAME
    game.until('game_state', 'STATE_PLAY')
    game.until('talk_state', 'TALK_IN', 10)

    (dwarf_x, dwarf_y, parts), (bubble_x, bubble_y, rows, cols, ok_col, ok_row, ok0, ok1, *_) = heads(game)
    count = len(parts)
    pieces = sym['DWARF_PIECES']
    dwarf, cursor, hidden = sym['XRAM_DWARF_SPRITES'], sym['XRAM_CURSOR_SPRITES'], sym['SPRITE_HIDDEN_Y']
    bubble = lambda: struct.unpack('<h', game.xram(f'XRAM_TALK_CONFIG+2', 2))[0]
    ok = f'XRAM_BUBBLE_MAP+{ok_row * sym["BUBBLE_COLS"] + ok_col}'
    check(game.ram('showing') == sym['TALK_FOREMAN'] and dwarf_x == sym['SCREEN_W'] - sym['DWARF_SIZE'],
          'the foreman, on the right')

    # He comes up from the foot of the screen as his bubble comes in from the
    # left, the other side, and both stop at once.
    game.run(2)
    first = game.sprite(dwarf), bubble()
    game.run(4)
    second = game.sprite(dwarf), bubble()
    check(first[0][1] > second[0][1] and first[1] < second[1], f'they come in together: {first}, {second}')
    game.until('talk_state', 'TALK_WAIT', 30)
    game.run(1)
    check([(x, y) for x, y, _ in game.sprites(dwarf, count)] == [(dwarf_x + x, dwarf_y + y) for x, y, *_ in parts],
          'the dwarf stops in his place')
    check(bubble() == bubble_x, 'and his bubble in its place')
    check(game.shown(cursor, 4) == 0 and game.xram(ok, 2) != bytes([ok0, ok1]), 'with no OK yet')
    print(f'ok: the dwarf came in to {dwarf_x}, {dwarf_y}, his bubble to {bubble_x}, {bubble_y}')

    # A moment later the OK shows, with the cursor round it. Esc does nothing.
    game.until('talk_state', 'TALK_READY', 60)
    game.run(2)
    check(game.xram(ok, 2) == bytes([ok0, ok1]), 'the OK shows')
    screen = game.screen(shot)
    inside = screen[bubble_y + 2 * 8 + 4][bubble_x + 2 * 8 + 4]  # between his first two lines
    check(near(inside, PAPER), f'the bubble shows on plane 2: {inside}')
    left, top = bubble_x + ok_col * 8 - 4, bubble_y + ok_row * 8 - 5
    corners = game.sprites(cursor, 4)
    size = sym['CURSOR_SIZE']
    check(left - 2 <= corners[0][0] <= left and top - 2 <= corners[0][1] <= top and
          left + 24 - size <= corners[3][0] <= left + 26 - size and
          top + 17 - size <= corners[3][1] <= top + 19 - size, f'the cursor goes round the OK: {corners}')
    game.tap('escape')
    game.run(5)
    check(game.ram('talk_state') == sym['TALK_READY'] and game.ram('game_state') == sym['STATE_PLAY'],
          'Esc does nothing while he talks')
    print('ok: the OK, with the cursor')

    # The button sends his bubble back the way it came, and his next comes
    # in the same way, while he stays. Its OK shows a moment later, as the
    # first's did.
    first_bubble = game.ram('said')
    stays = lambda: [(x, y) for x, y, _ in game.sprites(dwarf, count)] == \
        [(dwarf_x + x, dwarf_y + y) for x, y, *_ in parts]
    game.tap('space')
    check(game.ram('talk_state') == sym['TALK_NEXT'] and game.shown(cursor, 4) == 0,
          'the button sends his bubble away, and the cursor goes')
    going = []
    while game.ram('talk_state') == sym['TALK_NEXT']:
        going.append(bubble())
        check(stays(), 'and he stays')
        game.run(1)
    check(going == sorted(going, reverse=True) and going[-1] < going[0], f'his bubble goes back to the left: {going}')
    check(game.ram('said') == first_bubble + 1, 'and his next')
    coming = []
    while game.ram('talk_state') == sym['TALK_IN']:
        coming.append(bubble())
        check(stays(), 'and he stays')
        game.run(1)
    _, (x, _, _, next_cols, *_) = heads(game)
    game.run(1)
    check(coming == sorted(coming) and bubble() == x and x + 8 * next_cols == bubble_x + 8 * cols,
          f'comes in from the left, its right edge where the last one\'s was: {coming}')
    game.until('talk_state', 'TALK_READY', 60)
    game.tap('space')
    game.until('talk_state', 'TALK_READY', 120)
    check(game.ram('said') == first_bubble + 2, 'his third bubble')
    _, (_, _, _, last_cols, *_) = heads(game)
    print('ok: his bubbles, one after another')

    # The button after his last sends them away, and doesn't launch. The
    # menus come back.
    game.tap('space')
    check(game.ram('talk_state') == sym['TALK_OUT'] and game.shown(cursor, 4) == 0,
          'the button sends them away, and the cursor goes')
    game.until('talk_state', 'TALK_OFF', 30)
    game.run(2)
    check(game.shown(dwarf, pieces) == 0 and (bubble() >= 320 or bubble() + 8 * last_cols <= 0), 'they are gone')
    game.ready()
    check(game.ram('ball_state') == sym['BALL_DOCKED'] and not game.ram('energy_draining'),
          'the press that sent them away did not launch')
    menus = open(os.path.join(os.path.dirname(os.path.dirname(rom())), 'menus.bin'), 'rb').read()
    check(game.xram('XRAM_MENU_PALETTE', len(menus)) == menus, "the menus' art is back")
    left, right = game.ram('play_left', 2), game.ram('play_right', 2)
    field = lambda rows: [row[left:right] for row in rows[70:140]]  # under the bricks, over the paddle
    after = field(game.screen(shot))
    game.tap('escape')
    game.until('game_state', 'STATE_PAUSE', 10)
    game.run(2)
    box = game.screen(shot)[8 * 8 + 4][11 * 8 + 4]  # inside the pause menu, under its top edge
    check(game.shows('PAUSED') and near(box, FILL), f'and the menus show on plane 2: {box}')
    print('ok: the button sent them away, and the menus came back')

    # Restart doesn't bring the foreman again.
    for _ in range(2):
        game.tap('down')  # RESTART
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    game.ready()
    check(game.ram('talk_state') == sym['TALK_OFF'], "the foreman's word is only once")
    check(field(game.screen(shot)) == after, 'and he left nothing on the screen')
    print("ok: the foreman's word is only once, and he left nothing behind")

    # A first clear: the committeeman hands over the coin, from the right,
    # his bubble coming in from the left, and then the menu opens, with the
    # cursor.
    talk = lambda name: game.wait(f'talk {sym[name]}\\n', 30)  # the line's end, so 1 is not 11
    game.tap('space')
    game.run(20)
    game.paused_poke([('bricks_left', 0, 1)])
    game.wait('level cleared', 10)
    game.run(1)
    game.cmd('expect-not "menu THE DRY"')  # the end menu, as menu_open() logs it
    talk('TALK_COIN1')
    game.run(2)
    (dwarf_x, _, _), (bubble_x, bubble_y, _, cols, *_, coin_x, coin_y) = heads(game)
    check(dwarf_x == sym['SCREEN_W'] - sym['DWARF_SIZE'] and bubble_x + 8 * cols < dwarf_x + 16,
          f'the committeeman on the right, his bubble to his left: {dwarf_x}, {bubble_x}')
    coming = bubble()
    game.run(3)
    check(coming < bubble() <= bubble_x, f'coming in from the left: {coming}, {bubble()}')
    coin = sym['XRAM_BIG_COIN_SPRITE']
    check(game.sprite(coin) == (bubble() + coin_x, bubble_y + coin_y), 'the big coin coming in with it')
    game.run(30)
    check(bubble() == bubble_x, 'to its place')
    check(game.sprite(coin) == (bubble_x + coin_x, bubble_y + coin_y) and coin_y and coin_x < 8 * cols // 2,
          f'the big coin in the left of the bubble: {game.sprite(coin)}')
    check(not game.shows('LEVEL COMPLETE'), 'the dwarf with the coin comes before the menu')
    game.talk_ok()
    check(game.shows('LEVEL COMPLETE') and game.shown(cursor, 4) == 4, 'then the menu, with the cursor')
    check(game.sprite(coin)[1] == hidden, 'and the big coin gone with him')
    game.tap('space')
    check(game.ram('game_state') == sym['STATE_MENU'], 'which takes no choice at once')
    print('ok: the coin, then the menu')

    # The upgrade screen: as level 2 unlocks, the foreman says what that
    # means, and the unlock goes on under him. Then another says what the
    # screen is for, in two bubbles. The cursor is off until each OK, and comes back to the rail after.
    game.run(sym['TALK_OVER_WAIT'])
    game.tap('space')  # THE DRY
    game.until('game_state', 'STATE_SHOP', 60)
    talk('TALK_UNLOCK')
    check(game.shown(cursor, 4) == 0, 'no cursor while he comes in')
    icon = sym['XRAM_MENU_SPRITES'] + (game.ram('panel_picked') % sym['PANEL_SLOTS'] * sym['PANEL_SPRITES'] +
                                       sym['PICTURE_SPRITES']) * \
        sym['SPRITE_BYTES']
    check(game.shown(icon, 1) == 0, "nor the cost icon that would show over his bubble")
    game.until('talk_state', 'TALK_READY', 120)
    size = sym['DWARF_ASSET_BYTES']
    dwarves = open(os.path.join(os.path.dirname(os.path.dirname(rom())), 'dwarves.bin'), 'rb').read()
    art = game.xram('XRAM_TALK_DWARF', size)  # his head, colors and image
    check(art in [dwarves[i:i + size] for i in range(0, len(dwarves), size)], 'his art is one of the dwarves')
    game.wait('unlocked 2', 200)
    game.run(20)
    check(game.ram('talk_state') == sym['TALK_READY'], 'the unlock goes on while he talks')
    check(game.xram('XRAM_TALK_DWARF', size) == art, 'and nothing writes over him')
    corner = game.sprite(cursor)
    check(corner[1] > 120, f'the cursor stays on his OK, not the rail, as the new level is picked: {corner}')
    game.tap('space')
    check(game.shown(cursor, 4) == 0, 'the cursor goes with his OK')
    talk('TALK_DRY')
    check(game.shown(cursor, 4) == 0, 'and stays off as the next comes in')
    game.talk_ok()
    game.run(2)
    check(game.ram('cursor_on') == sym['ON_RAIL'] and game.shown(cursor, 4) == 4, 'then it comes back to the rail')
    check(game.shown(icon, 1) == 1, 'and the cost icon comes back')
    print('ok: the unlock, the upgrade screen, and the cursor back')

    # The next first clear has a coin but no more of the upgrade screen's.
    game.tap('down')
    game.tap('space')
    game.tap('space')  # YES, begin level 2
    game.until('game_state', 'STATE_PLAY', 60)
    game.run(5)
    check(game.ram('talk_state') == sym['TALK_OFF'], 'no foreman on level 2')
    game.ready()
    game.tap('space')
    game.run(20)
    game.paused_poke([('bricks_left', 0, 1)])
    game.wait('level cleared', 10)
    talk('TALK_COIN2')
    game.talk_ok()
    game.menu_choose('THE DRY')
    game.wait('unlocked 3', 200)
    check(game.ram('talk_state') == sym['TALK_OFF'], 'the unlock and the screen are told of once')
    print('ok: the second first clear')

    # In a debug build, Shift and the top row's letters bring in the talks
    # but the coins', in order, and Shift and a level's number the coin's
    # for that level as Shift is let go, its own or the first level's. The
    # screen comes back after each.
    def shift_keys(keys, name):
        game.cmd('press lshift')
        for key in keys:
            game.tap(key)
        if keys.isdigit():
            game.run(2)
            check(game.ram('talk_state') == sym['TALK_OFF'], f'Shift and {keys} waits for Shift to go')
        game.cmd('release lshift')
        talk(name)
        game.talk_ok()

    shift_keys('e', 'TALK_FOREMAN')
    check(game.ram('cursor_on') == sym['ON_RAIL'] and game.shown(cursor, 4) == 4,
          'Shift and E brings in the foreman on the upgrade screen, and its cursor comes back')
    shift_keys('3', 'TALK_COIN3')
    shift_keys('12', 'TALK_COIN1')
    print("ok: Shift and a level's number brings in its coin's talk, and the first's past them")
    game.tap('escape')
    game.tap('space')  # YES, return to the title
    game.until('game_state', 'STATE_TITLE', 60)
    game.run(5)
    shift_keys('w', 'TALK_DRY')
    check(game.ram('game_state') == sym['STATE_TITLE'] and game.title_panels() == 'SAVE',
          'and Shift and W a talk on the title, which comes back after')
    print('ok: Shift and a letter brings in a talk')
    print('PASS')


if __name__ == '__main__':
    main()
