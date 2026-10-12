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
| Launch | Space, Enter, keypad 0, keypad Enter, W, Up, keypad 8 | A, B, X or Y, or up |
| Pick in a menu | W and S, Up and Down, keypad 8 and 2 | D-pad or left stick |
| Choose | Space, Enter, keypad Enter | A, B, X or Y |
| Pause | Esc | Start |

The paddle floats on thrusters. The energy bar drains from the first
launch, and when it is empty the paddle falls and the stage ends. Each
brick you break turns into a nugget that flies to the count in the left
panel. When the stage ends, spend the nuggets on Upgrades, a wider or a
faster paddle, or Play again.

The game saves when a stage starts or ends and when it pauses, in
`SAVE:quarry.save`, and Resume on the title screen carries on from there.
New Game starts over, and replaces the save.

## Building

Quarry is C, built with llvm-mos. The
[RP6502-SDK](https://picocomputer.github.io/sdk.html#sdk-install) has the
install steps for the tools.

```bash
cmake --preset llvm-mos/Debug
cmake --build --preset llvm-mos/Debug
```

The ROM is `build/llvm-mos/debug/quarry.rp6502`. In VS Code, F5 builds it
and runs it in the emulator. Both presets optimize for size with `-Oz`,
because the game would not fit in the 6502's memory or keep up with 60
steps a second otherwise. Debug only adds the debug information.

- `src/tuning.h` holds every gameplay number.
- `src/xram.h` is the XRAM layout.
- `art/` holds the art as indexed PNGs. `art/png2bin.py` converts them
  for the VGA when the project builds.

## Tests

The tests play the game in the emulator from Python scripts. Run them from
the project folder after a Debug build:

```bash
python3 tests/controls.py build/llvm-mos/debug/quarry.rp6502
python3 tests/energy.py build/llvm-mos/debug/quarry.rp6502
python3 tests/nuggets.py build/llvm-mos/debug/quarry.rp6502
python3 tests/upgrades.py build/llvm-mos/debug/quarry.rp6502
python3 tests/saves.py build/llvm-mos/debug/quarry.rp6502
python3 tests/autoplay.py build/llvm-mos/debug/quarry.rp6502
python3 tests/autoplay.py build/llvm-mos/debug/quarry.rp6502 --miss 5
```

- `controls.py` works every key and gamepad control.
- `energy.py` drains the energy bar and runs out of energy.
- `nuggets.py` breaks bricks and follows their nuggets to the panel.
- `upgrades.py` works the end-of-stage menu and buys upgrades.
- `saves.py` works the title screen and the pause menu, and reads the save.
- `autoplay.py` plays stage 1 to the end, clearing it, or with `--miss 5`
  losing every ball. It also runs on a Release ROM.

The tests find the game's variables by name in the ELF beside the ROM, so
they need no addresses, and each keeps its saves in a folder of its own.
