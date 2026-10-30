#!/usr/bin/env python3
"""Checks the menu when a level ends and the upgrade screen, in the emulator.

  upgrades.py rom.rp6502

Needs a Debug ROM, which logs the game's events. The nugget count is poked
to buy with. Reads the menus from the text cells in XRAM, and the panels
from their own text cells. Exits 0 when every check passes.
"""

import os
import struct
import sys

from game import Game, check, rom

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art'))
from panels import FONT, LAYOUTS  # noqa: E402
import menus  # noqa: E402

END_ITEMS = ['TO THE DRY', 'REPLAY', 'MAIN MENU']

# The upgrades in the order of their panels: the name of tuning.h's values,
# the table of them in src/upgrades.c and the bytes of each, and the name of
# its ranks and costs.
UPGRADES = [('BALLS', 'ball_counts', 1, 'BALL'), ('DAMAGES', 'damages', 1, 'DAMAGE'),
            ('BURNS', 'burns', 1, 'BURN'), ('SPEEDS', 'speeds', 2, 'SPEED'), ('WIDTHS', 'widths', 1, 'WIDTH')]


def tuning(game):
    """The upgrade tables of src/upgrades.c, from RAM: each upgrade's values,
    from the one before any upgrade, and the cost of each rank after it,
    which tuning.h gives with its color in the top bits. The costs here are
    the counts of nuggets, and TUNE_BALL_COLORS and the like their colors."""
    shift = game.sym['COST_COLOR_SHIFT']
    tune = {}
    for values, table, size, name in UPGRADES:
        ranks = game.sym[f'{name}_RANKS']
        tune[f'TUNE_{values}'] = [game.ram(f'{table}+{i * size}', size) for i in range(ranks + 1)]
        costs = [game.ram(f'{name.lower()}_costs+{2 * i}', 2) for i in range(ranks)]
        tune[f'TUNE_{name}_COSTS'] = [c & ((1 << shift) - 1) for c in costs]
        tune[f'TUNE_{name}_COLORS'] = [c >> shift for c in costs]
    return tune


