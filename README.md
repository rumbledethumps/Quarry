# Quarry

An incremental brick breaker for the Picocomputer 6502. Play a stage,
collect nuggets from the bricks you break, spend them in an upgrade tree,
and play again.

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

A Debug build has cheats for testing. Shift and Right adds a ball, Shift
and Left takes one away, and Shift and Up or Down adds or takes away a
segment of energy. Holding them repeats.

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

The ROM is `build/llvm-mos/debug/quarry/quarry.rp6502`. In VS Code, F5 builds it
and runs it in the emulator. Both presets optimize for size with `-Oz`,
because the game would not fit in the 6502's memory or keep up with 60
steps a second otherwise. Debug only adds the debug information.

- `src/tuning.h` holds every gameplay number.
- `src/sfx.c` holds the sound effects, as notes for the PSG.
- `src/xram.h` is the XRAM layout.
- `art/` holds the art as indexed PNGs. `art/png2bin.py` converts them
  for the VGA when the project builds.

## Tests

The tests play the game in the emulator from Python scripts in `tests/`.
`CMakeLists.txt` adds each one with `rp6502_test()`, and ctest builds the
project and then runs them, or the Testing view in VS Code does:

```bash
ctest --test-dir build/llvm-mos/debug
ctest --test-dir build/llvm-mos/debug -R energy --output-on-failure
```

- `controls` works every key and gamepad control.
- `energy` drains the energy bar and runs out of energy.
- `nuggets` breaks bricks and follows their nuggets to the panel.
- `upgrades` works the end-of-stage menu and buys upgrades.
- `saves` works the title screen and the pause menu, and reads the save.
- `sound` sets off every sound effect and reads the PSG's channels.
- `autoplay` plays stage 1 until it ends, and `autoplay-miss` loses every
  ball.

The tests other than the two autoplay ones wait for the events that a
Debug ROM logs, so a Release build has only the autoplay tests:

```bash
ctest --test-dir build/llvm-mos/release
```

The tests read the game's variables, XRAM addresses, and tuning numbers by
name from `quarry.sym`, the symbol table that the build writes beside the
ROM, so they hold no addresses and no copies of the game's numbers. Each
test keeps its saves in a folder of its own, such as
`build/llvm-mos/debug/test/saves/save/`.
