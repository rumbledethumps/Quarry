# Quarry

An incremental brick breaker for the Picocomputer 6502. Play a level,
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
upgrade picked, for nothing, or, on the levels, opens the next level or
locks the last one again. On any screen, Shift and a number brings in that
talk of the dwarves, in the order of `TALKS` in `art/talk.py`, to see how
it looks there, without counting it as seen.

The playfield is framed in gray steel the ball bounces off, riveted
girders or an open truss, a frame set picked at random for each new level,
as its rock walls are. The paddle floats on thrusters. The energy bar
drains from the first launch, and when it is empty the paddle falls and
the level ends. When the last brick breaks, or the last ball is lost, the
paddle flies home, down off the screen under its own power: only out of
fuel does it fall.

The bricks are plain colors, gray, red, green, blue and gold, which stay
apart with any kind of color blindness. Gray breaks in one hit, red in
two, and the rest in more, by `TUNE_BRICK_HITS` in `src/tuning.h`. A brick
cracks more with each hit, its cracks a sprite over it, flipped and
placed at random for each brick when the level's screen opens. A brick
that breaks flies apart in chunks, and its nugget, a small ball of its
color, flies to the counts at the top left. A color's line of the counts
shows once its first nugget lands there, and the coins' once the first
level is cleared. The first clear of a level earns a coin, and opens the
next level.
When a level ends, its menu says how, LEVEL COMPLETE, OUT OF BALLS or
OUT OF FUEL, and goes to the upgrade screen, replays the level, or goes to
the main menu. Esc in a level pauses it, with Restart too. The menus are
framed in marching caution tape, and the upgrade screen's holographic
cursor picks in them.

The upgrade screen is coming together. Panels hang from a rail, one for
each upgrade, and slide left and right; the one in the middle lights up,
and the button buys it. Left, right and the button repeat while held. The
panels have their final frames and font, and hang in front of a
workshop whose cogs turn and whose vent puffs steam, their trolleys riding
the rail; their pictures are still stand-ins. Down goes to a train of mine
carts on a track, a cart for each level, where the button begins the level
picked. A level newly open is still locked the first time the screen shows
it: the screen opens on the level just cleared, the padlock on the next
cart shakes and breaks, and the train slides over to the new level, picked.
Each level places its own walls and bricks, so a playfield can be any
width, and its walls any distance from its bricks, each side on its own.
Level 1 is 4 by 4 gray bricks, 2 px apart, with half a brick of room for
the ball at each wall, and level 2 the same with red ones in the middle of
its top two rows. Levels 3 to 10 are level 2 again until they are
designed.

A new game starts with a cartoon dwarf miner coming up in the lower left
corner, his speech bubble coming in beside him with a welcome, a stand-in
for now. The button on its OK sends them away. He comes back with the coin
for each first clear, and on the upgrade screen to explain the first
unlock and, the first time there, what the screen is for. More dwarves,
and more for them to say, are coming.

The game saves when a level starts or ends, when it pauses, and when an
upgrade is bought, in `SAVE:quarry.save`, with what the dwarves have
already said and the lines of the counts reached. Resume on the title screen, there once there is a save,
opens the upgrade screen from there, on its level select; from a level, it
opens on the upgrades. New Game starts over at level 1, and replaces the
save, once Yes answers whether to; Esc is No.

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
- `levels/levels.py` lays out the levels: each is a short function, with
  what it is for said first, that places its walls and its bricks on the
  screen, to the pixel. The build checks them, writes them for the game,
  and draws each in `levels/` in the build folder, to look at.
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
- `nuggets` breaks bricks into chunks and follows their nuggets to the panel.
- `upgrades` works the menu when a level ends and the upgrade screen, earns a
  coin, and cracks and breaks a red brick of level 2.
- `saves` works the title screen and the pause menu, and reads the save.
- `sound` sets off every sound effect and reads the PSG's channels.
- `talk` brings in the dwarves: the welcome, the coin, and the upgrade
  screen's two, and checks the cursor and the screen under them.
- `autoplay` plays level 1 until it ends, and `autoplay-miss` loses every
  ball.
- `assets` checks that each asset the art scripts write is the size of
  what the game loads it into, and that the art scripts draw in the rows
  of `art/palettes.png` the game has them in. It reads the files and
  `quarry.sym`, and doesn't run the emulator.

The tests other than autoplay and assets wait for the events that a Debug
ROM logs, so a Release build has only those:

```bash
ctest --test-dir build/llvm-mos/release
```

The tests read the game's variables, XRAM addresses, and tuning numbers by
name from `quarry.sym`, the symbol table that the build writes beside the
ROM, so they hold no addresses and no copies of the game's numbers. Each
test keeps its saves in a folder of its own, such as
`build/llvm-mos/debug/test/saves/save/`.
