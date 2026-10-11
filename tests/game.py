"""Runs Quarry in the emulator for a test, and reads the game's state.

The game's variables are found by name in the ELF next to the ROM, with the
llvm-nm that the build's CMake cache names, so a test needs no addresses.
Text on the screen is found in XRAM, where the text cells are glyph and
color bytes, and so are sprites, by where they are.

The script's frames do not line up with the game's steps, so a read of the
game's RAM can land in the middle of a step, after it moves the ball across
and before it moves it down. The sprites are written all at once at the
start of each step, so a test that follows something moving reads its
sprite instead.
"""

import struct

import os
import subprocess
import sys

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art'))
from png2bin import read_png  # noqa: E402

TEXT_SEARCH = 8192  # XRAM bytes searched for text
SPRITE = 10         # sizeof(mode5_csprite_t)
HIDDEN_Y = -64      # SPRITE_HIDDEN_Y


def fail(message):
    sys.exit(f'FAIL: {message}')


def check(ok, message):
    if not ok:
        fail(message)


def symbols(rom):
    """The address of every symbol in the ELF built with the ROM."""
    build = os.path.dirname(os.path.abspath(rom))
    nm = None
    with open(os.path.join(build, 'CMakeCache.txt')) as f:
        for line in f:
            if line.startswith('CMAKE_NM:'):
                nm = line.split('=', 1)[1].strip()
    if not nm:
        fail(f'no CMAKE_NM in {build}/CMakeCache.txt')
    elf = os.path.splitext(rom)[0] + '.elf'
    out = subprocess.run([nm, elf], capture_output=True, text=True, check=True).stdout
    table = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            table[parts[2]] = int(parts[0], 16)
    return table


class Game:
    def __init__(self, rom, seed=1):
        self.rom = rom
        self.sym = symbols(rom)
        self.proc = subprocess.Popen(
            [os.path.join(TOOLS, 'rp6502-emu'), rom, '--script', '-',
             '--seed', str(seed), '--mute'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.send('reply')

    def send(self, line):
        """One script command. A failed one ends the test."""
        self.proc.stdin.write(line + '\n')
        reply = self.proc.stdout.readline().strip()
        if not reply.startswith('ok'):
            rest = self.proc.stdout.read()
            fail(f'{line!r} -> {reply}\n{rest}')
        return reply[2:].split()

    def run(self, frames=1):
        self.send(f'run {frames}')

    def wait(self, text, frames):
        self.send(f'wait "{text}" {frames}')

    def ram(self, name, size=1, signed=False):
        data = [int(b, 16) for b in self.send(f'dump ram:{self.sym[name]} {size}')]
        value = sum(b << (8 * i) for i, b in enumerate(data))
        if signed and value >> (8 * size - 1):
            value -= 1 << (8 * size)
        return value

    def poke(self, name, value, size=1):
        data = ' '.join(str((value >> (8 * i)) & 0xFF) for i in range(size))
        self.send(f'poke ram:{self.sym[name]} {data}')

    def px(self, name):
        """A position in 1/256 px, as whole pixels."""
        return self.ram(name, 4, signed=True) >> 8

    def xram(self, addr, size):
        return bytes(int(b, 16) for b in self.send(f'dump xram:{addr} {size}'))

    def sprite_at(self, x, y):
        """The XRAM address of the one sprite at x, y."""
        data = self.xram(0, TEXT_SEARCH)
        pos = struct.pack('<hh', x, y)
        found = [i for i in range(0, len(data) - 4, 2) if data[i:i + 4] == pos]
        check(len(found) == 1, f'one sprite at {x},{y}, found {len(found)}')
        return found[0]

    def sprite(self, addr):
        """The x, y of the sprite at addr."""
        return struct.unpack('<hh', self.xram(addr, 4))

    def sprites(self, addr, count):
        """The x, y, image of each of count sprites in a list from addr."""
        data = self.xram(addr, count * SPRITE)
        return [struct.unpack('<hhH', data[i:i + 6]) for i in range(0, len(data), SPRITE)]

    def shown(self, addr, count):
        """How many of count sprites in a list from addr are on the screen."""
        return sum(y != HIDDEN_Y for _, y, _ in self.sprites(addr, count))

    def shows(self, text):
        """Whether the text is anywhere on the text plane."""
        data = bytes(int(b, 16) for b in self.send(f'dump xram:0 {TEXT_SEARCH}'))
        glyphs = text.encode()
        for start in (0, 1):
            if glyphs in data[start::2]:
                return True
        return False

    def screen(self, path):
        """The screen, as rows of RGB tuples."""
        self.send(f'shot "{os.path.abspath(path)}"')
        _, _, _, rows, _, _ = read_png(path)
        return rows

    def close(self):
        self.proc.stdin.close()
        self.proc.stdout.read()
        self.proc.wait()
