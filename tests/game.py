"""Runs Quarry in the emulator for a test, and reads the game's state.

Each test is an rp6502_test() in CMakeLists.txt. ctest runs it with the
emulator options and the ROM as its arguments, and the emulator in
RP6502_EMU. A test also runs by itself, from the project folder:

  python3 tests/controls.py build/llvm-mos/debug/quarry/quarry.rp6502

Then the emulator is the one beside the ROM, and the saves go in a new
empty folder, so a test never touches the real saves.

The game's numbers come from the .sym file that the build writes beside
the ROM, as game.sym: each #define with a whole-number value, such as
TUNE_ENERGY or XRAM_PSG, and each variable, such as paddle_x. Script
commands take the same names, and expressions of them, wherever they take
a number, as in "wait game_state STATE_PLAY", so a test holds no addresses
and no copies of the game's numbers. Text on the
screen is read from the menus' map at XRAM_MENU_MAP, a tile a byte, each
tile from MENU_TILE_GLYPH a letter of the panels' font. The title's panels
are known by their map, which is one of art/title_panels.py's, but for the
progress, from TITLE_TILE_GLYPH a letter of its font. The sprites are read
from their lists in XRAM.

The script's frames do not line up with the game's steps, so a read of the
game's RAM can land in the middle of a step, after it moves the ball across
and before it moves it down. The sprites are written all at once at the
start of each step, so a test that follows something moving reads its
sprite instead.
"""

import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, os.path.join(HERE, '..', 'art'))
import rp6502  # noqa: E402
from panels import FONT  # noqa: E402
import title_panels  # noqa: E402
from png2bin import read_png  # noqa: E402


def fail(message):
    sys.exit(f'FAIL: {message}')


def check(ok, message):
    if not ok:
        fail(message)


def option(name):
    """The value of the emulator option --name in the test's arguments, or
    None."""
    args = sys.argv[1:]
    for i, word in enumerate(args):
        if word == '--':
            break
        if word == f'--{name}' and i + 1 < len(args):
            return args[i + 1]
        if word.startswith(f'--{name}='):
            return word.split('=', 1)[1]
    return None


def rom():
    """The path of the ROM in the test's arguments."""
    for word in sys.argv[1:]:
        if word == '--':
            break
        if word.endswith('.rp6502'):
            return os.path.abspath(word)
    fail('no ROM in the arguments of the test')


_save_dir = []


def save_dir():
    """The folder behind SAVE:, the test's --save-dir, or else one new empty
    folder for every Game of the test."""
    if not _save_dir:
        _save_dir.append(option('save-dir') or tempfile.mkdtemp())
    return _save_dir[0]


