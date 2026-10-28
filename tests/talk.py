#!/usr/bin/env python3
"""Checks a dwarf's talk, the welcome at the start of a new game, in the
emulator.

  talk.py rom.rp6502

Needs a Debug ROM, which logs the game's events. Reads where the dwarf and
his bubble stand from the talk in XRAM, and the menus' art from menus.bin
beside the ROM's folder. Exits 0 when every check passes.
"""

import os
import struct
import tempfile

from game import Game, check, rom

HEAD = '<hhhhBBBBBB'  # talk_head_t of src/xram.h, then its pieces
PIECE = '<hhHBB'
PAPER = (250, 246, 234)  # the bubble's, in art/talk.py
FILL = (2, 13, 26)       # inside a menu, in art/menus.py


def near(rgb, color):
    """Whether a pixel of the screen is the color, as the VGA's 5 bits a
    channel show it."""
    return all(abs(a - b) <= 8 for a, b in zip(rgb, color))


def main():
    game = Game()
    sym = game.sym
    shot = os.path.join(tempfile.mkdtemp(), 'talk.png')
    game.boot()
    game.tap('space')  # NEW GAME
    game.until('game_state', 'STATE_PLAY')
    game.until('talk_state', 'TALK_IN', 10)

    pieces = sym['DWARF_PIECES']
    data = game.xram('XRAM_TALK', struct.calcsize(HEAD) + pieces * struct.calcsize(PIECE))
    dwarf_x, dwarf_y, bubble_x, bubble_y, rows, ok_col, ok_row, ok0, ok1, count = \
        struct.unpack_from(HEAD, data)
    parts = [struct.unpack_from(PIECE, data, struct.calcsize(HEAD) + i * struct.calcsize(PIECE))
             for i in range(count)]
    dwarf, cursor, hidden = sym['XRAM_DWARF_SPRITES'], sym['XRAM_CURSOR_SPRITES'], sym['SPRITE_HIDDEN_Y']
    bubble = lambda: struct.unpack('<h', game.xram(f'XRAM_TALK_CONFIG+2', 2))[0]
    ok = f'XRAM_BUBBLE_MAP+{ok_row * sym["BUBBLE_COLS"] + ok_col}'

    # He comes up from the foot of the screen as his bubble comes in from the
    # right, and both stop at once.
    game.run(2)
    first = game.sprite(dwarf), bubble()
    game.run(4)
    second = game.sprite(dwarf), bubble()
    check(first[0][1] > second[0][1] and first[1] > second[1], f'they come in together: {first}, {second}')
    game.until('talk_state', 'TALK_WAIT', 30)
    game.run(1)
    check([game.sprite(dwarf + i * 10) for i in range(count)] == [(dwarf_x + x, dwarf_y + y) for x, y, *_ in parts],
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

    # The button sends them away, and doesn't launch. The menus come back.
    game.tap('space')
    check(game.ram('talk_state') == sym['TALK_OUT'] and game.shown(cursor, 4) == 0,
          'the button sends them away, and the cursor goes')
    game.until('talk_state', 'TALK_OFF', 30)
    game.run(2)
    check(game.shown(dwarf, pieces) == 0 and bubble() >= 320, 'they are gone')
    check(game.ram('balls') == sym['TUNE_BALLS'] and game.ram('ball_state') == sym['BALL_DOCKED'],
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

    # Restart doesn't welcome the player again.
    for _ in range(2):
        game.tap('down')  # RESTART
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    game.run(30)
    check(game.ram('talk_state') == sym['TALK_OFF'], 'the welcome is only once')
    check(field(game.screen(shot)) == after, 'and he left nothing on the screen')
    print('PASS')


if __name__ == '__main__':
    main()
