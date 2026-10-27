# Quarry Art Style

Quarry has two looks. The levels are **stone**: rough, organic quarry
walls, and bricks of rock with their ore showing through. The player's
equipment is **industrial**: heavy modern mining machinery, used every day
and well looked after. Every new piece of art belongs to one of the two.

The images in `ref/` set the look. Pass them as references when making new
art, and compare new art against them.

## The Screen

A stage's playfield is framed in steel: a post on each side and a cap beam
across the top, where the ball bounces. Outside the posts are the
curtains, the rock walls of the quarry. Stage 1 is the narrowest, 4 bricks
across with half a brick of space at each wall. The widest is about 10
bricks, with a little rock left on each side. Each stage is laid out
fresh, so the curtains never move while anyone watches.

The counts float over the curtains, with no panels behind them:

- **Upper left:** a count for each kind of nugget, with a sprite of the
  nugget beside it, a line for each, room for 8 or more.
- **Lower left:** the count of balls, with a sprite of the ball beside it,
  in the same presentation as the nuggets.
- **Right:** the energy gauge, a narrow vertical bar that rises and
  falls. It is narrower than the counts on the left. The bar there now is
  a placeholder.

The digits are sprites, 6x8 with a 1 px black outline, so they read over
any rock or steel. Each digit's outline overlaps the last one's, so a
5-digit count with its nugget is about 45 px wide. On the widest stages
the counts reach into the playfield, and those stages leave them room.

Each screen has an XRAM layout of its own. The keyboard, the gamepads,
the PSG, the sprite lists, and the small shared images stay put, and the
screens share the rest of XRAM as a union. A screen loads its art from
the ROM's assets when it starts, in a fraction of a second, so its art has
most of XRAM to itself.

## The Title

The title has the same cave as a stage, with no frame: a texture behind
everything and a curtain set, both picked at random each time, with the
curtains just outside the word QUARRY. Under the logo are the menu,
RESUME and NEW GAME, and under it a box as wide as the menu with the
progress of the save, as a percent. There is no sled on the title, and no
way to exit the game: every menu leads to another screen. More decoration
comes later.

## Stone: the levels

The curtains, the bricks, the break frames, the nuggets, and the logo.

- Rough, matte stone with chipped, irregular edges. Bricks are blocks of
  rock, not cut gems: no facets, no glassy shine.
- An ore shows as flecks, veins, or crystals in the rock. Each ore has its
  own colors, and its nugget is a small rough lump of the same ore.
- The curtains are quarry walls of ledges, boulders, and cracks, with no
  repeating tiles. Their inner edges are the walls of the playfield.
- The curtains are the model for how stone is drawn: warm weathered
  sandstone blending into cool blue-grey granite, angular chips, deep
  cracks, and a dark outline.
- The logo, `art/logo.png`, is layered sandstone carved with care: whole
  letters with crisp bevels, the same colors on every letter, a few chips,
  and dark specks in its seams. `art/logo.py` turns Retro Diffusion's logo
  into `art/logo.png`, and turns any moss green to rock.

References: `ref/old-logo-qu.png`, `ref/rock-crop.png`, `ref/logo-stone.png`, `ref/stone-wall.png`, `ref/ore-blocks.png`.

### Behind the Playfield

Behind the bricks is the faintest texture, so the playfield is not plain
black: two octaves of Perlin noise, cut into four very dark colors of
equal area, in large soft patches. `art/texture.py` makes it at build
time. It is a mode 3 bitmap at 2 bits a pixel, the size of the screen,
19 KB, and it wraps. There are four, one for each seed of
`QUARRY_TEXTURE_SEEDS` in `CMakeLists.txt`, and each stage picks one at
random and shows it from a random place, so it never seems to repeat. To
add one, add a seed there and raise `TEXTURES` in `src/scene.c`.

The texture's four colors come from the curtain set, so the floor matches
the walls: `art/curtain.py` takes the hue of the darker half of the rock,
at four faint levels.

In front of the texture, behind the ball, stand the supports and the
machines of the mine:

- a 45 degree knee brace in each top corner, from the post up to the beam,
  bolted at each end, heavy and a little cartoonish;
- a machine bolted to the inside of the right wall. It is not explained.
  It hints that it powers the energy gauge. Upgrades may add more machines
  along the walls.

### Curtain Sets

A curtain set is one Retro Diffusion image, split into the two curtains.
There can be many, and a stage picks one at random. To make one:

