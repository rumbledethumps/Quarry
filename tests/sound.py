#!/usr/bin/env python3
"""Checks the sound effects on the PSG, in the emulator.

  sound.py rom.rp6502

Needs a Debug ROM, which logs each effect it plays. The emulator runs muted,
so this reads the PSG's channels in XRAM instead of listening: each effect
must set its notes there, slide where it slides, and let go between notes.
Exits 0 when every check passes.
"""

import struct

from game import Game, check

BUY_NOTES = [523 * 3, 659 * 3, 784 * 3, 1047 * 3]
# The first note of a few effects, by their names in src/sfx.h: the wave,
# as PSG_WAVE_ names it, and the range of Hz * 3 its notes and slides pass
# through, from src/sfx.c. Each effect's number and each wave's come from
# the .sym.
NOTES = {
    'PADDLE': ('SQUARE', 196 * 3, 196 * 3),
    'WALL': ('TRIANGLE', 523 * 3, 523 * 3),
    'BRICK': ('SQUARE', 988 * 3, 988 * 3),
    'BREAK': ('NOISE', 2400 * 3 - 60 * 6, 2400 * 3),
    'NUGGET': ('TRIANGLE', 1319 * 3, 1760 * 3),
    'LOW': ('SQUARE', 1047 * 3, 1047 * 3),
    'LOW_BEEP': ('SQUARE', 1047 * 3, 1047 * 3),
    'SPUTTER': ('NOISE', 800 * 3 - 30 * 6, 1500 * 3),
    'FALL': ('SAWTOOTH', 700 * 3 - 54 * 32, 700 * 3),
    'MOVE': ('SQUARE', 1568 * 3, 1568 * 3),
}


def channels(game):
    """Each channel as (freq, wave, gate)."""
    data = game.xram('XRAM_PSG', game.sym['PSG_CHANNELS'] * 8)
    return [(struct.unpack('<H', data[i:i + 2])[0], data[i + 5] & 0xF0, data[i + 6] & game.sym['PSG_GATE'])
            for i in range(0, len(data), 8)]


def ram(game, name, size):
    """The bytes of the game's RAM from name."""
    return bytes.fromhex(game.cmd(f'dump {name} {size}'))


def wave(game, name):
    return game.sym[f'PSG_WAVE_{name}']


def played(game, sound, frames=60):
    """Waits for the effect, by its name in src/sfx.h, then checks its notes
    are set on the PSG."""
    game.wait(f'sfx {game.sym["SFX_" + sound]}\\n', frames)  # the line's end, so 1 is not 11
    if sound in NOTES:
        game.run(1)  # a taken channel starts a step late
        name, low, high = NOTES[sound]
        check(any(w == wave(game, name) and low <= f <= high for f, w, _ in channels(game)),
              f'effect {sound} is set on the PSG: {channels(game)}')