class Game(rp6502.Emu):
    """The game in the emulator, muted, with the ROM and the options of the
    test's arguments, and its saves in save_dir()."""

    def __init__(self, *args):
        emu = 'rp6502-emu.exe' if os.name == 'nt' else 'rp6502-emu'
        os.environ.setdefault('RP6502_EMU', os.path.join(os.path.dirname(rom()), emu))
        if option('save-dir') is None:
            args += ('--save-dir', save_dir())
        super().__init__('--mute', *args)
        self.booted = False

    def boot(self):
        """Runs until the title screen is up. Before the game starts, RAM
        holds whatever the emulator filled it with, which can read as the
        title screen, so the game is given time to start first."""
        self.run(10)
        self.until('game_state', 'STATE_TITLE', 120)
        self.run(2)
        self.booted = True

    def new_game(self):
        """From the title screen with no save, where Start Game is all
        there is, start a new game, get past the dwarf's welcome, and wait
        for the level to build up."""
        if not self.booted:
            self.boot()
        self.tap('space')
        self.until('game_state', 'STATE_PLAY')
        self.talk_ok()
        self.ready()

    def ready(self):
        """Wait for the level to build up, until its ball has landed on the
        sled, ready to launch."""
        self.until('building', 0, 60 + 2 * self.sym['TUNE_BUILD_STEPS'])

    def talk_ok(self):
        """Get past the dwarves: wait for each one's OK, press the button, and
        wait until he has gone, and the next comes in, or the last has gone
        and the screen under him has taken over again."""
        off, coming = self.sym['TALK_OFF'], self.sym['TALK_IN']
        self.run(2)
        while self.ram('talk_state') != off:
            self.until('talk_state', 'TALK_READY', 120)
            self.tap('space')
            for _ in range(60):
                if self.ram('talk_state') in (off, coming):
                    break
                self.run(1)
        self.run(2)

    def run(self, frames=1):
        self.cmd(f'run {frames}')

    def wait(self, text, frames):
        """Run until the game logs the text."""
        self.cmd(f'wait "{text}" {frames}')

    def ram(self, name, size=1, signed=False):
        data = bytes.fromhex(self.cmd(f'dump {name} {size}'))
        return int.from_bytes(data, 'little', signed=signed)

    def poke(self, name, value, size=1):
        data = (value & ((1 << 8 * size) - 1)).to_bytes(size, 'little')
        self.cmd(f'poke {name} {" ".join(str(b) for b in data)}')

    def paused_poke(self, pokes):
        """Pokes (name, value, size) into the game's RAM while play is paused,
        so no step is under way to overwrite them. Pausing saves the game."""
        self.tap('escape')
        self.until('game_state', 'STATE_PAUSE', 10)
        for name, value, size in pokes:
            self.poke(name, value, size)
        self.tap('escape')
        check(self.ram('game_state') != self.sym['STATE_PAUSE'], 'play carries on after the poke')

    def px(self, name):
        """A position in 1/256 px, as whole pixels."""
        return self.ram(name, 4, signed=True) >> 8

    def xram(self, addr, size):
        return bytes.fromhex(self.cmd(f'dump xram:{addr} {size}'))

    def sprite(self, addr):
        """The x, y of the sprite at addr."""
        return struct.unpack('<hh', self.xram(addr, 4))

    def sprites(self, addr, count):
        """The x, y, image of each of count sprites in a list from addr."""
        step = self.sym['SPRITE_BYTES']
        data = self.xram(addr, count * step)
        return [struct.unpack('<hhH', data[i:i + 6]) for i in range(0, len(data), step)]

    def sizes(self, addr, count):
        """The width_height byte of each of count sprites in a list from addr."""
        step = self.sym['SPRITE_BYTES']
        data = self.xram(addr, count * step)
        return [data[i + 8] for i in range(0, len(data), step)]

    def shown(self, addr, count):
        """How many of count sprites in a list from addr are on the screen."""
        hidden = self.sym['SPRITE_HIDDEN_Y']
        return sum(y != hidden for _, y, _ in self.sprites(addr, count))

    def count(self, first, sprites):
        """The number that the digit sprites of a count from first show."""
        base, size = self.sym['XRAM_DIGIT_IMAGES'], self.sym['DIGIT_IMAGE_BYTES']
        hidden = self.sym['SPRITE_HIDDEN_Y']
        digits = ''.join(str((image - base) // size)
                         for _, y, image in self.sprites(first, sprites) if y != hidden)
        return int(digits) if digits else None

    def letters(self, tiles):
        """The menus' tiles as text: a letter for each glyph, and a space
        for anything else."""
        first = self.sym['MENU_TILE_GLYPH']
        return ''.join(FONT[t - first] if 0 <= t - first < len(FONT) else ' ' for t in tiles)

    def shows(self, text):
        """Whether the text is anywhere in the menus."""
        cols = self.sym['TEXT_COLS']
        data = self.xram('XRAM_MENU_MAP', cols * self.sym['TEXT_ROWS'])
        return any(text in self.letters(data[r:r + cols]) for r in range(0, len(data), cols))

    def title_panels(self):
        """The title's panels as they show: 'SAVE' or 'START', the map of
        art/title_panels.py they are, but for the progress, or None, off the
        screen."""
        cols, rows, row = self.sym['TITLE_COLS'], self.sym['TITLE_ROWS'], self.sym['TITLE_PROGRESS_ROW']
        x = struct.unpack('<h', self.xram('XRAM_PANEL_CONFIG+2', 2))[0]
        if x >= self.sym['SCREEN_W']:
            return None
        size = cols * rows
        shown = self.xram('XRAM_TITLE_MAP', size)
        asset = open(os.path.join(os.path.dirname(os.path.dirname(rom())), 'title_panels.bin'), 'rb').read()
        but = lambda m: m[:row * cols] + m[(row + 1) * cols:]
        for name in title_panels.MAPS:
            at = self.sym['TITLE_ART_BYTES'] + self.sym[f'TITLE_MAP_{name}'] * size
            if but(asset[at:at + size]) == but(shown):
                return name
        fail('the title shows panels of none of its maps')

    def progress(self):
        """The progress on the title's panels, as text."""
        cols, row, first = self.sym['TITLE_COLS'], self.sym['TITLE_PROGRESS_ROW'], self.sym['TITLE_TILE_GLYPH']
        font = title_panels.FONT
        line = self.xram(f'XRAM_TITLE_MAP+{row * cols}', cols)
        return ''.join(font[t - first] if 0 <= t - first < len(font) else '#' for t in line).strip('#').strip()

    def screen(self, path):
        """The screen, as rows of RGB tuples."""
        self.cmd(f'shot "{os.path.abspath(path)}"')
        _, _, _, rows, _, _ = read_png(path)
        return rows

    def tap(self, key, frames=4):
        """Press a key, or a gamepad control such as 'pad 0 up', and let go."""
        if key.startswith('pad '):
            pad, button = key.split()[1:]
            self.cmd(f'pad {pad} press {button}')
            self.run(frames)
            self.cmd(f'pad {pad} release {button}')
        else:
            self.cmd(f'press {key}')
            self.run(frames)
            self.cmd(f'release {key}')
        self.run(frames)

    def until(self, name, value, frames=120):
        """Run until a byte of the game's RAM reads value, a number or a
        name such as 'STATE_PLAY'."""
        self.cmd(f'wait {name} {value} {frames}')

    def menu_choose(self, item, wait=True):
        """Choose THE DRY, REPLAY or MAIN MENU on the menu when a level ends.
        It opens with THE DRY picked and waits a second before it takes a
        choice. Works with a Release ROM too, which logs nothing."""
        items = ['THE DRY', 'REPLAY', 'MAIN MENU']
        states = ['STATE_SHOP', 'STATE_PLAY', 'STATE_TITLE']
        if wait:
            self.run(self.sym['LEVEL_OVER_WAIT'] + 10)
        for _ in range(items.index(item)):
            self.tap('down')
        self.tap('space')
        self.until('game_state', states[items.index(item)])
