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
import tempfile

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art'))
from png2bin import read_png  # noqa: E402

TEXT_SEARCH = 8192  # XRAM bytes searched for text
SPRITE = 10         # sizeof(mode5_csprite_t)
TEXT_COLS = 40
# game_state, from src/main.c
STATE_PLAY, STATE_MENU, STATE_SHOP, STATE_TITLE, STATE_CONFIRM, STATE_PAUSE = 1, 2, 3, 4, 5, 6
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
    """The game in the emulator, with its saves in save_dir, a new empty
    folder unless one is given, so a test never touches the real saves."""

    def __init__(self, rom, seed=1, save_dir=None):
        self.rom = rom
        self.sym = symbols(rom)
        self.save_dir = save_dir or tempfile.mkdtemp()
        self.proc = subprocess.Popen(
            [os.path.join(TOOLS, 'rp6502-emu'), rom, '--script', '-',
             '--seed', str(seed), '--mute', '--save-dir', self.save_dir],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.send('reply')

    def new_game(self):
        """From the title screen with no save, where New Game is picked,
        start a new game."""
        self.until('game_state', STATE_TITLE, 120)
        self.run(2)
        self.tap('space')
        self.until('game_state', STATE_PLAY)

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

    def sizes(self, addr, count):
        """The width_height byte of each of count sprites in a list from addr."""
        data = self.xram(addr, count * SPRITE)
        return [data[i + 8] for i in range(0, len(data), SPRITE)]

    def shown(self, addr, count):
        """How many of count sprites in a list from addr are on the screen."""
        return sum(y != HIDDEN_Y for _, y, _ in self.sprites(addr, count))

    def text_at(self, label, col, row):
        """The XRAM address of the text cells, from where label is drawn."""
        data = self.xram(0, TEXT_SEARCH)
        glyphs = label.encode()
        for i in range(0, len(data) - 2 * len(glyphs), 2):
            if data[i:i + 2 * len(glyphs):2] == glyphs:
                return i - (row * TEXT_COLS + col) * 2
        fail(f'{label!r} is not on the screen')

    def text(self, base, col, row, count):
        """count characters of text from col, row."""
        data = self.xram(base + (row * TEXT_COLS + col) * 2, count * 2)
        return data[::2].decode('ascii', 'replace').replace('\0', ' ')

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

    def tap(self, key, frames=4):
        """Press a key, or a gamepad control such as 'pad 0 up', and let go."""
        if key.startswith('pad '):
            pad, button = key.split()[1:]
            self.send(f'pad {pad} press {button}')
            self.run(frames)
            self.send(f'pad {pad} release {button}')
        else:
            self.send(f'press {key}')
            self.run(frames)
            self.send(f'release {key}')
        self.run(frames)

    def until(self, name, value, frames=120):
        """Run until a byte of the game's RAM reads value."""
        self.send(f'wait ram:{self.sym[name]} {value} {frames}')

    def menu_choose(self, item, wait=True, picked='UPGRADES'):
        """Choose PLAY or UPGRADES on the end-of-stage menu. After a stage it
        opens with UPGRADES picked and waits a second before it takes a
        choice. Back from the upgrade screen opens it with PLAY picked. Works
        with a Release ROM too, which logs nothing."""
        if wait:
            self.run(70)
        if item != picked:
            self.tap('down')
        self.tap('space')
        self.until('game_state', STATE_PLAY if item == 'PLAY' else STATE_SHOP)

    def close(self):
        self.proc.stdin.close()
        self.proc.stdout.read()
        self.proc.wait()