def main():
    game = Game()
    sym = game.sym
    CHANNELS = sym['PSG_CHANNELS']
    game.boot()
    check(all(c == (0, 0, 0) for c in channels(game)), 'the PSG starts quiet, at XRAM_PSG')

    game.new_game()
    game.run(5)

    # The ball off the bricks, and the bricks breaking, with a chime for
    # each nugget: the ball aimed up at the lowest brick, which breaks at a
    # hit. With the ball back on the paddle, so nothing else breaks, the
    # nuggets land in the counts without a sound.
    game.tap('space')
    count = game.ram('brick_count')
    ys, xs = (struct.unpack(f'<{count}h', ram(game, name, 2 * count)) for name in ('brick_y', 'brick_x'))
    alive = ram(game, 'brick_alive', count)
    low = max((y, i) for i, y in enumerate(ys) if alive[i])[1]
    game.paused_poke([(f'brick_hits+{low}', 1, 1), (f'brick_damage+{low}', 0, 1),
                       ('ball_x', (xs[low] + (sym['BRICK_W'] - sym['BALL_SIZE']) // 2) << 8, 4),
                       ('ball_y', (ys[low] + sym['BRICK_H'] + 4) << 8, 4),
                       ('ball_vx', 0, 2), ('ball_vy', -600 & 0xFFFF, 2)])
    played(game, 'BREAK', 30)
    played(game, 'NUGGET', 5)
    played(game, 'BRICK', 5)
    game.paused_poke([('ball_state', sym['BALL_DOCKED'], 1)])
    game.run(90)
    game.cmd(f'expect-not "sfx {sym["SFX_NUGGET"]}\\n"')
    game.cmd('expect "nugget landed"')
    print('ok: brick and break with a chime, and the nugget landing silent')

    # The ball off a wall and off the paddle, set up while paused.
    px = game.px('paddle_x')
    width = game.ram('paddle_width')
    game.paused_poke([('ball_x', (game.ram('play_left', 2) + 1) << 8, 4), ('ball_y', 150 << 8, 4),
                       ('ball_vx', -600 & 0xFFFF, 2), ('ball_vy', 300, 2),
                       ('ball_state', sym['BALL_FLYING'], 1)])
    played(game, 'WALL', 10)
    game.paused_poke([('ball_x', (px + width // 2 - 4) << 8, 4), ('ball_y', 190 << 8, 4),
                       ('ball_vx', 0, 2), ('ball_vy', 600, 2)])
    played(game, 'PADDLE', 20)
    print('ok: wall and paddle')

    # A lost ball whistles down. A spare ball in the count, so the level
    # goes on after this one is lost.
    game.paused_poke([('balls', 1, 1), ('ball_x', 100 << 8, 4), ('ball_y', 225 << 8, 4),
                       ('ball_vx', 0, 2), ('ball_vy', 600, 2)])
    played(game, 'LOST', 20)
    game.run(1)
    whistle = [i for i, (f, w, g) in enumerate(channels(game))
               if w == wave(game, 'SQUARE') and g and 360 <= f <= 660 * 3]
    check(whistle, 'the whistle is on a channel, gate held')
    first = channels(game)[whistle[0]][0]
    game.run(10)
    later = channels(game)[whistle[0]][0]
    check(later < first, f'the whistle slides down, {first} then {later}')
    print(f'ok: lost ball, sliding from {first} to {later}')

    # Low energy beeps, then beeps again while it stays low, if the burn
    # bought leaves it low long enough for another.
    burn = game.ram(f'burns+{game.ram("upgrade_ranks+UPGRADE_EFFICIENCY")}')
    game.paused_poke([('energy', sym['TUNE_ENERGY_LOW'] + 10 * burn, 2)])
    played(game, 'LOW', 30)
    if sym['TUNE_ENERGY_LOW'] // burn > sym['LOW_BEEP_STEPS']:
        played(game, 'LOW_BEEP', sym['LOW_BEEP_STEPS'] + 20)
        print('ok: low energy, and beeps while low')
    else:
        print(f'ok: low energy; note: a burn of {burn} empties the tank before a second beep, so none is checked')

    # Out of energy: the flames sputter, then the paddle falls.
    game.paused_poke([('energy', 5 * burn, 2)])
    played(game, 'SPUTTER', 20)
    played(game, 'FALL', 60)
    game.until('game_state', 'STATE_MENU', 200)
    print('ok: sputter and fall')

    # On the menu when a level ends and on the upgrade screen, moves click,
    # and a purchase plays four notes, letting go between them: the next
    # rank of the panel picked, with just the nuggets of each color it costs.
    game.run(70)
    game.tap('down')
    played(game, 'MOVE', 5)
    game.tap('up')
    game.menu_choose('TO THE DRY')
    game.cmd('expect "upgrades"')  # past every click before the upgrade screen
    game.talk_ok()
    game.tap('right')
    played(game, 'MOVE', 5)
    game.tap('left')
    game.run(20)
    for color, count in enumerate(game.cost_in(game.ram('panel_picked'))):
        if count:
            game.poke(f'nuggets+{2 * color}', count, 2)
    game.cmd('press enter')
    played(game, 'BUY', 10)
    game.cmd('release enter')
    notes = [[] for _ in range(CHANNELS)]
    gates = [[] for _ in range(CHANNELS)]
    for _ in range(24):
        for i, (f, w, g) in enumerate(channels(game)):
            if w != wave(game, 'TRIANGLE') or f not in BUY_NOTES:
                continue
            if not notes[i] or notes[i][-1] != f:
                notes[i].append(f)
            if not gates[i] or gates[i][-1] != g:
                gates[i].append(g)
        game.run(1)
    buy = [i for i in range(CHANNELS) if notes[i] == BUY_NOTES]
    check(buy, f'the purchase plays its four notes in order, on one channel: {notes}')
    check(gates[buy[0]].count(1) >= 3, f'and lets go between them: {gates[buy[0]]}')
    game.run(60)
    check(all(g == 0 for _, _, g in channels(game)), 'every channel lets go when its effect ends')
    check(game.ram('game_state') == sym['STATE_SHOP'], 'still on the upgrade screen')
    game.close()
    print('ok: menu moves and the purchase')
    print('PASS')


if __name__ == '__main__':
    main()