1. Generate a 256x240 image with `rd_pro__default`, with
   `ref/old-logo-qu.png` as the reference, and this prompt: "Looking straight
   at two rough quarry rock walls that fill the left and right halves of
   the image and frame a narrow dark vertical shaft down the middle:
   organic fractured stone with stacked broken ledges, angular boulders
   and deep cracks, warm weathered sandstone blending into cool blue-grey
   granite, a few faint dull ore streaks, soft light from the upper left,
   the whole wall dark and muted like a backdrop behind gameplay". Ask
   for 3 at a time with `num_images` for variety, and keep the prompt and
   the reference as they are. With `ref/rock-crop.png` as the reference,
   or other rock named in the prompt, the rock came out two or three times
   too big, and the shaft was lost.
2. Save it as the next `art/curtains/curtain-<n>.png`, and raise
   `QUARRY_CURTAIN_SETS` in `CMakeLists.txt` and `CURTAIN_SETS` in
   `src/scene.c` to match.
3. Look at it in the game: on the title screen, Shift and Left or Right
   switch the curtain set.

The build runs `art/curtain.py` on it. The shaft goes clear, so each
curtain keeps the rock's own edge, and the texture shows through past it.
The shaft is the flat colors that run down the middle column for 32 rows
or more. Where rock crosses the middle instead, the curtain's inner edge
is a straight cut, which looks like a seam: reject that image.
The rock is darkened, since this is underground, and cut to 15 colors of
its own palette, and the texture's four colors are made from it. Each
curtain is the 100 columns beside the middle. The build writes
`curtain<n>.png` in the build folder to look at.

## Industrial: the player's equipment

The sled, its flames and smoke, the ball, the energy gauge, and the
upgrade screen.

- Heavy modern machinery, slightly futuristic: clean panel lines, bolted
  plates, pistons, thruster nozzles, and small indicator lights.
- Safety-yellow paint over graphite steel, with black and yellow hazard
  chevrons.
- Used but maintained: scuffs and worn paint on the edges and corners.
  Rust, dents, and grime that read as neglect are out.
- Built for someone who gets their hands dirty and does a professional
  job. It looks heavy, solid, and dependable.
- The ball is part of the kit: forged steel.

References: `ref/sled-kit.png` for the sled and its parts,
`ref/ui-kit.png` for the energy gauge and the upgrade screen.

### The Frame

The posts and the cap beam are industrial too, a mine's post-and-cap set
in the sled's yellow and graphite, from `art/screen.py`. The inner face of
each post and the underside of the beam are bright lines, where the ball
bounces. A post has a hydraulic section every 64 rows, the beam a hazard
band, and a bracket caps each post where the beam ends. The beam is
pieces 64 wide that repeat every 8 px, so the width between the outer
faces of the posts must be a multiple of 8. `art/screen.py` also draws
the braces, the machine, the digits, and the placeholder gauge. The
braces and the machine use the shade row, so their brightness is set
there, not in their pictures. Run it
after a change there, then touch up any piece by hand.

### The Sled

The sled is the paddle. Its top is the surface that the ball bounces off,
so it must be unmistakable:

- The top is one flat, crisp plate, the full width of the sled, with a
  bright top edge.
- The plate reaches a couple of pixels past the machinery that hangs
  under it, on both sides. A ball that misses the plate clearly misses,
  even when it passes close to the machinery.
- Nothing rises above the plate, so its top row of pixels is where the
  ball bounces.
- The plate is thin, 3 rows: a bright top row, safety yellow, and a darker
  underside that bevels in at the ends. It has no hazard stripes.
- Under it is a slim graphite mount, and under the mount a small bell
  nozzle for each jet, with a slim flame no wider than the nozzle's mouth,
  6 rows at its longest.

The sled grows with each width upgrade, by the widths of `TUNE_WIDTHS`
in `src/tuning.h`. It starts with one jet and gains up to three, by
`TUNE_JETS`. The game is a power trip: the widest sled is easy to play,
even on the widest playfield.

Each width has a picture of its own, so each sled can have details of its
own, such as its scuffs, and a lamp between each two jets. The build draws
them with `art/sled.py` from the tuning, so a change to the widths or the
jets needs only a rebuild, and writes them to `sleds/` in the build folder
to look at. A picture holds the sled level, then tilted twice for its
fall. Once the widths settle, the pictures can move into `art/` to be
touched up by hand.

The jets are sprites of their own, a nozzle and its flame, in
`art/jet.png`, so they can swivel. A jet leans a little to push the sled
the way it moves, and `MODE5_HFLIP` mirrors the lean for the other way.

A ball that clips the side of the machinery may count for something
later, such as a rare bonus. The art leaves room for it.

