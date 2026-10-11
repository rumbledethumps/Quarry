# Quarry

An incremental brick breaker for the Picocomputer 6502. Play a stage,
collect nuggets from the bricks you break, spend them in an upgrade tree,
and play again.

Quarry is an early prototype, built a milestone at a time from
[plan/GAMEPLAN.md](plan/GAMEPLAN.md). Its sprites and tiles are drawn
from the concept art in [plan/](plan/).

<!-- rp6502
preset: llvm-mos/Release
publish: quarry.zip
-->
[![Quarry](https://rumbledethumps.github.io/quarry/quarry/screenshot.png)](https://rumbledethumps.github.io/quarry/quarry/)

[Play it in your browser](https://rumbledethumps.github.io/quarry/quarry/).

## Controls

| Action | Keyboard | Gamepad |
| --- | --- | --- |
| Move | A and D, Left and Right, keypad 4 and 6 | D-pad or left stick |
| Launch | Space, Enter, keypad 0, keypad Enter | A, B, X or Y |

## Building

Quarry is C, built with llvm-mos. The
[RP6502-SDK](https://picocomputer.github.io/sdk.html#sdk-install) has the
install steps for the tools.

```bash
cmake --preset llvm-mos/Debug
cmake --build --preset llvm-mos/Debug
```

The ROM is `build/llvm-mos/debug/quarry.rp6502`. In VS Code, F5 builds it
and runs it in the emulator.

- `src/tuning.h` holds every gameplay number.
- `src/xram.h` is the XRAM layout.
- `art/` holds the art as indexed PNGs. `art/png2bin.py` converts them
  for the VGA when the project builds.

## Tests

The emulator plays the game from a script. Run these from the project
folder after a Debug build:

```bash
tools/rp6502-emu build/llvm-mos/debug/quarry.rp6502 --script tests/controls.txt --seed 1 --mute
python3 tests/autoplay.py build/llvm-mos/debug/quarry.rp6502
python3 tests/autoplay.py build/llvm-mos/debug/quarry.rp6502 --miss 5
```

`controls.txt` works every key and gamepad control. `autoplay.py` plays
stage 1 to the end, clearing it, or with `--miss 5` losing every ball.
