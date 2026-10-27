#!/usr/bin/env python3
"""Convert Quarry's PNG art into data for the RP6502 VGA.

  png2bin.py image [--tile WxH] [--slot N] in.png... out.bin
      An indexed PNG whose palette indexes are the 4-bit colors, 0 to 15.
      The image is cut into tiles of WxH, read left to right, then top to
      bottom, and each tile is written row by row, two pixels to a byte,
      the left pixel in the high nibble. Without --tile, the whole image is
      one tile. This is the format of mode 2 tiles and mode 5 sprites.
      Several images are written one after another, each padded with 0 to
      N bytes with --slot, so each one starts N bytes after the last.

  png2bin.py palette in.png out.bin
      A PNG 16 pixels wide. Each row is a 16-color palette, written as
      RGB555 with the alpha bit set on colors with alpha of 128 or more.

Only the Python standard library is used, so the build needs nothing more.
"""

import argparse
import struct
import sys
import zlib

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def fail(message):
    sys.exit(f'png2bin: {message}')


def read_png(path):
    """Return (width, height, color type, rows of samples, PLTE, tRNS)."""
    with open(path, 'rb') as f:
        data = f.read()
    if data[:8] != PNG_SIGNATURE:
        fail(f'{path}: not a PNG')
    pos = 8
    header = None
    plte = []
    trns = b''
    idat = []
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b'tRNS':
            trns = body
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
    if header is None:
        fail(f'{path}: no IHDR')
    width, height, depth, color, _, _, interlace = header
    if interlace:
        fail(f'{path}: interlaced PNGs are not supported')
    if color not in CHANNELS or depth == 16 or (depth < 8 and color not in (0, 3)):
        fail(f'{path}: unsupported PNG format (color type {color}, depth {depth})')

    channels = CHANNELS[color]
    bits = depth * channels
    stride = (width * bits + 7) // 8
    bpp = max(1, bits // 8)
    raw = zlib.decompress(b''.join(idat))
    rows = []
    prev = bytearray(stride)
    i = 0
    for _ in range(height):
        kind = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if kind == 1:
                line[x] = (line[x] + a) & 0xFF
            elif kind == 2:
                line[x] = (line[x] + b) & 0xFF
            elif kind == 3:
                line[x] = (line[x] + (a + b) // 2) & 0xFF
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[x] = (line[x] + pred) & 0xFF
            elif kind != 0:
                fail(f'{path}: bad filter type {kind}')
        prev = line
        if depth < 8:
            per_byte = 8 // depth
            mask = (1 << depth) - 1
            samples = [(line[x // per_byte] >> (8 - depth * (x % per_byte + 1))) & mask
                       for x in range(width)]
            rows.append([(s,) for s in samples])
        else:
            rows.append([tuple(line[x * channels:(x + 1) * channels])
                         for x in range(width)])
    return width, height, color, rows, plte, trns


def image(path, tile):
    width, height, color, rows, _, _ = read_png(path)
    if color != 3:
        fail(f'{path}: an image must be an indexed PNG')
    tw, th = tile or (width, height)
    if tw % 2 or width % tw or height % th:
        fail(f'{path}: {width}x{height} does not divide into {tw}x{th} tiles')
    out = bytearray()
    for ty in range(0, height, th):
        for tx in range(0, width, tw):
            for y in range(ty, ty + th):
                for x in range(tx, tx + tw, 2):
                    left, right = rows[y][x][0], rows[y][x + 1][0]
                    if left > 15 or right > 15:
                        fail(f'{path}: pixel near {x},{y} uses an index above 15')
                    out.append(left << 4 | right)
    return out


def palette(path):
    width, _, color, rows, plte, trns = read_png(path)
    if width != 16:
        fail(f'{path}: a palette image must be 16 pixels wide')
    out = bytearray()
    for row in rows:
        for px in row:
            if color == 3:
                r, g, b = plte[px[0]]
                a = trns[px[0]] if px[0] < len(trns) else 255
            elif color == 2:
                (r, g, b), a = px, 255
            elif color == 6:
                r, g, b, a = px
            else:
                fail(f'{path}: a palette must be RGB, RGBA or indexed')
            value = (b >> 3) << 11 | (g >> 3) << 6 | (r >> 3)
            if a >= 128:
                value |= 1 << 5
            out += struct.pack('<H', value)
    return out


def tile_size(text):
    try:
        w, h = (int(n) for n in text.lower().split('x'))
    except ValueError:
        raise argparse.ArgumentTypeError(f'not WxH: {text}')
    return w, h


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('mode', choices=['image', 'palette'])
    parser.add_argument('--tile', type=tile_size, help='tile size, WxH')
    parser.add_argument('--slot', type=int, help='bytes for each image, padded with 0')
    parser.add_argument('input', nargs='+')
    parser.add_argument('output')
    args = parser.parse_args()
    if args.mode == 'palette':
        if len(args.input) != 1:
            parser.error('palette takes one input')
        data = palette(args.input[0])
    else:
        data = bytearray()
        for path in args.input:
            one = image(path, args.tile)
            if args.slot:
                if len(one) > args.slot:
                    fail(f'{path}: {len(one)} bytes, more than the slot of {args.slot}')
                one += bytes(args.slot - len(one))
            data += one
    with open(args.output, 'wb') as f:
        f.write(data)


if __name__ == '__main__':
    main()
