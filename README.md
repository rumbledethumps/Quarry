# Quarry

An incremental brick breaker for the Picocomputer 6502. Play a stage,
collect nuggets from the bricks you break, spend them in an upgrade tree,
and play again.

<!-- rp6502
preset: llvm-mos/Release
publish: quarry.zip
-->
[![Quarry](https://rumbledethumps.github.io/Quarry/quarry/screenshot.png)](https://rumbledethumps.github.io/Quarry/quarry/)

[Play it in your browser](https://rumbledethumps.github.io/Quarry/quarry/).

## Controls

| Action | Keyboard | Gamepad |
| --- | --- | --- |
| Move | A and D, Left and Right, keypad 4 and 6 | D-pad or left stick |
| Launch | the button, keypad 0 | the button |
| Pick in a menu | W and S, Up and Down, keypad 8 and 2 | D-pad or left stick |
| Choose | the button | the button |
| Menu | Esc, P, Pause | Start or Select |

The game plays with one stick and one button, and so with one hand: the
arrows and Ctrl, or WASD and Space. The button is Space, Enter, keypad
Enter or Ctrl on the keyboard, and A, B, X or Y on a gamepad. Up never
launches. Menus don't wrap around, and a menu that goes up and
down ignores left and right.

Shift and the arrow keys are for testing, and holding them repeats. On
the title screen, Shift and Left or Right switch the curtains. A Debug
build has cheats too: in play, Shift and Right adds a ball, Shift and Left
takes one away, and Shift and Up or Down adds or takes away a segment of
energy. On the upgrade screen, Shift and Right or Left raises or lowers the
upgrade picked, for nothing, or, on the stages, opens the next stage or
locks the last one again.

The paddle floats on thrusters. The energy bar drains from the first
launch, and when it is empty the paddle falls and the stage ends. Each
brick you break turns into a nugget that flies to the counts at the top
left. The first clear of a stage earns a coin, and opens the next stage.
When a stage ends, go to the upgrade screen, replay the stage, or go to
the main menu. Esc in a stage pauses it, with Restart too.

The upgrade screen is coming together. Panels hang from a rail, one for
each upgrade, and slide left and right; the one in the middle flickers on,
and the button buys it. Left, right and the button repeat while held. The panels have their final frames and a stand-in
font; the background and the pictures are still stand-ins. Down goes to the row of stages, where the button
begins the stage picked. A stage newly open is still locked the first time
the screen shows it: the lock shakes, breaks, and its button lights. Stages 2 to 10 are stand-ins: stage 1 a column
wider each time.

The game saves when a stage starts or ends, when it pauses, and when an
upgrade is bought, in `SAVE:quarry.save`. Resume on the title screen opens
the upgrade screen from there. New Game starts over at stage 1, and
replaces the save.

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
- `upgrades` works the menu when a stage ends and the upgrade screen, and earns a coin.
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
