# Game Plan — Quarry

An incremental brick breaker for the Picocomputer 6502. Play a stage, collect
nuggets from the bricks you break, spend them in an upgrade tree, and play
again.

The goal is a playable prototype, fast, so playtesters can tell us what's
fun. Their feedback drives the design and the tuning. Build only what the
current milestone needs, and don't build ahead.

The user playtests at every milestone. Each milestone below ends with a
**STOP**: hand over the build and wait for the go-ahead before starting the
next one.

**Read the whole manual first.** Before doing anything else in a session,
read the entire manual in `~/picocomputer.github.io/docs/source`, every page,
top to bottom. No cache, no summary, no subagents. Do nothing until it is
all read. Once per session is enough.

**Stay in your lane.** This is a development machine full of unrelated
projects, and reading them causes confusion. Read only the manual, this
plan, the game's own project, and anything else the user names. Read nothing
else: no example games, no other projects, no other files in this folder. If
something else looks useful, ask first.


## The Game

- There is no score. The currency is nuggets, counted by color.
- The paddle floats on thrusters, and the thrust burns energy. When the
  energy runs out, the paddle gives up a puff of smoke and falls off the
  screen, and the stage is over.
- A stage also ends when the last ball is lost, or when every brick is
  broken.
- After a stage ends, the player chooses **Upgrades** or **Play**. Play
  starts the next stage if this one was cleared, and the same stage again if
  not.
- Clearing a stage unlocks the next one.
- The upgrade tree is where nuggets are spent.
- Anything that falls off the bottom of the screen is gone.


## Screen (320x240)

- **Left panel:** the nugget counts. One line per brick color: a nugget icon
  and the count beside it. A color's line appears only once the player has
  reached a stage with that color, so stage 1 shows only white.
- **Middle:** the playfield. It starts narrow, 5 or 6 bricks across in
  stage 1, and gets wider in later stages.
- **Right panel:** the energy bar on top. Under it, the balls remaining, drawn
  as ball icons in rows as wide as the bar. More balls wrap to more rows,
  since there could be 30 or more later.
- No ground. The bottom of the screen is open.


## Bricks

- Bricks are sprites, not tiles, so they can move freely later, such as the
  whole wall creeping down one pixel at a time.
- Bricks start at 24x8. Sizes may vary later.
- Four stages to start, with fixed layouts:
  - Stage 1: white only, 5 or 6 across.
  - Stage 2: wider, with some yellow.
  - Stage 3: wider, adds a third color.
  - Stage 4: white is dropped, or at least rarer.
- Every brick breaks in one hit for now. Multi-hit bricks with cracks come
  later.
- When a brick breaks, its sprite is hidden and a nugget appears in its
  place. The nugget flies in a straight line, stepped Bresenham-style, to its
  color's line in the left panel. When it lands, that count goes up by one.
- The counts are global and persistent. They never reset, and only go down
  when spent in the upgrade tree.


## Paddle and Balls

- The paddle moves left and right at a fixed hover height.
- Thruster flames show under the paddle. Other effects, such as anti-gravity
  pulses, may come later as upgrades.
- The launch button launches a ball. One ball in play for now. More balls in
  play, or launching several at once, may come later as upgrades.
- Bounce off the paddle, as in Arkanoid: the paddle is split into zones. The
  center sends the ball up steeply, the zones beside it at 45 degrees, and
  the outer edges at a shallow angle. The left half sends it left and the
  right half sends it right.
- Ball speed is fixed for now. Later, if wanted: Breakout speeds the ball up
  after 4 hits, after 12 hits, and on reaching the back rows. Arkanoid
  changes the ball's angle after 40 bounces.


## Energy

- Energy drains over time.
- It starts full each stage.
- Anything more, such as refills, comes from the upgrade tree.


## Stage 1 Tuning Targets

These are rough starting estimates. Get them in the ballpark and move on.
Playtest feedback does the real tuning.

- 5 balls to start.
- The paddle starts narrow and a little slow. The ball is a little too fast
  for it.
- Most players lose all their balls before clearing stage 1. Clearing it is
  rare.
- Energy lasts long enough that losing balls, not energy, ends this first
  stage.
- After that, the player can afford a normal-width paddle and a bit more
  speed in the upgrade tree, and then clears stage 1.
- Every number lives in one tuning header, so a playtest change is a
  one-line edit.


## Upgrades

- The first upgrades: **paddle width** and **paddle speed**. Both cost white
  nuggets.
- The starting costs are placeholders. A typical first stage must earn
  enough for both.
- Later upgrades unlock from earlier ones and cost later colors. Which ones:
  to be decided.
- The look of the upgrade screen comes from the concept art.


## Controls

Keyboard, read from the key bitmap so held keys work:

- Left: A, Left arrow, keypad 4.
- Right: D, Right arrow, keypad 6.
- Launch: Space, Enter, keypad 0, keypad Enter, and every up key: W, Up
  arrow, keypad 8.
- Menus: W/S, Up/Down arrows, keypad 8/2 to move; Space or Enter to choose.
- Esc: pause.

Gamepad, from any connected gamepad:

- D-pad or left stick to move.
- A, B, X or Y to launch and choose. Up on the D-pad or stick launches too.
- Start: pause.

No mouse for now. It can be added later.


## Title, Pause and Saving

