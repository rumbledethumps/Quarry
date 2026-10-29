#!/usr/bin/env python3
"""Checks the energy gauge and running out of energy, in the emulator.

  energy.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The energy is poked low
to skip ahead, and the ball poked over the sled to make it bounce. Reads
the fuel in the gauge, its bubbles, the jets and the tilt of the falling
sled from their sprites, the glass from its image, the meter from its
sprite and its paddle's color, and the smoke from screenshots. Exits 0
when every check passes.
"""

import os
import tempfile

from game import Game, check

# The colors of the smoke, in the fx row of art/palettes.png.
SMOKE = [(0x51, 0x5a, 0x62), (0x8c, 0x94, 0x9a)]


def fuel(game):
    """The rows of fuel the gauge shows, from its sprites: its surface a row
    above the fuel, and each run of it under the surface, from the foot of
    the glass up, shown, and none above."""
    sym = game.sym
    hidden = sym['SPRITE_HIDDEN_Y']
    foot = game.sprite('XRAM_GLASS_SPRITES')[1] + sym['GLASS_H']
    y = game.sprite('XRAM_SURFACE_SPRITE')[1]
    rows = 0 if y == hidden else foot - y - 1
    for i, (_, top, _) in enumerate(game.sprites('XRAM_LIQUID_SPRITES', sym['LIQUID_SEGMENTS'])):
        run = foot - (i + 1) * sym['LIQUID_H']
        check(top == (run if rows and run >= foot - rows else hidden),
              f'run {i} of the fuel is at {top}, with {rows} rows of fuel')
    return rows


