#!/usr/bin/env python3
"""Works every control in the emulator.

  controls.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The paddle starts centered
in the playfield and moves 2 px a step: each move must reach 12 px to the
side, and the paddle must stop when the control is let go. Each test starts
from the same saved state, with the ball on the paddle. Exits 0 when every
check passes.
"""

import os
import tempfile

from game import Game, check

MOVES = [('d', 'right'), ('a', 'left'), ('right', 'right'), ('left', 'left'),
         ('kp6', 'right'), ('kp4', 'left')]
LAUNCH_KEYS = ['space', 'enter', 'lctrl', 'rctrl', 'kp0', 'kpenter']
LAUNCH_BUTTONS = [(0, 'a'), (0, 'b'), (0, 'x'), (1, 'y')]


def main():
    state = os.path.join(tempfile.mkdtemp(), 'controls.state')
    game = Game()
    num_lock = 1 << game.sym['KEYBOARD_NUM_LOCK']  # in the first byte of the key bitmap
    start_balls = game.sym['TUNE_BALLS']

    # Enter held from boot, as when it loaded the game, does not choose on the
    # title screen.
    game.cmd('press enter')
    game.boot()
    game.run(30)
    game.cmd('release enter')
    game.run(5)
    check(game.ram('game_state') == game.sym['STATE_TITLE'], 'a key held from boot does not choose')

    # Nor does a choose held into play get past the dwarf's welcome, which
    # takes the input while he is up, or launch once he has gone.
    game.cmd('press enter')
    game.until('game_state', 'STATE_PLAY')
    game.until('talk_state', 'TALK_READY', 120)
    game.run(10)
    game.cmd('release enter')
    game.run(5)
    check(game.ram('talk_state') == game.sym['TALK_READY'], 'a key held into play does not pass the dwarf')
    game.talk_ok()
    game.cmd('expect-not "launch"')

    game.run(2)
    paddle = game.sym['XRAM_SLED_SPRITE']
    start_x = (game.ram('play_left', 2) + game.ram('play_right', 2) - game.ram('paddle_width')) // 2
    check(game.sprite(paddle) == (start_x, game.sym['TUNE_PADDLE_Y']),
          f'the paddle starts centered, at {start_x}')
    game.cmd('pad 0 connect')
    game.cmd('pad 1 connect')
    game.run(2)
    game.cmd(f'state save "{state}"')

    def move(press, release, direction, label):
        game.cmd(f'state load "{state}"')
        game.cmd(press)
        target = start_x + 12 if direction == 'right' else start_x - 12
        game.cmd(f'wait xram:{paddle} {target} 30')
        game.cmd(release)
        game.run(3)
        x = game.sprite(paddle)[0]
        game.run(10)
        check(game.sprite(paddle)[0] == x, f'{label}: the paddle stops when let go')
        print(f'ok: {label}')

    check(game.xram('XRAM_KEYBOARD', 1)[0] & num_lock, 'Num Lock is on when the emulator starts')
    for key, direction in MOVES:
        move(f'press {key}', f'release {key}', direction, f'{key} moves {direction}, Num Lock on')

    game.cmd(f'state load "{state}"')
    game.cmd('lock num')
    game.run(2)
    check(not game.xram('XRAM_KEYBOARD', 1)[0] & num_lock, 'Num Lock is off')
    game.cmd(f'state save "{state}"')
    for key, direction in MOVES[4:]:
        move(f'press {key}', f'release {key}', direction, f'{key} moves {direction}, Num Lock off')
    game.cmd(f'state load "{state}"')
    game.cmd('lock num')
    game.run(2)
    check(game.xram('XRAM_KEYBOARD', 1)[0] & num_lock, 'Num Lock is on again')
    game.cmd(f'state save "{state}"')

    for direction in ['left', 'right']:
        move(f'pad 0 press {direction}', f'pad 0 release {direction}', direction,
             f'gamepad d-pad {direction}')
    move('pad 1 stick -128 0 0 0', 'pad 1 stick 0 0 0 0', 'left', 'gamepad 2 left stick left')
    move('pad 1 stick 127 0 0 0', 'pad 1 stick 0 0 0 0', 'right', 'gamepad 2 left stick right')

    for key in LAUNCH_KEYS:
        game.cmd(f'state load "{state}"')
        game.cmd(f'press {key}')
        game.wait(f'launch, {start_balls - 1} balls left', 5)
        game.cmd(f'release {key}')
        print(f'ok: {key} launches')
    for pad, button in LAUNCH_BUTTONS:
        game.cmd(f'state load "{state}"')
        game.cmd(f'pad {pad} press {button}')
        game.wait(f'launch, {start_balls - 1} balls left', 5)
        game.cmd(f'pad {pad} release {button}')
        print(f'ok: gamepad {pad + 1} button {button} launches')
    # Up doesn't launch, from a key or a gamepad.
    for press, release in [('press w', 'release w'), ('press up', 'release up'),
                           ('press kp8', 'release kp8'), ('pad 0 press up', 'pad 0 release up'),
                           ('pad 1 stick 0 -128 0 0', 'pad 1 stick 0 0 0 0')]:
        game.cmd(f'state load "{state}"')
        game.cmd(press)
        game.run(10)
        game.cmd('expect-not "launch"')
        game.cmd(release)
    print('ok: up does not launch')

    # A held launch control launches only once, even when the ball is back
    # on the paddle while it is still held.
    game.cmd(f'state load "{state}"')
    game.cmd('press space')
    game.wait(f'launch, {start_balls - 1} balls left', 5)
    game.run(10)
    game.poke('ball_state', 0)
    game.run(30)
    game.cmd(f'expect-not "launch, {start_balls - 2} balls left"')
    game.cmd('release space')
    game.run(2)
    game.cmd('press space')
    game.wait(f'launch, {start_balls - 2} balls left', 5)
    game.cmd('release space')
    print('ok: a held launch launches once')

    # The cheats of a debug build: Shift and right or left adds a ball or
    # takes one away, and Shift and up or down a segment of energy. With
    # Shift, the arrows neither move nor launch.
    game.cmd(f'state load "{state}"')
    x, balls, energy = game.sprite(paddle)[0], game.ram('balls'), game.ram('energy', 2)
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('balls') == balls + 1, 'Shift and right adds a ball')
    game.tap('left')
    game.tap('left')
    check(game.ram('balls') == balls - 1, 'Shift and left takes one away')
    game.tap('down')
    check(game.ram('energy', 2) == energy - game.sym['SEGMENT_ENERGY'], 'Shift and down takes energy')
    game.tap('up')
    check(game.ram('energy', 2) == energy, 'Shift and up gives it back')
    check(game.sprite(paddle)[0] == x, 'with Shift, the arrows do not move the paddle')
    game.cmd('expect-not "launch"')
    game.cmd('release lshift')
    print('ok: the cheats')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
