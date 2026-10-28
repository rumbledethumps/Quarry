#!/usr/bin/env python3
"""Checks that each asset the art scripts write is the size of what the game
loads it into, from the numbers of the .sym file beside the ROM.

  assets.py rom.rp6502

The art scripts lay out their files byte for byte as the structs of
src/xram.h, and the game copies them into XRAM as they are, so an asset of
another size means the two have drifted apart. The assets are in the build
folder, beside the ROM's folder. The emulator isn't needed. Exits 0 when
every check passes.
"""

import os
import sys

from game import check, rom

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from rp6502 import Symbols  # noqa: E402


def main():
    sym = Symbols(os.path.splitext(rom())[0] + '.sym')
    build = os.path.dirname(os.path.dirname(rom()))
    numbered = lambda name, count: [f'{name}{n}' for n in range(1, count + 1)]
    # Each asset, and the bytes it must be. The carts' tiles are as many as
    # the art has, up to CART_TILES_MAX, so the carts may be less.
    exact = {'palettes': 'PALETTES_BYTES', 'backdrop': 'BACKDROP_BYTES', 'panels': 'PANELS_BYTES',
             'menus': 'MENUS_BYTES', 'logo': 'LOGO_BYTES'}
    exact.update({name: 'TEXTURE_BYTES' for name in numbered('texture', sym['TEXTURES'])})
    exact.update({name: 'CURTAIN_SET_BYTES' for name in numbered('curtain', sym['CURTAIN_SETS'])})
    exact.update({name: 'FRAME_SET_BYTES' for name in numbered('frame', sym['FRAME_SETS'])})
    exact.update({name: 'TALK_BYTES' for name in numbered('talk', sym['TALKS'])})
    size = lambda name: os.path.getsize(os.path.join(build, f'{name}.bin'))
    for name, bytes_name in exact.items():
        check(size(name) == sym[bytes_name], f'{name}.bin is {size(name)} bytes, not the {sym[bytes_name]} of {bytes_name}')
    check(size('carts') <= sym['CARTS_BYTES'], f'carts.bin is {size("carts")} bytes, more than CARTS_BYTES')
    sleds = (sym['WIDTH_RANKS'] + 1) * sym['SLED_SLOT']
    check(size('sleds') == sleds, f'sleds.bin is {size("sleds")} bytes, not a SLED_SLOT for each width, {sleds}')
    print(f'ok: {len(exact) + 2} assets, each the size of what it loads into')
    print('PASS')


if __name__ == '__main__':
    main()
