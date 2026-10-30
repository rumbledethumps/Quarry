#!/usr/bin/env python3
"""Checks the menu when a level ends and the upgrade screen, in the emulator.

  upgrades.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The nuggets are poked to
buy with. Reads the menus from the text cells in XRAM, and the panels from
their own text cells. The upgrades' values, costs and ranks are read from
the game's tables in RAM, and the levels' bricks from the game, so neither
the tuning nor the levels are written into the test. Exits 0 when every
check passes.
"""

import os
import struct
import sys

from game import Game, check, rom

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art'))
from panels import FONT, LAYOUTS  # noqa: E402
import menus  # noqa: E402

END_ITEMS = ['TO THE DRY', 'REPLAY', 'MAIN MENU']

# The upgrades in the order of their panels: each one's title and unit on
# its panel, its name in the log, and its tables in src/upgrades.c, of its
# values, with the bytes of each, and of its costs.
UPGRADES = [('BALLS', 'BALLS', 'balls', 'ball_counts', 1, 'ball_costs'),
            ('WEIGHT', 'DAMAGE', 'damage', 'damages', 1, 'damage_costs'),
            ('EFFICIENCY', 'L/S', 'efficiency', 'burns', 1, 'burn_costs'),
            ('SPEED', 'PX/S', 'speed', 'speeds', 2, 'speed_costs'),
            ('SIZE', 'PX', 'width', 'widths', 1, 'width_costs')]
BALLS, WEIGHT, EFFICIENCY, SPEED, SIZE = range(len(UPGRADES))
SPARE = 5  # nuggets of each color left over when every width is bought


def tuning(game):
    """Each upgrade's values, from RAM, in the order of the panels: from the
    one before any upgrade, and the cost of each rank after it, as its count
    of nuggets and their color, which tuning.h gives in its top bits."""
    shift = game.sym['COST_COLOR_SHIFT']
    tune = []
    for u, (_, _, _, values, size, costs) in enumerate(UPGRADES):
        ranks = game.ram(f'ranks+{u}')
        words = [game.ram(f'{costs}+{2 * i}', 2) for i in range(ranks)]
        tune.append(([game.ram(f'{values}+{i * size}', size) for i in range(ranks + 1)],
                     [(w & ((1 << shift) - 1), w >> shift) for w in words]))
    return tune


