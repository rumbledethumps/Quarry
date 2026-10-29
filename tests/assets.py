#!/usr/bin/env python3
"""Checks that each asset the art scripts write is the size of what the game
loads it into, from the numbers of the .sym file beside the ROM.

  assets.py rom.rp6502

The art scripts lay out their files byte for byte as the structs of
src/xram.h, and the game copies them into XRAM as they are, so an asset of
another size means the two have drifted apart. The images that load as the
ROM starts are each where CMakeLists.txt puts them, and fill the room up to
what comes next. It also checks the rows of art/palettes.png the art
scripts draw in against the palettes of palettes_t. The assets are in the
build folder, beside the ROM's folder. The emulator isn't needed. Exits 0
when every check passes.
"""

import os
import re
import sys

from game import check, rom

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, os.path.join(HERE, '..', 'art'))
from rp6502 import Symbols  # noqa: E402
import bricks, frames, gauge, logo, screen, sled, texture  # noqa: E402, E401


def main():
    sym = Symbols(os.path.splitext(rom())[0] + '.sym')
    build = os.path.dirname(os.path.dirname(rom()))
    numbered = lambda name, count: [f'{name}{n}' for n in range(1, count + 1)]
    # Each asset, and the bytes it must be.
    exact = {'palettes': 'PALETTES_BYTES', 'backdrop': 'BACKDROP_BYTES', 'panels': 'PANELS_BYTES',
             'carts': 'CARTS_BYTES', 'menus': 'MENUS_BYTES', 'logo': 'LOGO_BYTES',
             'cracks': 'CRACKS_BYTES', 'chunks': 'CHUNKS_BYTES', 'gauge': 'GAUGE_BYTES'}
    exact.update({name: 'TEXTURE_BYTES' for name in numbered('texture', sym['TEXTURES'])})
    exact.update({name: 'CURTAIN_SET_BYTES' for name in numbered('curtain', sym['CURTAIN_SETS'])})
    exact.update({name: 'FRAME_SET_BYTES' for name in numbered('frame', sym['FRAME_SETS'])})
    exact.update({name: 'TALK_BYTES' for name in numbered('talk', sym['TALKS'])})
    size = lambda name: os.path.getsize(os.path.join(build, f'{name}.bin'))
    for name, bytes_name in exact.items():
        check(size(name) == sym[bytes_name], f'{name}.bin is {size(name)} bytes, not the {sym[bytes_name]} of {bytes_name}')
    levels = sym['LEVELS'] * sym['LEVEL_BYTES']
    check(size('levels') == levels, f'levels.bin is {size("levels")} bytes, not a LEVEL_BYTES for each level, {levels}')
    sleds = (sym['WIDTH_RANKS'] + 1) * sym['SLED_SLOT']
    check(size('sleds') == sleds, f'sleds.bin is {size("sleds")} bytes, not a SLED_SLOT for each width, {sleds}')
    print(f'ok: {len(exact) + 2} assets, each the size of what it loads into')

    # The images that load as the ROM starts, but the palettes, checked
    # whole above.
    cmake = open(os.path.join(HERE, '..', 'CMakeLists.txt')).read()
    images = re.findall(r'rp6502_asset\(quarry XRAM\((XRAM_\w+)\) \$\{CMAKE_CURRENT_BINARY_DIR\}/(\w+)\.bin\)', cmake)
    starts = sorted({value for name, value in sym.items() if name.startswith('XRAM_')})
    for at, name in images:
        if name != 'palettes':
            room = min(s for s in starts if s > sym[at]) - sym[at]
            check(size(name) == room, f'{name}.bin is {size(name)} bytes, but has {room} at {at}')
    print(f'ok: {len(images) - 1} images, each filling its room in XRAM')

    # The rows of art/palettes.png the art scripts draw in, each where its
    # palette is in palettes_t, 16 colors a row.
    row = lambda palette: (sym[f'XRAM_PALETTE_{palette}'] - sym['XRAM_PALETTES']) // 32
    rows = [(bricks, 'BRICK_ROW', 'BRICKS'), (bricks, 'SLED_ROW', 'SLED'),
            (logo, 'LOGO_ROW', 'LOGO'), (sled, 'SLED_ROW', 'SLED'), (screen, 'SLED_ROW', 'SLED'),
            (screen, 'FX_ROW', 'FX'), (screen, 'HOLO_ROW', 'HOLO'), (texture, 'TEXTURE_ROW', 'TEXTURE'),
            (frames, 'SLED_ROW', 'SLED'), (frames, 'SHADE_ROW', 'SHADE'),
            (gauge, 'LIQUID_ROW', 'LIQUID'), (gauge, 'FITTING_ROW', 'FITTING')]
    for module, name, palette in rows:
        check(getattr(module, name) == row(palette),
              f'art/{module.__name__}.py has {name} {getattr(module, name)}, but the {palette} palette is row {row(palette)}')
    print(f'ok: {len(rows)} palette rows of the art scripts')
    check(len(bricks.COLORS) == sym['BRICK_COLORS'] and bricks.CRACK_COLORS == sym['BRICK_CRACK_COLORS'],
          f'art/bricks.py draws {len(bricks.COLORS)} colors, their cracks from {bricks.CRACK_COLORS}, '
          f'and the game has {sym["BRICK_COLORS"]}, from {sym["BRICK_CRACK_COLORS"]}')
    print('ok: the brick colors and their cracks')
    print('PASS')


if __name__ == '__main__':
    main()
