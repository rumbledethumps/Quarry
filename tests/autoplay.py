#!/usr/bin/env python3
"""Plays stage 1 in the emulator, to check the ball and the bricks.

  autoplay.py [--seed N] [--miss N] [--frames N] rom.rp6502

The bot reads the ball and paddle sprites from XRAM each step and steers
the paddle under the ball with the arrow keys. With --miss N it lets the
first N balls fall. Every step it checks that the ball stays inside the
playfield and never moves more than 3 px a step. It stops at the end of
the stage, reports how the stage ended,
then presses Space and checks that the stage starts again.

Exits 0 when every check passes.
"""

import argparse
import os
import subprocess
import sys

EMU = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rp6502-emu')

# XRAM addresses, from the layout in src/xram.h.
XRAM_PALETTE_MAIN = 104
XRAM_BRICKS = 168
XRAM_ACTORS = 648
XRAM_BALL_ICONS = 738
XRAM_TEXT = 1098
XRAM_BALL_IMAGE = 5770
SPRITE = 10  # sizeof(mode5_csprite_t)
BALL_SPRITE = XRAM_ACTORS
PADDLE_SPRITE = XRAM_ACTORS + SPRITE
HIDDEN_Y = -64

# Stage 1 geometry, from src/play.h, src/tuning.h and src/bricks.c.
PLAY_LEFT, PLAY_RIGHT, PLAY_TOP = 88, 232, 16
PADDLE_Y, PADDLE_W = 208, 24
BALL = 8
BRICKS = 30
BALLS = 5


class Emu:
    def __init__(self, rom, seed):
        self.proc = subprocess.Popen(
            [EMU, rom, '--script', '-', '--seed', str(seed), '--mute'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.send('reply')

    def send(self, line):
        self.proc.stdin.write(line + '\n')
        reply = self.proc.stdout.readline().strip()
        if not reply.startswith('ok'):
            rest = self.proc.stdout.read()
            sys.exit(f'FAIL: {line!r} -> {reply}\n{rest}')
        return reply[2:].split()

    def words(self, addr, count):
        data = [int(b, 16) for b in self.send(f'dump xram:{addr} {count * 2}')]
        values = [data[i] | data[i + 1] << 8 for i in range(0, len(data), 2)]
        return [v - 0x10000 if v & 0x8000 else v for v in values]

    def text(self, row, col, count):
        data = self.send(f'dump xram:{XRAM_TEXT + (row * 40 + col) * 2} {count * 2}')
        return ''.join(chr(int(b, 16)) for b in data[::2]).replace('\0', ' ')

    def close(self):
        self.proc.stdin.close()
        out = self.proc.stdout.read()
        self.proc.wait()
        return out


def check(ok, message):
    if not ok:
        sys.exit(f'FAIL: {message}')


def icons(emu):
    ys = emu.words(XRAM_BALL_ICONS + 2, 1 + (BALLS - 1) * SPRITE // 2)[::SPRITE // 2]
    return sum(y != HIDDEN_Y for y in ys)


def bricks(emu):
    ys = emu.words(XRAM_BRICKS + 2, 1 + (BRICKS - 1) * SPRITE // 2)[::SPRITE // 2]
    return sum(y != HIDDEN_Y for y in ys)


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

    emu = Emu(args.rom, args.seed)
    emu.send('run 10')
    image, palette = emu.words(BALL_SPRITE + 4, 2)
    check(image == XRAM_BALL_IMAGE and palette == XRAM_PALETTE_MAIN,
          'the XRAM layout in this script does not match src/xram.h')
    check(icons(emu) == BALLS, f'{BALLS} ball icons at the start')
    check(bricks(emu) == BRICKS, f'{BRICKS} bricks at the start')

    held = None
    prev = None
    launches = hits = 0
    zone_aim = 0
    for frame in range(args.frames):
        bx, by = emu.words(BALL_SPRITE, 2)
        px = emu.words(PADDLE_SPRITE, 1)[0]
        if by == HIDDEN_Y:
            break
        x, y = bx, by
        check(PLAY_LEFT <= x <= PLAY_RIGHT - BALL, f'ball x {x} left the playfield')
        check(y >= PLAY_TOP, f'ball y {y} went through the top wall')
        check(PLAY_LEFT <= px <= PLAY_RIGHT - PADDLE_W, f'paddle x {px} left the playfield')

        docked = y == PADDLE_Y - BALL and abs(x + BALL // 2 - (px + PADDLE_W // 2)) <= 1
        want = None
        if docked and prev and prev[1] > PADDLE_Y:
            prev = None  # a lost ball, back on the paddle
        if docked and (prev is None or prev[1] == y):
            if launches < BALLS:
                emu.send('press space')
                emu.send('run 2')
                emu.send('release space')
                emu.send('run 2')
                launches += 1
                shown = icons(emu)
                check(shown == BALLS - launches,
                      f'launch {launches} at step {frame} leaves {shown} icons')
            prev = None
            continue
        if prev:
            dx, dy = x - prev[0], y - prev[1]
            check(abs(dx) <= 3 and abs(dy) <= 3,
                  f'ball jumped from {prev[0]},{prev[1]} to {x},{y} at step {frame}')
            if dy < 0 and prev[2] > 0 and y > PADDLE_Y - BALL - 8:
                hits += 1
                zone_aim = (zone_aim + 1) % 5
            missing = launches <= args.miss
            if not missing:
                target = predict(x, y, dx, dy) + BALL // 2 - PADDLE_W // 2
                target += (zone_aim - 2) * 4
                if target < px - 1:
                    want = 'left'
                elif target > px + 1:
                    want = 'right'
            prev = (x, y, dy or prev[2])
        else:
            prev = (x, y, 0)
        if want != held:
            if held:
                emu.send(f'release {held}')
            if want:
                emu.send(f'press {want}')
            held = want
        emu.send('run 1')
    else:
        sys.exit(f'FAIL: the stage did not end in {args.frames} steps')

    left = bricks(emu)
    message = emu.text(15, 14, 13).strip()
    print(f'stage over after {frame} steps: {message!r}, {left} bricks left, '
          f'{launches} launches, {hits} paddle hits')
    if left:
        check(message == 'OUT OF BALLS', 'out of balls is shown')
        check(launches == BALLS, 'the stage ends when the last ball is lost')
    else:
        check(message == 'STAGE CLEAR', 'stage clear is shown')
    check(emu.text(17, 13, 14) == 'LAUNCH TO PLAY', 'launch to play is shown')

    # Launch starts the stage again, after a short wait.
    if held:
        emu.send(f'release {held}')
    emu.send('run 70')
    emu.send('press space')
    emu.send('run 2')
    emu.send('release space')
    emu.send('run 10')
    check(bricks(emu) == BRICKS, 'the bricks come back')
    check(icons(emu) == BALLS, 'the balls come back')
    check(emu.text(15, 14, 13).strip() == '', 'the message is cleared')
    emu.close()
    print('PASS')


if __name__ == '__main__':
    main()