def main():
    game = Game()
    sym = game.sym
    game.cmd('pad 0 connect')
    game.new_game()
    tune = tuning(game)
    game.run(5)
    colors = sym['BRICK_COLORS']
    names = {sym[f'BRICK_{n.upper()}']: n for n in ('gray', 'red', 'green', 'blue', 'gold')}

    # A new game's level starts with the balls before any upgrade: one on
    # the sled, and the rest in the count.
    first = tune[BALLS][0][0]
    check(game.ram('ball_state') == sym['BALL_DOCKED'] and game.ram('balls') == first - 1 and
          game.count('XRAM_BALL_DIGITS', sym['BALL_DIGITS']) == first - 1,
          f'a new game starts with {first} balls: one on the sled, and {first - 1} in the count')

    def nuggets():
        """The nuggets of each color."""
        return [game.ram(f'nuggets+{2 * c}', 2) for c in range(colors)]

    def stock(costs, spare=0):
        """Pokes the nuggets of each color: what the costs, as (count,
        color), come to in it, and spare more. Returns them."""
        have = [spare] * colors
        for price, color in costs:
            have[color] += price
        for color, n in enumerate(have):
            game.poke(f'nuggets+{2 * color}', n, 2)
        return have

    def end_picked():
        """The item picked on the menu when a level ends, end_menus in
        src/main.c."""
        return END_ITEMS[game.ram('picked')]

    def cursor_on_item(menu, item):
        """Whether the holographic cursor's top left corner is at the item
        of a menu with a title, as src/menu.c places it, or out from it as
        far as it breathes, up to 2 px."""
        center, top = game.ram(menu), game.ram(f'{menu}+1')
        row = top + sym['HEAD_ROWS'] + item * sym['ITEM_ROWS']
        x, y = game.sprite('XRAM_CURSOR_SPRITES')
        out = (center - sym['MENU_COLS'] // 2 + 2) * 8 - x
        return out == row * 8 - y and 0 <= out <= 2

    def panel_tiles(p, row):
        """The tiles inside panel p, on a row of its map."""
        cols, left = sym['PANEL_MAP_COLS'], p % sym['PANEL_SLOTS'] * sym['PANEL_PITCH'] + sym['PANEL_BORDER']
        return game.xram(sym['XRAM_PANELS'] + row * cols + left, sym['PANEL_INSIDE'])

    def panel(p, row):
        """The text inside panel p, on a row of its map: each tile of the
        font, lit or dim, as its character, and the short digits as digits."""
        dim, text = sym['PANEL_TILE_DIM'], ''
        for t in panel_tiles(p, row):
            i = (t - 1) % dim
            text += FONT[i] if i < len(FONT) else str(i - len(FONT)) if i < len(FONT) + 10 else '?'
        return text.strip()

    def short(p, row):
        """For each tile of a row of panel p that isn't blank, whether it is
        one of the short digits, as a cost that can't be paid shows, and not
        the font's."""
        dim, font = sym['PANEL_TILE_DIM'], len(FONT)
        return [(t - 1) % dim >= font for t in panel_tiles(p, row) if (t - 1) % dim]

    def panel_lit(p):
        """Whether panel p's contents are lit: its plate a lit tile."""
        return panel_tiles(p, sym['TITLE_ROW'])[0] <= sym['PANEL_TILE_DIM']

    def panel_left(p):
        """Where panel p's left edge is, as the rail has slid."""
        return sym['PANEL_LEFT'] + p * sym['PANEL_STEP'] - game.ram('panel_scroll', 2)

    def slot_sprite(p, i):
        """Sprite i of panel p's slot, as PANEL_SPRITE in src/shop.c."""
        slots, sprites = sym['PANEL_SLOTS'], sym['PANEL_SPRITES']
        return sym['XRAM_MENU_SPRITES'] + (p % slots * sprites + i) * sym['SPRITE_BYTES']

    def cost_icon(p):
        """The image and colors of the icon by panel p's cost."""
        return struct.unpack('<HH', game.xram(slot_sprite(p, sym['PICTURE_SPRITES']) + 4, 4))

    brick_palette = lambda color: sym['XRAM_PALETTE_BRICKS'] + 32 * color
    nugget = lambda color: (sym['XRAM_NUGGET_ICON_IMAGE'], brick_palette(color))

    def value(p, rank):
        """Upgrade p's value at a rank, as its panel shows it: a burn in
        liters a second, from its tenths."""
        v = tune[p][0][rank]
        return f'{v // 10}.{v % 10}' if p == EFFICIENCY else str(v)

    def panel_shows(p):
        """Checks that panel p shows its title, what its next rank does, and
        that rank's cost, by a nugget of its color, in short digits just when
        there are too few of them, or MAX at the top rank."""
        title, unit = UPGRADES[p][:2]
        costs, rank, row = tune[p][1], game.ram(f'upgrade_ranks+{p}'), sym['COST_ROW']
        effect = value(p, rank) + (f' \x10 {value(p, rank + 1)}' if rank < len(costs) else '') + f' {unit}'
        check(panel(p, sym['TITLE_ROW']) == title and panel(p, sym['EFFECT_ROW']) == effect,
              f'panel {p} shows {title}, and what its next rank does: {panel(p, sym["EFFECT_ROW"])!r}')
        if rank == len(costs):
            check(panel(p, row) == 'MAX', f'and MAX, at its top rank: {panel(p, row)!r}')
            return
        price, color = costs[rank]
        few = nuggets()[color] < price
        check(panel(p, row) == str(price) and cost_icon(p) == nugget(color) and
              short(p, row) == [few] * len(str(price)),
              f'and its cost, {price}, by a {names[color]} nugget, in {"short digits" if few else "the font"}: '
              f'{panel(p, row)!r}')

    def buy(p):
        """Buys the next rank of panel p, the one picked, and checks that it
        spends that rank's cost, in its color, and no other nuggets."""
        rank, have, name = game.ram(f'upgrade_ranks+{p}'), nuggets(), UPGRADES[p][2]
        price, color = tune[p][1][rank]
        game.tap('space')
        game.wait(f'bought {name} {rank + 1}', 10)
        game.run(2)
        have[color] -= price
        check(game.ram(f'upgrade_ranks+{p}') == rank + 1 and nuggets() == have,
              f'{name} {rank + 1} is bought for its {price} {names[color]} nuggets, and no others')

    def cursor_on_panel():
        """Whether the holographic cursor is around the panel in the middle,
        a few px out from its frame, as tall as art/panels.py makes it, or out
        from there as far as it breathes, up to 2 px."""
        rows, size, step = LAYOUTS[game.ram('panel_picked')]['rows'], sym['CURSOR_SIZE'], sym['SPRITE_BYTES']
        left, top = game.sprite(sym['XRAM_CURSOR_SPRITES'])
        right, bottom = game.sprite(sym['XRAM_CURSOR_SPRITES'] + 3 * step)
        out = sym['PANEL_LEFT'] - 3 - left
        return (0 <= out <= 2 and top == sym['PANEL_Y'] + sym['TOP_ROW'] * 8 - 3 - out and
                right + size == sym['PANEL_LEFT'] + sym['PANEL_COLS'] * 8 + 3 + out and
                bottom + size == sym['PANEL_Y'] + (rows + 1) * 8 + 3 + out)

    def balls_picture(n):
        """The balls panel's picture is the count of balls a level starts
        with: n, in the panels' font, centered on its row with the two cells
        before it, and the ball icon of the counts in those cells."""
        row, dim, icon = sym['BALLS_ROW'], sym['PANEL_TILE_DIM'], sym['ICON_SIZE']
        filled = [c for c, t in enumerate(panel_tiles(BALLS, row)) if (t - 1) % dim]
        first = filled[0] if filled else 0
        before, after = first - 2, sym['PANEL_INSIDE'] - first - len(str(n))
        check(panel(BALLS, row) == str(n) and not any(short(BALLS, row)) and 0 <= after - before <= 1,
              f'the balls panel shows {n}, in its font, centered with two cells before it: {panel(BALLS, row)!r}')
        x, y, image, colors, size = struct.unpack('<hhHHB', game.xram(slot_sprite(BALLS, 0), 9))
        cells = panel_left(BALLS) + (sym['PANEL_BORDER'] + before) * 8
        check(image == sym['XRAM_BALL_ICON_IMAGE'] and colors == sym['XRAM_PALETTE_MAIN'] and
              size == (icon // 4 - 1) << 4 | (icon // 4 - 1) and cells <= x and x + icon <= cells + 16 and
              y == sym['PANEL_Y'] + row * 8 - 1, f'and the ball icon of the counts in those cells: {x}, {y}')

    def sled_picture(p):
        """Panel p's picture is the sled of rank SLED_PICTURE, doubled and
        centered on the panel, with its jets."""
        rank = sym['SLED_PICTURE']
        width, doubled = tune[SIZE][0][rank], sym['MODE5_HDOUBLE'] | sym['MODE5_VDOUBLE']
        x, _, _, _, size, attributes = struct.unpack('<hhHHBB', game.xram(slot_sprite(p, 0), 10))
        jets = game.shown(slot_sprite(p, 1), sym['PICTURE_SPRITES'] - 1)
        check(size == (8 // 4 - 1) << 4 | ((width + 3) // 4 - 1) and attributes & doubled == doubled and
              x == panel_left(p) + (sym['PANEL_COLS'] * 8 - 2 * width) // 2 and jets == game.ram(f'jets+{rank}'),
              f'panel {p} shows the sled of rank {rank}, {width} px, doubled and centered, with its {jets} jets')

    def settle():
        game.run(40)

    # The level ends: the menu, with TO THE DRY picked, takes no choice for a
    # moment. The ball launched is the last, poked under the sled, falling.
    game.tap('space')
    game.paused_poke([('balls', 0, 1), ('ball_y', 225 << 8, 4), ('ball_vx', 0, 2), ('ball_vy', 600, 2)])
    game.wait('out of balls', 60)
    game.run(2)
    check(game.ram('game_state') == sym['STATE_MENU'], 'the menu opens when the level ends')
    check(game.ram('paddle_state') == sym['PADDLE_LEAVING'], 'and out of balls, the sled flies home')
    check(all(game.shows(w) for w in ['OUT OF BALLS'] + END_ITEMS), 'it says OUT OF BALLS, with its items')
    check(end_picked() == 'TO THE DRY', 'THE DRY is picked')
    check(cursor_on_item('end_menus', 0), 'and the cursor is on it at once')
    game.tap('space')
    game.run(10)
    check(game.ram('game_state') == sym['STATE_MENU'], 'a choice right away is not taken')
    game.run(60)

    # Every up and down key moves the pick, no left or right key does, the
    # menu doesn't wrap, and keypad 0, which only launches, does not choose.
    for key in ['down', 'up', 's', 'w', 'kp2', 'kp8', 'pad 0 down', 'pad 0 up']:
        was = end_picked()
        game.tap(key)
        check(end_picked() != was, f'{key} moves the pick')
    for key in ['right', 'left', 'd', 'a', 'kp6', 'kp4', 'pad 0 right', 'pad 0 left']:
        was = end_picked()
        game.tap(key)
        check(end_picked() == was, f'{key} does not move the pick')
    game.tap('up')
    check(end_picked() == 'TO THE DRY', 'up from the first stays: the menu does not wrap')
    for _ in END_ITEMS:
        game.tap('down')
    check(end_picked() == 'MAIN MENU', 'down from the last stays')
    game.tap('up')
    game.tap('up')
    print('ok: up and down move the pick, without wrapping, and left and right do not')
    game.tap('kp0')
    check(game.ram('game_state') == sym['STATE_MENU'], 'keypad 0 does not choose')

    # The upgrade screen, with no nuggets: a panel for each upgrade, the
    # first lit in the middle, each with what its first rank does and its
    # cost, in short digits, and nothing to buy.
    stock([])
    game.menu_choose('TO THE DRY', wait=False)
    game.talk_ok()  # the dwarf's first word on the screen
    game.run(20)  # past the flicker of the panel in the middle
    check(game.ram('panel_picked') == 0 and game.ram('cursor_on') == sym['ON_RAIL'],
          'it opens on the rail, with the first panel picked')
    check(cursor_on_panel(), 'and the cursor around it, as tall as its frame')
    for p in (BALLS, WEIGHT, EFFICIENCY):
        panel_shows(p)
    balls_picture(tune[BALLS][0][0])
    check(panel_lit(0) and not panel_lit(1), 'the middle panel is lit and the next one dim')
    # The weight and efficiency panels' pictures are the weight and the
    # jerrycan, centered at the top of their plates, a whole cell clear of
    # the title, in their own colors, dim, as the panels are.
    build = os.path.dirname(os.path.dirname(rom()))
    art = lambda name: open(os.path.join(build, name), 'rb').read()

    def own_picture(p, name):
        x, y, image, colors, size = struct.unpack('<hhHHB', game.xram(slot_sprite(p, 0), 9))
        w, h = sym[f'{name.upper()}_W'], sym[f'{name.upper()}_H']
        check(size == (h // 4 - 1) << 4 | (w // 4 - 1) and x == panel_left(p) + (8 * sym['PANEL_COLS'] - w) // 2 and
              y == sym['PANEL_Y'] + sym['PICTURE_ROW'] * 8 and y + h + 8 <= sym['PANEL_Y'] + sym['TITLE_ROW'] * 8,
              f'the {name} is {w} across, centered on its panel, a cell clear of the title: {x}, {y}')
        check(game.xram(image, w * h // 2) == art(f'{name}.bin') and
              game.xram(colors, 32) == art(f'{name}-colors.bin')[32:], f'the {name} is in its own colors, dim')

    own_picture(WEIGHT, 'weight')
    own_picture(EFFICIENCY, 'jerrycan')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram('upgrade_ranks', sym['UPGRADES']) == 0, 'no upgrade without the nuggets')

    # Right slides the panels left, the next one lit in the middle, and the
    # picture slides with its panel. The panels after come in as it goes,
    # speed and size, each with the sled. At the last panel, right does
    # nothing.
    picture = game.sprite(f'XRAM_MENU_SPRITES')[0]
    game.tap('right')
    settle()
    check(game.ram('panel_picked') == 1 and game.ram('panel_scroll', 2) == sym['PANEL_STEP'],
          'right slides the next panel to the middle')
    check(game.sprite(f'XRAM_MENU_SPRITES')[0] == picture - sym['PANEL_STEP'],
          'the picture slides with its panel')
    check(panel_lit(1) and not panel_lit(0), 'and it is lit, the one it left dim')
    check(cursor_on_panel(), 'the cursor stays around the panel in the middle')
    panel_shows(SPEED)
    sled_picture(SPEED)
    game.tap('right')
    settle()
    check(cursor_on_panel(), 'the cursor stays around the panel in the middle')
    panel_shows(SIZE)
    sled_picture(SIZE)
    for _ in range(sym['PANELS']):
        game.tap('right')
    settle()
    check(game.ram('panel_picked') == sym['PANELS'] - 1, 'right stops at the last panel')
    check(cursor_on_panel(), 'the cursor is around it')
    for _ in range(sym['PANELS']):
        game.tap('left')
    settle()
    check(game.ram('panel_picked') == 0 and game.ram('panel_scroll', 2) == 0, 'and left at the first')
    game.cmd('press right')
    game.run(sym['REPEAT_DELAY'] + 2)
    game.cmd('release right')
    check(game.ram('panel_picked') == 2, 'held, right repeats')
    game.cmd('press left')
    game.run(sym['REPEAT_DELAY'] + 2)
    game.cmd('release left')
    settle()
    check(game.ram('panel_picked') == 0, 'and so does left')
    print('ok: the panels slide')

    # The cheats of a debug build: on the rail, Shift and right or left raise
    # or lower the upgrade picked, for nothing, and repeat while held, up to
    # the top rank and back down to none.
    held = sym['REPEAT_DELAY'] + sym['REPEAT_STEPS'] * sym['UPGRADE_RANKS_MAX']  # past any top rank
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('upgrade_ranks') == 1 and not any(nuggets()), 'Shift and right raises the balls, for nothing')
    balls_picture(tune[BALLS][0][1])
    game.tap('left')
    check(game.ram('upgrade_ranks') == 0, 'Shift and left lowers it')
    game.cmd('press right')
    game.run(held)
    game.cmd('release right')
    check(game.ram('upgrade_ranks') == len(tune[BALLS][1]), 'held, it repeats, up to the top rank and no further')
    game.cmd('press left')
    game.run(held)
    game.cmd('release left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram('upgrade_ranks') == 0, 'and back down to none')
    print('ok: the upgrade cheats')

    # With the nuggets they cost: each rank of balls, at its cost, in its
    # color. After each, the panel shows the next rank and its cost, in the
    # font, with the nuggets for it, and its count of balls.
    stock(tune[BALLS][1])
    for rank in range(1, len(tune[BALLS][1]) + 1):
        buy(BALLS)
        panel_shows(BALLS)
        balls_picture(tune[BALLS][0][rank])
    print('ok: bought the balls')

    # With one too few nuggets of the color of weight's first cost, and as
    # many of every other color as it costs, weight can't be bought. With
    # them, it buys, for that color only, and the next rank shows its own
    # cost and color.
    game.tap('right')
    price, color = tune[WEIGHT][1][0]
    stock([(price, c) for c in range(colors)])
    game.poke(f'nuggets+{2 * color}', price - 1, 2)
    have = nuggets()
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram(f'upgrade_ranks+{WEIGHT}') == 0 and nuggets() == have,
          f'with {price - 1} {names[color]} nuggets, and {price} of every other color, weight 1 is not bought')
    game.poke(f'nuggets+{2 * color}', price, 2)
    buy(WEIGHT)
    panel_shows(WEIGHT)
    # Lowered again with the cheat, so the ball's damage on level 2 is the
    # first rank's.
    game.cmd('press lshift')
    game.tap('left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram(f'upgrade_ranks+{WEIGHT}') == 0, 'the cheat lowers the weight again')
    print('ok: weight, in the color of its cost')

    # A rank of fuel efficiency, on the next panel, and of speed, on the one
    # after.
    for p in (EFFICIENCY, SPEED):
        game.tap('right')
        stock(tune[p][1][:1])
        buy(p)

    # On the last panel, every line of the counts showing, with the button
    # held, every rank of width, then MAX. The counts show what is left.
    game.tap('right')
    game.poke('counts_shown', game.ram('counts_shown') | (1 << colors) - 1)
    stock(tune[SIZE][1], SPARE)
    ranks = len(tune[SIZE][1])
    game.cmd('press space')
    game.run(sym['REPEAT_DELAY'] + sym['REPEAT_STEPS'] * ranks)
    game.cmd('release space')
    game.wait(f'bought width {ranks}', 10)
    game.run(2)
    have = [SPARE] * colors
    check(game.ram(f'upgrade_ranks+{SIZE}') == ranks and nuggets() == have,
          'held, the button buys every rank, each at its cost')
    digits = lambda c: sym['XRAM_NUGGET_DIGITS'] + c * sym['COUNT_DIGITS'] * sym['SPRITE_BYTES']
    check([game.count(digits(c), sym['COUNT_DIGITS']) for c in range(colors)] == have,
          'the counts show what is left')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(nuggets() == have, 'nothing more to buy at the top rank')
    panel_shows(SIZE)
    print('ok: bought every width')

    # Down goes to the levels, where only the open ones can be picked.
    game.tap('down')
    check(game.ram('cursor_on') == sym['ON_LEVELS'], 'down moves the cursor to the levels')
    game.tap('right')
    check(game.ram('level_picked') == 1, 'level 2 is locked until level 1 is cleared')

    # On the levels, Shift and right opens the next level, with its unlock,
    # and another cuts that short and opens the one after. Shift and left
    # locks them again.
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('levels_cleared') == 1 and game.ram('unlocking') == 2,
          'Shift and right opens level 2, to unlock')
    game.tap('right')
    check(game.ram('levels_shown') == 2 and game.ram('unlocking') == 3,
          'another cuts the unlock short, and opens level 3')
    game.tap('left')
    game.tap('left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram('levels_cleared') == 0 and game.ram('unlocking') == 0 and
          game.ram('level_picked') == 1 and game.ram('levels_shown') == 1, 'Shift and left locks them again')
    print('ok: the level cheats')

    # Esc asks to go back to the title, and Esc again doesn't.
    game.tap('escape')
    check(game.shows('RETURN TO TITLE?'), 'Esc asks to go back to the title')
    check(not cursor_on_item('begin_menu', 0), 'the cursor slides to the question')
    settle()
    check(cursor_on_item('begin_menu', 0), 'and comes to its YES')
    game.tap('escape')
    check(not game.shows('RETURN TO TITLE?'), 'Esc again does not')

    # The button on a level asks to begin it, with YES picked, and YES plays
    # it with the upgrades bought.
    game.tap('space')
    check(game.shows('BEGIN LEVEL 1?'), 'the button asks to begin the level')
    # Text an odd number of letters long goes half a cell over, so it is
    # centered in the box too: YES in the halves of art/menus.py, from a
    # space to a space, either side of the box's middle.
    center, top = game.ram('begin_menu'), game.ram('begin_menu+1')
    yes_row = top + sym['HEAD_ROWS'] + 1
    cells = game.xram(sym['XRAM_MENU_MAP'] + yes_row * sym['TEXT_COLS'] + center - 2, 4)
    halves = menus.pairs()
    check(list(cells) == [sym['MENU_TILE_HALF'] + halves.index(p) for p in (' Y', 'YE', 'ES', 'S ')],
          f'YES goes half a cell over, centered in the box: {list(cells)}')
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    game.ready()
    width, px = tune[SIZE][0][-1], tune[SPEED][0][1]
    check(game.ram('paddle_width') == width, f'the paddle is {width} px wide now')
    speed = game.ram('paddle_speed', 2)
    check(abs(speed - px * 256 / 60) <= 0.5, f'and moves {px} px a second: {speed} 1/256 px a step')
    size = (8 // 4 - 1) << 4 | ((width + 3) // 4 - 1)  # MODE5_SIZE(SLED_IMAGE_W(width), 8)
    check(game.sizes('XRAM_SLED_SPRITE', 1)[0] == size, f'the sled shows {width} px wide')
    jets = game.ram(f'jets+{ranks}')
    check(game.shown('XRAM_JET_SPRITES', sym['JETS_MAX']) == jets, f'with its {jets} jets')
    balls = tune[BALLS][0][-1]
    check(game.ram('ball_state') == sym['BALL_DOCKED'] and game.ram('balls') == balls - 1 and
          game.count('XRAM_BALL_DIGITS', sym['BALL_DIGITS']) == balls - 1,
          f'the level starts with the {balls} balls bought: one on the sled, and {balls - 1} in the count')
    check(nuggets() == have, 'the nuggets left are kept')
    # Short of the wall: the steps it takes from the middle of the playfield.
    x = game.px('paddle_x')
    steps = min(20, (x - game.ram('play_left', 2)) * 256 // speed)
    game.cmd('press left')
    game.run(steps)
    game.cmd('release left')
    moved = x - game.px('paddle_x')
    check(abs(moved - (steps - 1) * speed / 256) <= speed / 256 + 1,
          f'the paddle moves at its new speed, {moved} px in {steps} steps')
    print(f'ok: a {width} px paddle moving {speed / 256} px a step')
    game.cmd('press space')
    game.wait('launch', 5)
    game.cmd('release space')
    full = game.ram('energy', 2)
    game.run(60)
    burn, burned = tune[EFFICIENCY][0][1], full - game.ram('energy', 2)
    check(55 * burn <= burned <= 65 * burn, f'and the fuel burns {burn} a step, burned {burned} in 60')

    # The first clear of level 1 earns a coin and opens level 2, which the
    # upgrade screen picks. Clearing it again earns nothing.
    def clear():
        game.ready()
        game.tap('space')
        game.run(20)
        game.paused_poke([('bricks_left', 0, 1)])
        game.wait('level cleared', 10)
        game.run(2)

    clear()
    check(game.ram('coins', 2) == 1 and game.ram('levels_cleared') == 1, 'a coin for clearing level 1')
    check(game.count('XRAM_COIN_DIGITS', sym['COUNT_DIGITS']) == 1, 'the count shows it')

    # The sled flies home, down off the screen under its own power: level,
    # its flames burning, with no smoke.
    check(game.ram('paddle_state') == sym['PADDLE_LEAVING'], 'the sled flies home when the level is cleared')
    sled, size, heights = 'XRAM_SLED_SPRITE', game.sizes('XRAM_SLED_SPRITE', 1)[0], []
    for _ in range(150):
        if game.ram('paddle_state') == sym['PADDLE_GONE']:
            break
        heights.append(game.sprite(sled)[1])
        check(game.sizes(sled, 1)[0] == size and game.shown('XRAM_SMOKE_SPRITES', sym['JETS_MAX']) == 0 and
              game.sprites('XRAM_JET_SPRITES', 1)[0][2] != sym['XRAM_JET_IMAGES'] + sym['JET_NOZZLE'] *
              sym['JET_IMAGE_BYTES'], 'level, its flames burning, with no smoke')
        game.run(1)
    check(game.ram('paddle_state') == sym['PADDLE_GONE'] and heights == sorted(heights) and
          heights[-1] > heights[0] and game.shown(sled, 1) == 0, 'down off the screen')
    game.talk_ok()  # the dwarf hands it over
    game.menu_choose('REPLAY')
    clear()
    check(game.ram('coins', 2) == 1, 'no coin for clearing it again')
    game.menu_choose('TO THE DRY')
    game.run(5)
    check(game.ram('level_picked') == 1 and game.ram('cart_scroll', 2) == 0,
          'the upgrade screen opens on level 1, just cleared')
    check(game.ram('unlocking') == 2 and game.shown(sym['XRAM_HALF_SPRITES'], 2) == 2,
          'and the lock of level 2 shows, to break')
    locked = min(sym['LOCKS'], sym['LEVELS'] - 2)
    check(game.shown(sym['XRAM_LOCK_SPRITES'], sym['LOCKS']) == locked,
          f'with padlocks on the {locked} carts locked after it')
    game.wait('unlocked 2', 200)
    check(game.ram('levels_shown') == 2 and game.ram('unlocking') == 0 and game.ram('level_picked') == 2,
          'the lock breaks, and level 2 shows open, picked')
    game.run(40)
    check(game.ram('cart_scroll', 2) == sym['CART_STEP'], 'and the train slides over to it')
    game.talk_ok()  # the dwarf who says what the unlock means
    game.tap('down')
    game.tap('space')
    check(game.shows('BEGIN LEVEL 2?'), 'and asks to begin level 2')
    game.tap('space')
    game.until('game_state', 'STATE_PLAY', 30)
    game.ready()
    print('ok: a coin for the first clear, and the next level')

    # Level 2 lays its bricks, each in its color. Its lowest brick, poked
    # red, to break at three hits of the ball's damage, cracks more with each
    # hit, by the steps of CRACK_STATES it is broken, rounded up, and the
    # third breaks it, into red chunks and a red nugget, which lands in the
    # red line of the counts. For each hit, the ball is poked under it,
    # rising.
    bricks, step, red = sym['LEVEL2_BRICKS'], sym['SPRITE_BYTES'], sym['BRICK_RED']
    palette = lambda addr: struct.unpack('<H', game.xram(addr + 6, 2))[0]
    looks = [game.ram(f'brick_color+{i}') for i in range(bricks)]
    check(game.ram('bricks_left') == bricks and
          [palette(sym['XRAM_BRICKS'] + i * step) for i in range(bricks)] == [brick_palette(c) for c in looks],
          f'level 2 lays its {bricks} bricks, each in its color: {looks}')
    ys = [game.ram(f'brick_y+{2 * i}', 2, signed=True) for i in range(bricks)]
    i = ys.index(max(ys))
    x, y = game.ram(f'brick_x+{2 * i}', 2, signed=True), ys[i]
    damage = tune[WEIGHT][0][0]
    hits, was = 3 * damage, nuggets()[red]
    under = [('ball_x', x + 8 << 8, 4), ('ball_y', y + sym['BRICK_H'] + 4 << 8, 4), ('ball_vx', 0, 2),
             ('ball_vy', -512, 2)]
    game.tap('space', 2)
    game.paused_poke([(f'brick_color+{i}', red, 1), (f'brick_hits+{i}', hits, 1), ('balls', 2, 1)] + under)
    crack = sym['XRAM_CRACK_SPRITES'] + i * sym['CRACK_PIECES'] * step
    for hit in (1, 2):
        cracks = -(-hit * damage * sym['CRACK_STATES'] // hits)
        game.wait(f'cracked {i}, {hit * damage} of {hits}', 60)
        game.run(1)
        cx, cy, image, crack_palette, _, mode = struct.unpack('<hhHHBB', game.xram(crack, step))
        state = (image - sym['XRAM_CRACK_IMAGES']) // sym['CRACK_IMAGE_BYTES'] % sym['CRACK_STATES'] + 1
        check(x <= cx <= x + sym['BRICK_W'] - sym['CRACK_W'] and cy == y and state == cracks and
              mode & 3 == sym['MODE5_2BPP'] and crack_palette == brick_palette(red) + 2 * sym['BRICK_CRACK_COLORS'],
              f'hit {hit} cracks a red brick {cracks} steps of {sym["CRACK_STATES"]}: it shows {state}')
        game.paused_poke(under)
    game.wait(f'brick {i},', 60)
    game.run(1)
    check(game.shown(crack, 1) == 0, 'the third breaks it, and its cracks are gone')
    first = (game.ram('chunk_next') - sym['CHUNKS_PER_BREAK']) % sym['CHUNKS_MAX']
    check(palette(sym['XRAM_CHUNK_SPRITES'] + first * step) == brick_palette(red), 'it breaks into red chunks')
    game.wait('nugget landed', 120)
    game.run(1)
    icon = sym['XRAM_NUGGET_ICONS'] + red * step
    check(game.sprite(icon) == (sym['ICON_X'], sym['ICON_TOP'] + (red + 1) * sym['LINE_H'] - 1) and
          nuggets()[red] == was + 1, 'its nugget lands in the red line of the counts, and counts')
    game.close()
    print('ok: level 2, and a red brick')
    print('PASS')


if __name__ == '__main__':
    main()