### The Energy Gauge

The energy gauge is a narrow vertical bar on the right side of the
screen. It reads like a thermometer with no bulb, built as an industrial
indicator: a tube in a steel frame, with the level rising and falling in
it. It leaves room on its left and right for effects at the level line.

## Rules for both

- The light comes from the upper left.
- Sprites have a dark outline, near-black navy, like the logo.
- The pieces in play, the bricks, the ball, and the sled, have the
  strongest contrast. The curtains stay in the darker half of the values,
  and the texture behind the playfield is darker still.
- Pixels are on the native grid of the canvas, 320x240. No art is scaled
  in the game.

## Palettes

The game has 1 KB of palettes: 512 colors, or 32 rows of 16.
`palettes_t` in `src/xram.h` holds them, in the order of the rows of
`art/palettes.png`, and `MODE5_PALETTE_CHECK(palettes_t)` stops the build
if they pass 512 colors.

In each row, index 0 is transparent, and indexes 1 to 15 are colors,
darkest first. Each class of art gets a row of its own:

| Row | Used by |
| --- | --- |
| main | the text and the menus, and the ball |
| bricks | one per ore: the brick, its break frames, its nugget, and its nugget sprite |
| fx | the smoke and the energy gauge |
| logo | the title logo |
| sled | the sleds, their jets and flames, the frame, the braces, the machine, and the digits |
| texture | the texture behind the playfield, its first 4 colors, loaded with each curtain set |
| curtain | the curtain set of the stage, loaded with it |
| shade | the sled row at 60%, for the braces and the machine behind the ball |

A jet's nozzle and its flame are one sprite, so the flames share the sled
row. Every curtain set brings its own palette into the one curtain row.
That is 7 rows and the ores, so 25 rows are left for ores.

## Sizes

| Art | Size |
| --- | --- |
| brick | 24x8 |
| break frames | 2 frames, 24x16 |
| nugget, nugget sprite of a count | 8x8 |
| ball, ball sprite of the count | 8x8 |
| digit | 8x12 sprite, a 6x8 digit with its outline |
| texture | 320x240 at 2 bits a pixel |
| post | 8 wide, in pieces 64 tall |
| cap beam | 16 tall, in pieces 64 wide, and a cap 8x16 over each post |
| brace | 32x32 |
| machine | 24x40 |
| sled | the widths of `TUNE_WIDTHS`, up to 64, rounded up to 4 for the sprite; 8 tall, then its two tilts, 24 tall each |
| jet | 7 frames, 8x12: the nozzle alone, 3 flames, 3 swiveled flames |
| smoke | 3 frames, 8x8 |
| energy gauge | a narrow vertical bar; the placeholder is 8 wide, in pieces 8 tall |
| logo | 3 pieces, 64x64, as one 192x64 image |
| curtains | 100x240 each, cut from a 256x240 curtain set |

The current sizes come from `src/xram.h`. RD Pro styles start at 12x12, so
art 8 pixels tall is made as a larger study, then redrawn by hand at its
size.

## Making Art with Retro Diffusion

1. Choose the style: `rd_pro__default` for one piece or a curtain,
   `rd_pro__spritesheet` for a family of small pieces in one image, and
   `rd_pro__ui_panel` for the parts of the upgrade screen. Each image
   costs $0.18, and the cost estimate is free.
2. Write the subject, then add the block of its look from below. The
   style draws the pixels, so the prompt never says "pixel art". For a
   single piece, give a plain background, such as "on a plain black
   background", and remove it with `remove_bg`.
3. Pass a reference: `ref/rock-crop.png` for stone, or a crop of up to
   64x64 from `ref/sled-kit.png` for industrial. Keep references small
   RGB PNGs. The API refused the indexed `art/logo.png`.
4. Reduce the colors to 15 with Retro Diffusion's `color_reducer`, which
   is free, or map them onto a row with its `palette_converter`.
5. Convert it with `art/rd2png.py`:

   ```bash
   python3 art/rd2png.py ore.png art/brick.png --palette-out row.png
   python3 art/rd2png.py nugget.png art/nugget.png --palette art/palettes.png --row 4
   ```

   The first writes the colors as a palette row, to add to
   `art/palettes.png`. The second puts a piece on a row that is already
   there.
6. Build the game, and judge the art in the emulator, in front of the
   curtains and the texture, not as a loose image.

The blocks of the looks:

- **Stone:** "rough matte quarried stone, chipped edges, dark outline,
  light from the upper left"
- **Ore:** the stone block, then the ore, such as "granite with
  copper-green malachite veins", then "matte stone, not polished gems"