def main():
    game = Game()
    sym = game.sym
    tune = tuning(game)
    game.cmd('pad 0 connect')
    game.new_game()
    game.run(5)

    # A new game's level starts with the balls before any upgrade: one on
    # the sled, and the rest in the count.
    first = tune['TUNE_BALLS'][0]
    check(game.ram('ball_state') == sym['BALL_DOCKED'] and game.ram('balls') == first - 1 and
          game.count('XRAM_BALL_DIGITS', sym['BALL_DIGITS']) == first - 1,
          f'a new game starts with {first} ball: one on the sled, and {first - 1} in the count')

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

    nugget = lambda color: (sym['XRAM_NUGGET_ICON_IMAGE'], sym['XRAM_PALETTE_BRICKS'] + 32 * color)

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
        filled = [c for c, t in enumerate(panel_tiles(0, row)) if (t - 1) % dim]
        first = filled[0] if filled else 0
        before, after = first - 2, sym['PANEL_INSIDE'] - first - len(str(n))
        check(panel(0, row) == str(n) and not any(short(0, row)) and 0 <= after - before <= 1,
              f'the balls panel shows {n}, in its font, centered with two cells before it: {panel(0, row)!r}')
        x, y, image, colors, size = struct.unpack('<hhHHB', game.xram(slot_sprite(0, 0), 9))
        cells = panel_left(0) + (sym['PANEL_BORDER'] + before) * 8
        check(image == sym['XRAM_BALL_ICON_IMAGE'] and colors == sym['XRAM_PALETTE_MAIN'] and
              size == (icon // 4 - 1) << 4 | (icon // 4 - 1) and cells <= x and x + icon <= cells + 16 and
              y == sym['PANEL_Y'] + row * 8 - 1, f'and the ball icon of the counts in those cells: {x}, {y}')

    def sled_picture(p):
        """Panel p's picture is the sled of rank SLED_PICTURE, doubled and
        centered on the panel, with its jets."""
        rank = sym['SLED_PICTURE']
        width, doubled = tune['TUNE_WIDTHS'][rank], sym['MODE5_HDOUBLE'] | sym['MODE5_VDOUBLE']
        x, _, _, _, size, attributes = struct.unpack('<hhHHBB', game.xram(slot_sprite(p, 0), 10))
        jets = game.shown(slot_sprite(p, 1), sym['PICTURE_SPRITES'] - 1)
        check(size == (8 // 4 - 1) << 4 | ((width + 3) // 4 - 1) and attributes & doubled == doubled and
              x == panel_left(p) + (sym['PANEL_COLS'] * 8 - 2 * width) // 2 and jets == game.ram(f'jets+{rank}'),
              f'panel {p} shows the sled of rank {rank}, {width} px, doubled and centered, with its {jets} jets')

    def settle():
        game.run(40)

    # The level ends: the menu, with TO THE DRY picked, takes no choice for a
    # moment. The count is emptied, whatever a new game starts with, so the
    # ball launched is the last.
    game.tap('space')
    game.poke('balls', 0)
    game.wait('out of balls', 3000)
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
    # first lit in the middle, and nothing to buy.
    game.poke('nuggets', 0, 2)
    game.menu_choose('TO THE DRY', wait=False)
    game.talk_ok()  # the dwarf's first word on the screen
    game.run(20)  # past the flicker of the panel in the middle
    check(game.ram('panel_picked') == 0 and game.ram('cursor_on') == sym['ON_RAIL'],
          'it opens on the rail, with the first panel picked')
    check(cursor_on_panel(), 'and the cursor around it, as tall as its frame')
    title, effect, cost = sym['TITLE_ROW'], sym['EFFECT_ROW'], sym['COST_ROW']
    check([panel(p, title) for p in range(3)] == ['BALLS', 'WEIGHT', 'EFFICIENCY'],
          'the panels show their titles')
    counts = tune['TUNE_BALLS']
    check(panel(0, effect) == f'{counts[0]} \x10 {counts[1]} BALLS', 'and what the next count of balls is')
    check(panel(0, cost) == str(tune['TUNE_BALL_COSTS'][0]) and cost_icon(0) == nugget(sym['BRICK_GRAY']),
          'and what it costs, by a gray nugget')
    balls_picture(counts[0])
    damages = tune['TUNE_DAMAGES']
    check(panel(1, effect) == f'{damages[0]} \x10 {damages[1]} DAMAGE', "the ball's damage has its panel")
    burns = [f'{b // 10}.{b % 10}' for b in tune['TUNE_BURNS']]
    check(panel(2, effect) == f'{burns[0]} \x10 {burns[1]} L/S' and
          panel(2, cost) == str(tune['TUNE_BURN_COSTS'][0]),
          f'and efficiency, in liters a second: {panel(2, effect)!r}')
    check(panel_lit(0) and not panel_lit(1), 'the middle panel is lit and the next one dim')
    # The size and speed panels' picture is the smallest sled with two jets.
    rank = sym['SLED_PICTURE']
    check(game.ram(f'jets+{rank}') == 2 and game.ram(f'jets+{rank - 1}') < 2,
          f'size and speed show the sled of rank {rank}, the smallest with two jets')
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

    own_picture(1, 'weight')
    own_picture(2, 'jerrycan')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram('upgrade_ranks', sym['UPGRADES']) == 0, 'no upgrade without the nuggets')

    # Right slides the panels left, the next one lit in the middle, and the
    # picture slides with its panel. The panels after come in as it goes:
    # speed, in pixels a second, and size, in pixels, each with the sled.
    # At the last panel, right does nothing.
    picture = game.sprite(f'XRAM_MENU_SPRITES')[0]
    game.tap('right')
    settle()
    check(game.ram('panel_picked') == 1 and game.ram('panel_scroll', 2) == sym['PANEL_STEP'],
          'right slides the next panel to the middle')
    check(game.sprite(f'XRAM_MENU_SPRITES')[0] == picture - sym['PANEL_STEP'],
          'the picture slides with its panel')
    check(panel_lit(1) and not panel_lit(0), 'and it is lit, the one it left dim')
    check(cursor_on_panel(), 'the cursor stays around the panel in the middle')
    speeds = [s * 60 // 256 for s in tune['TUNE_SPEEDS']]
    check(panel(3, title) == 'SPEED' and panel(3, effect) == f'{speeds[0]} \x10 {speeds[1]} PX/S' and
          panel(3, cost) == str(tune['TUNE_SPEED_COSTS'][0]),
          f'the speed panel comes in, in pixels a second: {panel(3, effect)!r}')
    sled_picture(3)
    game.tap('right')
    settle()
    check(cursor_on_panel(), 'the cursor stays around the panel in the middle')
    widths = tune['TUNE_WIDTHS']
    check(panel(4, title) == 'SIZE' and panel(4, effect) == f'{widths[0]} \x10 {widths[1]} PX' and
          panel(4, cost) == str(tune['TUNE_WIDTH_COSTS'][0]),
          f'and the last, size, in pixels: {panel(4, effect)!r}')
    sled_picture(4)
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
    # or lower the upgrade picked, for nothing, and repeat while held. Balls,
    # on the first panel, has few ranks, so held, it goes to the top and
    # stops there.
    game.cmd('press lshift')
    game.tap('right')
    check(game.ram('upgrade_ranks') == 1 and game.ram('nuggets', 2) == 0,
          'Shift and right raises the balls, for nothing')
    balls_picture(counts[1])
    game.tap('left')
    check(game.ram('upgrade_ranks') == 0, 'Shift and left lowers it')
    game.cmd('press right')
    game.run(sym['REPEAT_DELAY'] + 2 * sym['REPEAT_STEPS'] + 2)
    game.cmd('release right')
    check(game.ram('upgrade_ranks') == sym['BALL_RANKS'], 'held, it repeats, up to the top rank and no further')
    game.cmd('press left')
    game.run(sym['REPEAT_DELAY'] + sym['REPEAT_STEPS'] * sym['UPGRADE_RANKS_MAX'])
    game.cmd('release left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram('upgrade_ranks') == 0, 'and back down to none')
    print('ok: the upgrade cheats')

    # With nuggets: each rank of balls, at its cost in gray, and the panel's
    # count goes up with each.
    have = 200
    game.poke('nuggets', have, 2)
    game.poke('counts_shown', 1 << sym['BRICK_GRAY'])
    for rank, (price, color) in enumerate(zip(tune['TUNE_BALL_COSTS'], tune['TUNE_BALL_COLORS']), 1):
        check(color == sym['BRICK_GRAY'] and panel(0, cost) == str(price), f'balls {rank} costs {price} gray')
        game.tap('space')
        game.wait(f'bought balls {rank}', 10)
        game.run(2)
        have -= price
        check(game.ram('nuggets', 2) == have, f'balls {rank} is bought for {price}')
        balls_picture(counts[rank])
    print('ok: bought the balls')

    # Weight's first rank costs red nuggets. With gray enough but no red, it
    # can't be bought: its cost shows in short digits, by a red nugget. With
    # red, it buys, and spends the red, not the gray. The next rank shows
    # its own cost and color.
    game.tap('right')
    price, color = tune['TUNE_DAMAGE_COSTS'][0], tune['TUNE_DAMAGE_COLORS'][0]
    check(color == sym['BRICK_RED'], 'weight 1 costs red nuggets')
    check(panel(1, cost) == str(price) and all(short(1, cost)),
          f'with no red, its cost, {price}, is in short digits')
    check(cost_icon(1) == nugget(color), 'by a red nugget')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram(f'upgrade_ranks+{sym["UPGRADE_DAMAGE"]}') == 0 and game.ram('nuggets', 2) == have,
          'gray nuggets do not buy it')
    # Just the red it costs, so none is left over for level 2, which counts
    # the first red nugget there.
    red = f'nuggets+{2 * color}'
    game.poke(red, price, 2)
    game.tap('space')
    game.wait('bought damage 1', 10)
    game.run(2)
    check(game.ram(red, 2) == 0 and game.ram('nuggets', 2) == have,
          f'with red, it buys for {price} red, and no gray')
    price, color = tune['TUNE_DAMAGE_COSTS'][1], tune['TUNE_DAMAGE_COLORS'][1]
    check(panel(1, cost) == str(price) and cost_icon(1) == nugget(color),
          'and the next rank shows its cost, by a nugget of its color')
    # Lowered again with the cheat, so the ball takes a single hit off a
    # brick on level 2, where the hits are counted.
    game.cmd('press lshift')
    game.tap('left')
    game.cmd('release lshift')
    game.run(2)
    check(game.ram(f'upgrade_ranks+{sym["UPGRADE_DAMAGE"]}') == 0, 'the cheat lowers the weight again')
    print('ok: weight, in red nuggets')

    # A rank of fuel efficiency, on the next panel, and of speed, on the one
    # after.
    game.tap('right')
    game.tap('space')
    game.wait('bought efficiency 1', 10)
    have -= tune['TUNE_BURN_COSTS'][0]
    check(game.ram('nuggets', 2) == have, 'fuel efficiency 1 costs its cost')
    game.tap('right')
    game.tap('space')
    game.wait('bought speed 1', 10)
    have -= tune['TUNE_SPEED_COSTS'][0]
    check(game.ram('nuggets', 2) == have, 'speed 1 costs its cost')

    # On the last panel, a rank of width at its cost, then, with the button
    # held, every other rank, then MAX. The count shows what is left.
    game.tap('right')
    game.tap('space')
    game.wait('bought width 1', 10)
    have -= tune['TUNE_WIDTH_COSTS'][0]
    check(game.ram('nuggets', 2) == have, f'width 1 costs {tune["TUNE_WIDTH_COSTS"][0]}')
    game.cmd('press space')
    game.run(sym['REPEAT_DELAY'] + sym['REPEAT_STEPS'] * len(tune['TUNE_WIDTH_COSTS']))
    game.cmd('release space')
    game.wait(f'bought width {len(tune["TUNE_WIDTH_COSTS"])}', 10)
    have -= sum(tune['TUNE_WIDTH_COSTS'][1:])
    width_rank = f'upgrade_ranks+{sym["UPGRADE_WIDTH"]}'
    check(game.ram(width_rank) == len(tune['TUNE_WIDTH_COSTS']) and game.ram('nuggets', 2) == have,
          'held, the button buys every rank, each at its cost')
    check(game.count('XRAM_NUGGET_DIGITS', sym['COUNT_DIGITS']) == have, 'the count shows what is left')
    game.tap('space')
    game.cmd('expect-not "bought"')
    check(game.ram('nuggets', 2) == have, 'nothing more to buy at the top rank')
    check(panel(4, cost) == 'MAX', 'the top rank shows MAX')
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
    # it with the paddle upgraded.
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
    width, speed = widths[-1], tune['TUNE_SPEEDS'][1]
    check(game.ram('paddle_width') == width, f'the paddle is {width} px wide now')
    check(game.ram('paddle_speed', 2) == speed, f'and moves {speed} a step')
    size = (8 // 4 - 1) << 4 | ((width + 3) // 4 - 1)  # MODE5_SIZE(SLED_IMAGE_W(width), 8)
    check(game.sizes('XRAM_SLED_SPRITE', 1)[0] == size, f'the sled shows {width} px wide')
    jets = game.ram(f'jets+{len(tune["TUNE_WIDTH_COSTS"])}')
    check(game.shown('XRAM_JET_SPRITES', sym['JETS_MAX']) == jets, f'with its {jets} jets')
    balls = counts[len(tune['TUNE_BALL_COSTS'])]
    check(game.ram('ball_state') == sym['BALL_DOCKED'] and game.ram('balls') == balls - 1 and
          game.count('XRAM_BALL_DIGITS', sym['BALL_DIGITS']) == balls - 1,
          f'the level starts with the {balls} balls bought: one on the sled, and {balls - 1} in the count')
    check(game.ram('nuggets', 2) == have, 'the nuggets left are kept')
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
    burn, burned = tune['TUNE_BURNS'][1], full - game.ram('energy', 2)
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

    # Level 2 is level 1 with red bricks in the middle of its top two rows,
    # and tougher: the gray take two hits and the red three. Each hit cracks
    # a red brick more, by the steps of CRACK_STATES it is broken, rounded
    # up, and the third breaks it, into red chunks and a red nugget, whose
    # line of the counts shows once it lands.
    bricks, step = sym['LEVEL2_BRICKS'], sym['SPRITE_BYTES']
    gray, red = sym['XRAM_PALETTE_BRICKS'], sym['XRAM_PALETTE_BRICKS'] + 32 * sym['BRICK_RED']
    palette = lambda addr: struct.unpack('<H', game.xram(addr + 6, 2))[0]
    colors = [palette(sym['XRAM_BRICKS'] + i * step) for i in range(bricks)]
    reds = [i for i, c in enumerate(colors) if c == red]
    check(game.ram('bricks_left') == bricks and reds == [1, 2, 5, 6] and colors.count(gray) == bricks - 4,
          f'level 2 has red bricks in the middle of its top two rows: {colors}')
    check(all(game.ram(f'brick_hits+{i}') == (3 if i in reds else 2) for i in range(bricks)),
          'the gray take two hits, and the red three')
    x, y = game.ram('brick_x+2', 2), game.ram('brick_y+2', 2)
    game.tap('space', 2)
    game.paused_poke([('ball_x', x + 8 << 8, 4), ('ball_y', sym['BEAM_H'] + 4 << 8, 4), ('ball_vx', 0, 2),
                      ('ball_vy', 512, 2)])
    for hit in (1, 2):
        steps = -(-hit * sym['CRACK_STATES'] // 3)
        game.wait(f'cracked 1, {hit} of 3', 60)
        game.run(1)
        cx, cy, image, crack_palette, _, mode = struct.unpack('<hhHHBB',
                                                               game.xram(sym['XRAM_CRACK_SPRITES'] + step, step))
        state = (image - sym['XRAM_CRACK_IMAGES']) // sym['CRACK_IMAGE_BYTES'] % sym['CRACK_STATES'] + 1
        check(x <= cx <= x + sym['BRICK_W'] - sym['CRACK_W'] and cy == y and state == steps and
              mode & 3 == sym['MODE5_2BPP'] and crack_palette == red + 2 * sym['BRICK_CRACK_COLORS'],
              f'hit {hit} cracks a red brick {steps} steps of {sym["CRACK_STATES"]}: it shows {state}')
    game.wait('brick 1,', 60)
    game.run(1)
    check(game.shown(sym['XRAM_CRACK_SPRITES'] + step, 1) == 0, 'the third breaks it, and its cracks are gone')
    first = (game.ram('chunk_next') - sym['CHUNKS_PER_BREAK']) % sym['CHUNKS_MAX']
    check(palette(sym['XRAM_CHUNK_SPRITES'] + first * step) == red, 'it breaks into red chunks')
    game.wait('nugget landed', 120)
    game.run(1)
    icon = sym['XRAM_NUGGET_ICONS'] + sym['BRICK_RED'] * step
    check(game.sprite(icon) == (sym['ICON_X'], sym['ICON_TOP'] + (sym['BRICK_RED'] + 1) * sym['LINE_H'] - 1) and
          game.ram(f'nuggets+{2 * sym["BRICK_RED"]}', 2) == 1, 'its nugget lands in the red line of the counts')
    game.close()
    print('ok: level 2, and a red brick')
    print('PASS')


if __name__ == '__main__':
    main()
