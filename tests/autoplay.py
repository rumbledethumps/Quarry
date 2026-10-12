#!/usr/bin/env python3
"""Plays stage 1 in the emulator, to check the ball and the bricks.

  autoplay.py [--seed N] [--miss N] [--frames N] rom.rp6502

The bot reads the ball and the paddle sprites each step and steers the paddle under the ball with the arrow keys. With --miss N it lets
the first N balls fall. Every step it checks that the ball stays inside the
playfield and never moves more than 3 px a step. It stops at the end of the
stage, reports how the stage ended, checks a nugget landed for each broken
brick, then chooses Play on the end-of-stage menu and checks that the stage
starts again.

Exits 0 when every check passes.
"""

import argparse

from game import STATE_PLAY, Game, check, fail

# Stage 1, from src/play.c, src/tuning.h and src/bricks.c.
PLAY_LEFT, PLAY_RIGHT, PLAY_TOP = 88, 232, 16
ICONS_X, ICONS_Y = 270, 92
PADDLE_Y, PADDLE_W = 208, 24
BALL = 8
BRICKS = 30
BALLS = 5

BALL_DOCKED, BALL_FLYING = 0, 1


def predict(x, y, dx, dy):
    """The ball's left edge when it reaches the paddle, off the side walls."""
    if dy <= 0:
        return x
    x += dx * (PADDLE_Y - BALL - y) / dy
    lo, hi = PLAY_LEFT, PLAY_RIGHT - BALL
    span = hi - lo
    x = (x - lo) % (2 * span)
    return lo + (x if x <= span else 2 * span - x)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rom')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--miss', type=int, default=0)
    parser.add_argument('--frames', type=int, default=60 * 60 * 10)
    args = parser.parse_args()

    game = Game(args.rom, args.seed)
    game.run(10)
    ball_sprite = game.sprite_at(game.px('ball_x'), game.px('ball_y'))
    paddle_sprite = game.sprite_at(game.px('paddle_x'), game.px('paddle_y'))
    flame_sprite = game.sprite_at(game.px('paddle_x'), game.px('paddle_y') + 8)
    icon_sprites = game.sprite_at(ICONS_X, ICONS_Y)
    brick_sprites = game.sprite_at(PLAY_LEFT, 32)
    full = game.ram('energy', 2)
    check(game.ram('balls') == BALLS, f'{BALLS} balls at the start')
    check(game.shown(icon_sprites, BALLS + 1) == BALLS, f'{BALLS} ball icons at the start')
    check(game.ram('bricks_left') == BRICKS, f'{BRICKS} bricks at the start')
    check(game.shown(brick_sprites, BRICKS) == BRICKS, f'{BRICKS} brick sprites at the start')

    held = None
    prev = None
    launches = hits = 0
    zone_aim = 0
    for step in range(args.frames):
        if game.ram('game_state') != STATE_PLAY:
            break
        state = game.ram('ball_state')
        x, y = game.sprite(ball_sprite)
        px = game.sprite(paddle_sprite)[0]
        check(PLAY_LEFT <= px <= PLAY_RIGHT - PADDLE_W, f'paddle x {px} left the playfield')
        want = None
        if state == BALL_DOCKED:
            prev = None
            if launches < BALLS:
                game.send('press space')
                game.run(2)
                game.send('release space')
                game.run(2)
                launches += 1
                check(game.ram('balls') == BALLS - launches, 'each launch takes a ball')
                check(game.shown(icon_sprites, BALLS) == BALLS - launches,
                      'an icon goes with each launch')
            continue
        if state == BALL_FLYING and 0 <= y < 240:
            check(PLAY_LEFT <= x <= PLAY_RIGHT - BALL, f'ball x {x} left the playfield')
            check(y >= PLAY_TOP, f'ball y {y} went through the top wall')
            if prev:
                dx, dy = x - prev[0], y - prev[1]
                # A frame can end before the game draws the ball, and then the
                # next frame shows it two steps on. The ball always moves at
                # least a pixel down or up a step, so a frame where it did not
                # is one of those.
                limit = 6 if prev[4] == 0 else 3
                check(abs(dx) <= limit and abs(dy) <= limit,
                      f'ball jumped from {prev[0]},{prev[1]} to {x},{y} at step {step}')
                if dy < 0 and prev[2] > 0 and y > PADDLE_Y - BALL - 8:
                    hits += 1
                    zone_aim = (zone_aim + 1) % 5
                if launches > args.miss:
                    target = predict(x, y, dx, dy) + BALL // 2 - PADDLE_W // 2
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
                game.send(f'release {held}')
            if want:
                game.send(f'press {want}')
            held = want
        game.run()
    else:
        fail(f'the stage did not end in {args.frames} steps')

    left = game.ram('bricks_left')
    message = next((m for m in ('STAGE CLEAR', 'OUT OF BALLS', 'OUT OF ENERGY')
                    if game.shows(m)), None)
    print(f'stage over after {step} steps: {message!r}, {left} bricks left, '
          f'{launches} launches, {hits} paddle hits, energy {game.ram("energy", 2)}')
    if left:
        check(message == 'OUT OF BALLS', 'out of balls is shown')
        check(launches == BALLS, 'the stage ends when the last ball is lost')
    else:
        check(message == 'STAGE CLEAR', 'stage clear is shown')
    check(game.shows('UPGRADES') and game.shows('PLAY'), 'the end-of-stage menu is shown')
    images = set()
    for _ in range(30):
        game.run()
        images.add(game.sprites(flame_sprite, 1)[0][2])
    check(len(images) > 1, 'the flames still burn after the stage ends')
    game.run(90)
    check(game.shown(brick_sprites, BRICKS) == left, 'a sprite for each brick left')
    counted = game.ram('nuggets', 2)
    check(counted == BRICKS - left, f'a nugget for each broken brick, {counted} of {BRICKS - left}')

    # Play starts the stage again.
    if held:
        game.send(f'release {held}')
    game.menu_choose('PLAY', wait=False)
    game.run(5)
    check(game.ram('game_state') == STATE_PLAY, 'the stage starts again')
    check(game.ram('bricks_left') == BRICKS, 'the bricks come back')
    check(game.shown(brick_sprites, BRICKS) == BRICKS, 'the brick sprites come back')
    check(game.ram('balls') == BALLS, 'the balls come back')
    check(game.ram('nuggets', 2) == counted, 'the nuggets are kept')
    check(game.shown(icon_sprites, BALLS + 1) == BALLS, 'the ball icons come back')
    check(game.ram('energy', 2) == full, 'the energy is full again')
    check(not game.shows('UPGRADES'), 'the menu is gone')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