def fuel_of(game, energy):
    """The rows of fuel for the energy: a row for each GLASS_H-th of a full
    gauge, or part of one."""
    return -(-energy * game.sym['GLASS_H'] // game.sym['TUNE_ENERGY'])


def check_fuel(game, message):
    """The gauge shows the energy, read after its sprites: the energy may
    have drained a step since, but never more."""
    rows = fuel(game)
    expected = fuel_of(game, game.ram('energy', 2))
    check(expected <= rows <= expected + 1, f'{message}: {rows} rows of fuel, for {expected}')
    return rows


def check_glass(game):
    """The glass is the right curtain's rock behind it, pixel for pixel: an
    outline down each side, the darkest rock where the shaft is clear, and
    the glint."""
    sym = game.sym
    nibble = lambda data, pitch, x, y: data[y * pitch + x // 2] >> (0 if x & 1 else 4) & 15
    right = '(XRAM_CURTAIN_SPRITES+CURTAIN_TILES*SPRITE_BYTES)'
    pieces = []
    for (x, y, image), size in zip(game.sprites(right, sym['CURTAIN_TILES']), game.sizes(right, sym['CURTAIN_TILES'])):
        w, h = ((size & 15) + 1) * 4, ((size >> 4) + 1) * 4
        pieces.append((x, y, w, h, game.xram(image, w * h // 2)))

    def rock(sx, sy):
        for x, y, w, h, data in pieces:
            if x <= sx < x + w and y <= sy < y + h:
                return nibble(data, w // 2, sx - x, sy - y) or sym['GLASS_ROCK']
        return sym['GLASS_ROCK']

    gx, gy, _ = game.sprites('XRAM_GLASS_SPRITES', 1)[0]
    w, h, col = sym['GLASS_W'], sym['GLASS_H'], sym['GLINT_COL']
    glass = game.xram(sym['XRAM_GLASS_IMAGE'], w * h // 2)
    for y in range(h):
        row = [nibble(glass, w // 2, x, y) for x in range(w)]
        want = [sym['GLASS_OUTLINE']] + [rock(gx + x, gy + y) for x in range(1, w - 1)] + [sym['GLASS_OUTLINE']]
        want[col] = sym['GLASS_GLINT']
        check(row == want, f'row {y} of the glass is {row}, the rock behind it {want}')


def bubbles(game, image='XRAM_BUBBLE_IMAGE'):
    """The tops of the bubbles rising in the gauge, from their sprites, or
    with XRAM_DROP_IMAGE, of the drops the popped ones throw up."""
    hidden, image = game.sym['SPRITE_HIDDEN_Y'], game.sym[image]
    return [y for _, y, i in game.sprites('XRAM_BUBBLE_SPRITES', game.sym['BUBBLES']) if y != hidden and i == image]


def bounce(game):
    """The ball dropped straight onto the middle of the sled, to bounce off
    it."""
    sym = game.sym
    x = game.px('paddle_x') + game.ram('paddle_width') // 2 - sym['BALL_SIZE'] // 2
    y = game.px('paddle_y') - sym['BALL_SIZE'] - 3
    game.paused_poke([('ball_x', x << 8, 4), ('ball_y', y << 8, 4), ('ball_vx', 0, 2), ('ball_vy', 256, 2)])
    game.wait('paddle zone', 10)
    game.run(2)


def check_bubbles(game):
    """A bubble rises from the foot of the fuel each time the ball bounces
    off the sled, while one is free. One is never taken from another, so
    each rises all the way, pops at the surface, and throws up a drop that
    hops over it and falls back in."""
    sym = game.sym
    foot = game.sprite('XRAM_GLASS_SPRITES')[1] + sym['GLASS_H']
    bounce(game)
    risen = bubbles(game)
    check(len(risen) == 1 and foot - sym['BUBBLE_SIZE'] - 4 <= risen[0] < foot,
          f'a bounce sends a bubble up from the foot of the fuel, at {foot}: {risen}')
    game.run(20)
    check(bubbles(game)[0] < risen[0] - 10, f'the bubble rises, from {risen[0]} to {bubbles(game)[0]}')
    for _ in range(sym['BUBBLES'] - 1):
        bounce(game)
    full = sorted(bubbles(game))
    check(len(full) == sym['BUBBLES'], f'a bubble for each bounce, {sym["BUBBLES"]} at most: {full}')
    bounce(game)
    after = sorted(bubbles(game))
    gaps = lambda ys: [b - a for a, b in zip(ys, ys[1:])]
    check(len(after) == sym['BUBBLES'] and gaps(after) == gaps(full) and after[0] < full[0],
          f'with none free, a bounce makes none and takes none: {full}, then {after}')
    highest = 0
    for _ in range(sym['GLASS_H'] + 40):
        tops, drops = bubbles(game), bubbles(game, 'XRAM_DROP_IMAGE')
        if not tops and not drops:
            break
        surface = game.sprite('XRAM_SURFACE_SPRITE')[1] + 1
        check(not tops or min(tops) > surface, f'no bubble rises past the surface, at {surface}: {tops}')
        # A read can land part way through the gauge's drawing, when the
        # surface has fallen a row and its drops have not yet moved.
        check(all(surface - sym['DROP_PEAK'] - 1 <= y < surface for y in drops),
              f'a drop hops up to {sym["DROP_PEAK"]} px over the surface, at {surface}: {drops}')
        highest = max([highest] + [surface - y for y in drops])
        game.run()
    check(not bubbles(game) and not bubbles(game, 'XRAM_DROP_IMAGE'), 'every bubble pops and its drop falls back')
    check(sym['DROP_PEAK'] <= highest <= sym['DROP_PEAK'] + 1, f'the drops hop {sym["DROP_PEAK"]} px, saw {highest}')
    print(f'ok: {sym["BUBBLES"]} bubbles at most, each up to the surface, where it throws up a drop')


def meter(game):
    """How far up the meter's paddle is, from 0, down, by its sprite's
    image, and its color."""
    sym = game.sym
    image = game.sprites('XRAM_METER_SPRITE', 1)[0][2]
    color = game.xram(sym['XRAM_PALETTE_FITTING'] + 2 * sym['METER_PADDLE'], 2)
    return (image - sym['XRAM_METER_IMAGES']) // sym['METER_IMAGE_BYTES'], int.from_bytes(color, 'little')


def check_meter(game, color, message):
    """The meter's paddle, on its way down from up, flips down a frame at a
    time, and comes up again in the color, as PADDLE_ names it in
    src/frame.c. The poke that set it off took some steps, so it may be
    part way down."""
    sym = game.sym
    up, was = sym['METER_FRAMES'] - 1, meter(game)[1]
    want = sym[f'PADDLE_{color}']
    seen = [meter(game)]
    for _ in range(2 * sym['METER_FRAMES'] * sym['METER_STEPS']):
        game.run()
        if meter(game) != seen[-1]:
            seen.append(meter(game))
    flip = [(f, was) for f in range(up, -1, -1)] + [(f, want) for f in range(up + 1)]
    check(seen[0] in flip[:up + 1] and seen == flip[flip.index(seen[0]):], f'{message}: {seen}')


def smoke_pixels(game, shot, x0, x1, y0, y1):
    rows = game.screen(shot)
    return sum(1 for y in range(y0, y1) for x in range(x0, x1)
               if any(sum(abs(a - b) for a, b in zip(rows[y][x], c)) < 24 for c in SMOKE))


def main():
    shot = os.path.join(tempfile.mkdtemp(), 'shot.png')
    game = Game()
    sym = game.sym
    game.new_game()
    game.run(5)

    full = game.ram('energy', 2)
    check(full == sym['TUNE_ENERGY'], 'the energy starts full')
    check(fuel(game) == sym['GLASS_H'], 'the gauge starts full')
    check_glass(game)
    up = sym['METER_FRAMES'] - 1
    check(meter(game) == (up, sym['PADDLE_GREEN']), f"the meter's paddle has flipped up green: {meter(game)}")
    print('ok: a full gauge, its glass the rock behind it, and the meter green')
    x, y = game.px('paddle_x'), game.px('paddle_y')
    pieces, flames = 'XRAM_SLED_SPRITE', 'XRAM_JET_SPRITES'
    nozzle = sym['XRAM_JET_IMAGES'] + sym['JET_NOZZLE'] * sym['JET_IMAGE_BYTES']  # a jet with no flame
    check(game.sprite(pieces) == (x, y), 'the paddle is where it is in RAM')
    images = set()
    for _ in range(30):
        game.run()
        jet = game.sprites(flames, 1)[0]
        check(jet[1] == y + sym['JET_TOP'], 'the jet burns under the sled')
        images.add(jet[2])
    check(len(images) == 3, f'the flames burn through 3 frames, saw {len(images)}')
    game.run(90)
    check(game.ram('energy', 2) == full, 'no energy drains before the first launch')

    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.run(60)
    drained = full - game.ram('energy', 2)
    drain = sym['TUNE_ENERGY_DRAIN']
    check(55 * drain <= drained <= 65 * drain,
          f'energy drains {drain} a step after the launch, drained {drained} in 60')
    print(f'drained {drained} in 60 steps after the launch')
    check_bubbles(game)

    game.paused_poke([('energy', sym['TUNE_ENERGY_MID'], 2)])
    check_meter(game, 'YELLOW', "at TUNE_ENERGY_MID, the meter's paddle flips down and up again yellow")
    low = sym['TUNE_ENERGY_LOW']
    game.paused_poke([('energy', low + 20, 2)])
    game.wait('energy low', 30)
    lamp_color = sym['XRAM_PALETTE_SHADE'] + 2 * sym['LAMP_COLOR']
    lamp = lambda: int.from_bytes(game.xram(lamp_color, 2), 'little')
    check(lamp() == sym['LAMP_ON'], "the machine's lamp lights with the warning")
    # The script's frames don't line up with the steps, so the wait can end
    # a step after the beep.
    game.run(sym['LAMP_STEPS'] - 2)
    check(lamp() == sym['LAMP_ON'], f'and stays lit for {sym["LAMP_STEPS"]} steps')
    game.run(2)
    check(lamp() == sym['LAMP_OFF'], 'and goes out after it')
    check(meter(game) == (up, sym['PADDLE_RED']), f'by then the meter has turned red: {meter(game)}')
    print('ok: the meter turns yellow, then red as the warning beeps and the lamp lights')
    rows = check_fuel(game, 'the gauge falls with the energy')
    print(f'low: {rows} rows of fuel')

    # Out of energy: the flames sputter and the player loses control. The
    # ball is put in flight in the middle of the playfield, rising slowly,
    # so it is still in flight when the paddle has gone.
    left = game.ram('play_left', 2, signed=True)
    game.paused_poke([('energy', 30, 2), ('ball_state', sym['BALL_FLYING'], 1), ('ball_x', (left + 20) << 8, 4),
                      ('ball_y', 120 << 8, 4), ('ball_vx', 0, 2), ('ball_vy', -64, 2)])
    game.wait('out of energy', 40)
    check(game.ram('paddle_state') == sym['PADDLE_SPUTTER'], 'the paddle sputters')
    x = game.px('paddle_x')
    game.cmd('press right')
    lit = 0
    for _ in range(20):
        game.run()
        lit += game.sprites(flames, 1)[0][2] != nozzle
    game.cmd('release right')
    check(game.px('paddle_x') == x, 'the paddle does not move while it sputters')
    check(0 < lit < 20, f'the flame flickers while it sputters, lit {lit} of 20')
    check(fuel(game) == 0, 'the gauge is empty')

    # A puff of smoke, and the paddle falls and tilts.
    game.wait('paddle falls', sym['TUNE_SPUTTER_STEPS'])
    top = game.px('paddle_y')
    game.run(6)
    puff = smoke_pixels(game, shot, x - 4, x + 32, top - 8, top + 16)
    check(puff > 10, f'a puff of smoke where the paddle gave up, {puff} pixels')
    jets = game.ram('sled_jets')
    check(game.shown('XRAM_SMOKE_SPRITES', sym['JETS_MAX']) == jets, f'a puff for each of its {jets} jets')
    game.run(10)
    check(game.sizes(pieces, 1)[0] >> 4 == sym['SLED_TILT_ROWS'] // 4 - 1,
          'the falling sled shows its tilted picture')
    check(game.sprites(flames, 1)[0][2] == nozzle, 'no flames on a falling paddle')
    check(game.px('paddle_y') > top + 4, 'the paddle falls')
    game.wait('paddle gone', 120)
    game.run(2)
    ball = 'XRAM_BALL_SPRITE'
    check(game.ram('game_state') == sym['STATE_PLAY'] and game.ram('ball_state') == sym['BALL_FLYING'],
          'with the paddle gone, the level plays on while the ball is in flight')
    check(game.shown(ball, 1) == 1, 'and the ball still shows')
    game.run(30)
    check(game.ram('game_state') == sym['STATE_PLAY'] and game.shown(ball, 1) == 1, 'and goes on')
    game.paused_poke([('ball_y', 200 << 8, 4), ('ball_vy', 512, 2)])
    game.wait('ball lost', 30)
    game.run(2)
    check(game.ram('game_state') != sym['STATE_PLAY'], 'the level ends once the ball falls off the screen')
    game.cmd(f'expect-not "sfx {sym["SFX_LOST"]}\\n"')  # the sled's fall was its sound
    check(game.shows('OUT OF FUEL'), 'the menu says OUT OF FUEL')
    print(f'puff of {puff} smoke pixels, the paddle fell off the screen, and the ball played on until it fell')

    # Replay plays again, with a full bar.
    game.menu_choose('REPLAY')
    game.run(5)
    check(game.ram('energy', 2) == full, 'the energy is full again')
    check(game.ram('energy_draining') == 0, 'it waits for the first launch again')
    check(game.ram('paddle_state') == sym['PADDLE_HOVER'], 'the paddle hovers again')
    check(fuel(game) == sym['GLASS_H'], 'the gauge is full again')
    game.run(sym['METER_FRAMES'] * sym['METER_STEPS'])
    check(meter(game) == (up, sym['PADDLE_GREEN']), f'and the meter green again: {meter(game)}')

    # Out of energy with the ball on the paddle: the ball goes down with it,
    # and launch does nothing.
    game.paused_poke([('energy', 10, 2), ('energy_draining', 1, 1)])
    game.wait('out of energy', 20)
    game.cmd('press space')
    game.run(4)
    game.cmd('release space')
    check(game.ram('balls') == sym['TUNE_BALLS'], 'no launch once out of energy')
    game.wait('paddle falls', sym['TUNE_SPUTTER_STEPS'])
    game.run(15)
    middle = game.sprite(pieces)[1] + game.ram('paddle_width') // 2 * sym['TILT_MAX'] // 8
    check(game.sprite(ball)[1] == middle - 8, 'the ball rides the middle of the tilted paddle')
    game.wait('paddle gone', 120)
    game.wait('ball lost', 10)
    game.run(2)
    game.cmd(f'expect-not "sfx {sym["SFX_LOST"]}\\n"')  # the ball fell with the sled, and its sound
    check(game.shows('OUT OF FUEL'), 'the menu says OUT OF FUEL again')

    # The level clears while the paddle falls: it still falls off the screen.
    game.menu_choose('REPLAY')
    game.run(5)
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    game.paused_poke([('energy', 5, 2)])
    game.wait('paddle falls', sym['TUNE_SPUTTER_STEPS'] + 10)
    check(game.ram('ball_state') == sym['BALL_FLYING'], 'the ball is still in flight')
    game.paused_poke([('bricks_left', 0, 1)])
    game.wait('level cleared', 5)
    game.wait('paddle gone', 120)
    game.run(2)
    check(game.shown(pieces, 1) == 0, 'the paddle fell off after the level cleared')
    game.talk_ok()  # the dwarf with the coin for a first clear
    check(game.shows('LEVEL COMPLETE'), 'the menu says LEVEL COMPLETE')
    print('cleared while falling: the paddle still fell off the screen')
    game.close()
    print('PASS')


if __name__ == '__main__':
    main()