- **Title screen:** Resume, New Game, Exit.
  - Resume is grayed out until a save exists.
  - New Game starts over and replaces the save. When a save exists, it asks
    yes/no first. That is the way to clear the save.
  - Exit calls exit().
- **Pause menu**, from Esc or Start: Continue or Exit. Exit goes back to the
  title screen.
- The game saves when:
  - the pause menu opens,
  - a stage starts,
  - a stage ends.
- One save, one file: `SAVE:quarry.save`. It holds the nugget counts per
  color, the upgrade levels and the stages unlocked.
- The web player sets `db: 'rumbledethumps-quarry'` so saves last between
  visits.


## How It's Built

- A new project from the SDK template, in C with llvm-mos.
- Canvas 320x240.
- The whole game uses 16-color palettes, 4-bit color.
- Starting planes, back to front. They can move later.
  - **Plane 0:** background tiles in the fill layer; bricks in the sprite
    layer.
  - **Plane 1:** paddle, flames, smoke and ball in the sprite layer.
  - **Plane 2:** panel and menu text in the fill layer (mode 1 character
    mode); nugget icons, flying nuggets, ball icons and the energy bar in the
    sprite layer, so they draw over the panel text.
- The background is tiles (mode 2). A bitmap costs too much memory. The
  walls are part of the background, and its map changes with the playfield
  width of each stage.
- All sprites are mode 5 custom sprites. Each sprite has its own size, 4 to
  64 pixels in steps of 4, so bricks, the ball and the paddle pieces share
  one list.
- Every sprite has its own palette pointer, so one brick image serves every
  color, with a white palette, a yellow palette and so on. Nuggets work the
  same way.
- One game step per VSYNC, 60 a second.
- Positions and speeds have sub-pixel precision.
- The ball is checked against every brick each step.
- XRAM layout in one `xram.h`: keyboard, gamepads, PSG, mode configs, sprite
  lists, palettes (one struct, under 512 colors), images, tiles and text
  cells.
- Art PNGs are converted by a small Python script run from CMake, and loaded
  into XRAM with `rp6502_asset()`.
- Sound effects on the PSG.
- Web player from `rp6502_web()`.


## Milestones

Placeholder art (plain colored shapes) until the art arrives. Art is swapped
in whenever it's ready.

1. **Bounce.** Project set up. The paddle moves with every key and the
   gamepad. The launch button launches the ball, and it bounces off walls,
   paddle zones and bricks. Stage 1 bricks break. A ball that falls off the
   bottom is gone. 5 balls, shown as icons in the right panel. The stage
   ends at 0 balls or when every brick is broken.
   **STOP** — playtest paddle and ball feel. Check keypad 4/6 with Num Lock
   both on and off.
2. **Energy.** The energy bar drains over time and the flames burn. When it
   is empty, the paddle puffs smoke, falls off the screen and the stage
   ends.
   **STOP** — playtest.
3. **Nuggets.** Broken bricks turn into nuggets that fly to the left panel,
   and each one that lands adds one to its color's count.
   **STOP** — playtest.
4. **Upgrades.** End-of-stage menu (Upgrades / Play). Upgrade screen with
   paddle width and speed, paid in white nuggets. Tuning header. Stage 1
   roughly at the targets above.
   **STOP** — the main playtest.
5. **Title, pause and saves.** Title screen, pause menu, every save point,
   and the web player's `db`.
   **STOP** — playtest, including Exit and coming back.
6. **Sound.** PSG effects: paddle, wall and brick hits, brick break, nugget
   landing, lost ball, low energy, paddle falling, purchase, menu moves.
   **STOP** — playtest.
7. **Stages 2–4.** Fixed layouts, wider playfields, yellow and a third
   color. Each color's line appears in the left panel when its stage is
   reached.
   **STOP** — playtest.
8. **Later, driven by playtests.** Multi-hit bricks with cracks, more balls
   in play, more upgrades, moving bricks, random layouts, mouse, effects
   under the paddle.


## Testing

- Claude builds after every change and runs the emulator with `--script`
  and `--seed` to drive the keys and gamepad and check the one thing that
  changed.
- The user playtests at every STOP.


## Concept Art Wanted

The concept art sets the look. The final sprites are drawn from it in 16
colors at the sizes given, so each item notes its size on the 320x240
screen.

1. **Title screen:** the Quarry logo, with Resume, New Game and Exit.
2. **Play screen, 320x240:** nugget counts on the left, the narrow stage 1
   playfield in the middle, the energy bar and rows of ball icons on the
   right. The paddle with thruster flames, bricks, a ball, and a nugget in
   flight.
3. **Bricks, 24x8:** white, yellow and a third color, all the same shape so
   one image works with each color's palette.
4. **Nugget, 8x8:** per color, same shape for every color. It is also the
   icon in the left panel.
5. **Brick to nugget:** a few frames of a brick breaking down into a nugget.
6. **Paddle, 8 tall:** left end, a middle piece that repeats, right end.
   Narrow and normal width.
7. **Thruster flame:** a few frames, under the paddle.
8. **Out of energy:** a puff of smoke as the paddle gives up and falls.
9. **Ball, 8x8 or smaller.** It is also the ball icon in the right panel.
10. **Background tiles and walls** around the playfield.
11. **Energy bar.**
12. **Upgrade tree screen.**
13. **End-of-stage menu** (Upgrades / Play) and **pause menu** (Continue /
    Exit).