- **Curtain:** "the whole wall dark and muted like a backdrop behind
  gameplay"
- **Industrial:** "heavy modern mining machinery, safety-yellow paint over
  graphite steel, black and yellow hazard chevrons, bolted plates, scuffed
  edges and worn paint but clean and well maintained, slightly futuristic,
  light from the upper left"
- **Sled:** the industrial block, then "a single flat, crisp top plate
  that overhangs the machinery beneath it by a couple of pixels on each
  side"

## The Reference Images

| File | What to take from it |
| --- | --- |
| `ref/old-logo-qu.png` | 64x64 of the old logo's QU: fine, flecked rock at a small scale. The reference for the curtain sets, and the one that made the first. |
| `ref/rock-crop.png` | 64x64 of the rock of the first curtain set: how stone is drawn. A reference for a stone piece, such as the logo. Not for a curtain set: it is zoomed in, so the rock comes out too big. |
| `ref/logo-stone.png` | The logo as Retro Diffusion made it, before `art/logo.py`: `rd_pro__typography`, 192x64, with `rock-crop.png` and `old-logo-qu.png` as references: "\"QUARRY\" in big bold blocky capital letters, carefully carved from solid stone by a master stonemason: clean even letterforms with crisp chiseled bevels and flat faces, every letter whole and unbroken, only a few small natural chips and fine hairline marks, all the letters the same warm weathered sandstone with subtle flecks like the reference rock, cool blue-grey stone only in the shadowed bevels, a dark outline and a dark shadow under the letters, light from the upper left, on a plain white background". One of three, and the one with moss, which `art/logo.py` turns to rock; the others were plainer, or cracked with stray dots. |
| `ref/stone-wall.png` | The organic shapes of the curtains, and the warm sandstone turning to cool granite. It is too bright as it is. |
| `ref/ore-blocks.png` | Matte ore rock and the pairing of each brick with its nugget. Eight candidate ores: limestone, gold-flecked sandstone, malachite in granite, iron ore, coal, silver in slate, rose quartz, and amber in basalt. Stage 1's white is the limestone. |
| `ref/sled-kit.png` | The colors, the chevrons, the bolts, and the thrusters. Keep the scuffs and leave out the rust specks. Its tops are not flat: the new sled has the flat, overhanging top plate of [The Sled](#the-sled). |
| `ref/ui-kit.png` | Graphite panels with yellow trim, gauges, and meters. Its vertical meter is a start for the energy gauge. |

The prompts that made them, all RD Pro, with no seed returned:

- `stone-wall.png`, `rd_pro__default`, 256x240, with `old-logo-qu.png` as a
  reference: "Looking straight at the inner wall of a deep open-pit
  quarry: an organic face of rough, fractured stone that fills the whole
  image, stacked broken ledges, angular boulders and deep vertical cracks,
  warm weathered sandstone blending into cool blue-grey granite, a few
  faint dull ore streaks, soft light from the upper left, the whole wall
  dark and muted like a backdrop behind gameplay"
- `ore-blocks.png`, `rd_pro__spritesheet`, 256x256, with `old-logo-qu.png`
  as a reference: "Eight rough rectangular blocks of quarried rock, each
  about three times as wide as it is tall, chipped stone edges and a dark
  outline, each with a small matching rough nugget of its ore beside it:
  pale limestone, sandstone flecked with gold, granite with copper-green
  malachite veins, rust-red iron ore, black coal seam, slate with pale
  silver threads, quartz with pink feldspar, dark basalt with amber
  crystals; matte stone, not polished gems, light from the upper left, on
  a plain black background"
- `sled-kit.png`, `rd_pro__spritesheet`, 256x256: "Parts of a heavy
  industrial mining hover sled seen from the side: a long, low armored
  vehicle body in short, medium and long lengths, separate left end cap,
  middle section and right end cap pieces, downward thruster nozzles,
  hydraulic pistons and bolted steel plates; safety-yellow paint over
  graphite steel with black and yellow hazard chevrons, scuffed edges and
  worn paint but clean and well maintained, modern and slightly futuristic
  heavy machinery, light from the upper left, on a plain white background"
- `ui-kit.png`, `rd_pro__ui_panel`, 256x256: "Control panel parts for
  heavy modern mining machinery: riveted graphite steel panels with
  safety-yellow trim, chunky industrial push buttons and toggle switches,
  a round analog pressure gauge, a vertical segmented energy meter, hazard
  stripe bars, worn edges and scuffed paint but clean and well maintained,
  built for hard daily work"
