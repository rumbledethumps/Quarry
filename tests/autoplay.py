#!/usr/bin/env python3
"""Plays stage 1 in the emulator, to check the ball and the bricks.

  autoplay.py [--miss N] [--frames N] rom.rp6502

The bot reads the ball and the paddle sprites each step and steers the
paddle under the ball with the arrow keys. With --miss N it lets the first
N balls fall. Every step it checks that the ball stays inside the playfield
and never moves more than 3 px a step. It stops at the end of the stage,
reports how the stage ended, checks a nugget landed for each broken brick,
then chooses Play on the end-of-stage menu and checks that the stage starts
again. It runs on a Release ROM too.

Exits 0 when every check passes.
"""

import argparse
import sys

from game import Game, check, fail


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--miss', type=int, default=0)
    parser.add_argument('--frames', type=int, default=60 * 60 * 10)
    # Game() takes the ROM and the emulator options from the rest.
    args, sys.argv[1:] = parser.parse_known_args()

    game = Game()
    sym = game.sym
    game.new_game()
    game.run(10)
    play_left = game.ram('play_left', 2, signed=True)
    play_right = game.ram('play_right', 2, signed=True)
    play_top = sym['WALL_SIZE']
    paddle_y, paddle_w = sym['TUNE_PADDLE_Y'], game.ram('paddle_width')
    ball = sym['BALL_SIZE']
    bricks = sym['STAGE1_COLS'] * sym['STAGE1_ROWS']
    balls = sym['TUNE_BALLS']

    def predict(x, y, dx, dy):
        """The ball's left edge when it reaches the paddle, off the side walls."""
        if dy <= 0:
            return x
        x += dx * (paddle_y - ball - y) / dy
        lo, hi = play_left, play_right - ball
        span = hi - lo
        x = (x - lo) % (2 * span)
        return lo + (x if x <= span else 2 * span - x)

    full = game.ram('energy', 2)
    check(game.ram('balls') == balls, f'{balls} balls at the start')
    check(game.shown('XRAM_BALL_ICONS', balls + 1) == balls, f'{balls} ball icons at the start')
    check(game.ram('bricks_left') == bricks, f'{bricks} bricks at the start')
    check(game.shown('XRAM_BRICKS', bricks) == bricks, f'{bricks} brick sprites at the start')

    held = None
    prev = None
    launches = hits = 0
    zone_aim = 0
    for step in range(args.frames):
        if game.ram('game_state') != sym['STATE_PLAY']:
            break
        state = game.ram('ball_state')
        x, y = game.sprite('XRAM_BALL_SPRITE')
        px = game.sprite('XRAM_SLED_SPRITE')[0]
        check(play_left <= px <= play_right - paddle_w, f'paddle x {px} left the playfield')
        want = None
        if state == sym['BALL_DOCKED']:
            prev = None
            if launches < balls:
                game.cmd('press space')
                game.run(2)
                game.cmd('release space')
                game.run(2)
                launches += 1
                check(game.ram('balls') == balls - launches, 'each launch takes a ball')
                check(game.shown('XRAM_BALL_ICONS', balls) == balls - launches,
                      'an icon goes with each launch')
            continue
        if state == sym['BALL_FLYING'] and 0 <= y < sym['SCREEN_H']:
            check(play_left <= x <= play_right - ball, f'ball x {x} left the playfield')
            check(y >= play_top, f'ball y {y} went through the top wall')
            if prev:
                dx, dy = x - prev[0], y - prev[1]
                # A frame can end before the game draws the ball, and then the
                # next frame shows it two steps on. The ball always moves at
                # least a pixel down or up a step, so a frame where it did not
                # is one of those.
                limit = 6 if prev[4] == 0 else 3
                check(abs(dx) <= limit and abs(dy) <= limit,
                      f'ball jumped from {prev[0]},{prev[1]} to {x},{y} at step {step}')
                if dy < 0 and prev[2] > 0 and y > paddle_y - ball - 8:
                    hits += 1
                    zone_aim = (zone_aim + 1) % 5
                if launches > args.miss:
                    target = predict(x, y, dx, dy) + ball // 2 - paddle_w // 2
                    target += (zone_aim - 2) * 4
                    if target < px - 1:
                        want = 'left'
                    elif target > px + 1:
                        want = 'right'
                prev = (x, y, dy or prev[2], dx, dy)
            else:
                prev = (x, y, 0, 1, 1)
        if want != held:
            if held:
                game.cmd(f'release {held}')
            if want:
                game.cmd(f'press {want}')
            held = want
        game.run()
    else:
        fail(f'the stage did not end in {args.frames} steps')

    left = game.ram('bricks_left')
    message = next((m for m in ('STAGE CLEAR', 'OUT OF BALLS', 'OUT OF ENERGY')
                    if game.shows(m)), None)
    print(f'stage over after {step} steps: {message!r}, {left} bricks left, '
          f'{launches} launches, {hits} paddle hits, energy {game.ram("energy", 2)}')
    if message == 'OUT OF ENERGY':
        check(left and game.ram('energy', 2) == 0, 'the stage ends when the energy runs out')
    elif left:
        check(message == 'OUT OF BALLS', 'out of balls is shown')
        check(launches == balls, 'the stage ends when the last ball is lost')
    else:
        check(message == 'STAGE CLEAR', 'stage clear is shown')
    check(game.shows('UPGRADES') and game.shows('PLAY'), 'the end-of-stage menu is shown')
    if message != 'OUT OF ENERGY':
        images = set()
        for _ in range(30):
            game.run()
            images.add(game.sprites('XRAM_JET_SPRITES', 1)[0][2])
        check(len(images) > 1, 'the flames still burn after the stage ends')
    game.run(90)
    check(game.shown('XRAM_BRICKS', bricks) == left, 'a sprite for each brick left')
    counted = game.ram('nuggets', 2)
    check(counted == bricks - left, f'a nugget for each broken brick, {counted} of {bricks - left}')

    # Play starts the stage again.
    if held:
        game.cmd(f'release {held}')
    game.menu_choose('PLAY', wait=False)
    game.run(5)
    check(game.ram('game_state') == sym['STATE_PLAY'], 'the stage starts again')
    check(game.ram('bricks_left') == bricks, 'the bricks come back')
    check(game.shown('XRAM_BRICKS', bricks) == bricks, 'the brick sprites come back')
    check(game.ram('balls') == balls, 'the balls come back')
    check(game.ram('nuggets', 2) == counted, 'the nuggets are kept')
    check(game.shown('XRAM_BALL_ICONS', balls + 1) == balls, 'the ball icons come back')
    check(game.ram('energy', 2) == full, 'the energy is full again')
    check(not game.shows('UPGRADES'), 'the menu is gone')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
