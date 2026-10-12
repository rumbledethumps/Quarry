#!/usr/bin/env python3
"""Works every control in the emulator.

  controls.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The paddle starts centered
at x 148 and moves 2 px a step: each move must reach 160 or 136, and the
paddle must stop when the control is let go. Each test starts from the same
saved state, with the ball on the paddle. Exits 0 when every check passes.
"""

import os
import sys
import tempfile

from game import Game, check

MOVES = [('d', 'right'), ('a', 'left'), ('right', 'right'), ('left', 'left'),
         ('kp6', 'right'), ('kp4', 'left')]
LAUNCH_KEYS = ['space', 'enter', 'kp0', 'kpenter', 'w', 'up', 'kp8']
LAUNCH_BUTTONS = [(0, 'a'), (0, 'b'), (0, 'x'), (1, 'y'), (0, 'up')]
START_X = 148
NUM_LOCK = 0x02  # in the first byte of the key bitmap, with NO_KEY 0x01


def main():
    rom = sys.argv[1]
    state = os.path.join(tempfile.mkdtemp(), 'controls.state')
    game = Game(rom)

    # Enter held from boot, as when it loaded the game, does not launch.
    game.send('press enter')
    game.wait('stage start', 60)
    game.run(30)
    game.send('release enter')
    game.run(5)
    game.send('expect-not "launch"')

    game.run(2)
    paddle = game.sprite_at(game.px('paddle_x'), game.px('paddle_y'))
    check(game.sprite(paddle)[0] == START_X, f'the paddle starts at {START_X}')
    game.send('pad 0 connect')
    game.send('pad 1 connect')
    game.run(2)
    game.send(f'state save "{state}"')

    def move(press, release, direction, label):
        game.send(f'state load "{state}"')
        game.send(press)
        target = START_X + 12 if direction == 'right' else START_X - 12
        game.send(f'wait xram:{paddle} {target} 30')
        game.send(release)
        game.run(3)
        x = game.sprite(paddle)[0]
        game.run(10)
        check(game.sprite(paddle)[0] == x, f'{label}: the paddle stops when let go')
        print(f'ok: {label}')

    check(game.xram(0, 1)[0] & NUM_LOCK, 'Num Lock is on when the emulator starts')
    for key, direction in MOVES:
        move(f'press {key}', f'release {key}', direction, f'{key} moves {direction}, Num Lock on')

    game.send(f'state load "{state}"')
    game.send('lock num')
    game.run(2)
    check(not game.xram(0, 1)[0] & NUM_LOCK, 'Num Lock is off')
    game.send(f'state save "{state}"')
    for key, direction in MOVES[4:]:
        move(f'press {key}', f'release {key}', direction, f'{key} moves {direction}, Num Lock off')
    game.send(f'state load "{state}"')
    game.send('lock num')
    game.run(2)
    check(game.xram(0, 1)[0] & NUM_LOCK, 'Num Lock is on again')
    game.send(f'state save "{state}"')

    for direction in ['left', 'right']:
        move(f'pad 0 press {direction}', f'pad 0 release {direction}', direction,
             f'gamepad d-pad {direction}')
    move('pad 1 stick -128 0 0 0', 'pad 1 stick 0 0 0 0', 'left', 'gamepad 2 left stick left')
    move('pad 1 stick 127 0 0 0', 'pad 1 stick 0 0 0 0', 'right', 'gamepad 2 left stick right')

    for key in LAUNCH_KEYS:
        game.send(f'state load "{state}"')
        game.send(f'press {key}')
        game.wait('launch, 4 balls left', 5)
        game.send(f'release {key}')
        print(f'ok: {key} launches')
    for pad, button in LAUNCH_BUTTONS:
        game.send(f'state load "{state}"')
        game.send(f'pad {pad} press {button}')
        game.wait('launch, 4 balls left', 5)
        game.send(f'pad {pad} release {button}')
        print(f'ok: gamepad {pad + 1} button {button} launches')
    game.send(f'state load "{state}"')
    game.send('pad 1 stick 0 -128 0 0')
    game.wait('launch, 4 balls left', 5)
    game.send('pad 1 stick 0 0 0 0')
    print('ok: gamepad 2 left stick up launches')

    # A held launch control launches only once, even when the ball is back
    # on the paddle while it is still held.
    game.send(f'state load "{state}"')
    game.send('press space')
    game.wait('launch, 4 balls left', 5)
    game.run(10)
    game.poke('ball_state', 0)
    game.run(30)
    game.send('expect-not "launch, 3 balls left"')
    game.send('release space')
    game.run(2)
    game.send('press space')
    game.wait('launch, 3 balls left', 5)
    game.send('release space')
    print('ok: a held launch launches once')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
