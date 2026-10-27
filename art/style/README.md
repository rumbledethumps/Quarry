# Quarry Art Style

Quarry has two looks. The levels are **stone**: a rough, organic quarry
wall, and bricks of rock with their ore showing through. The player's
equipment is **industrial**: heavy modern mining machinery, used every day
and well looked after. Every new piece of art belongs to one of the two.

The images in `ref/` set the look. Pass them as references when making new
art, and compare new art against them.

## Stone: the levels

The backdrop, the walls, the bricks, the break frames, the nuggets, and
the logo.

- Rough, matte stone with chipped, irregular edges. Bricks are blocks of
  rock, not cut gems: no facets, no glassy shine.
- An ore shows as flecks, veins, or crystals in the rock. Each ore has its
  own colors, and its nugget is a small rough lump of the same ore.
- The backdrop is a quarry wall of ledges, boulders, and cracks, with no
  repeating tiles. It is dark and muted, so the ball and the bricks stand
  out in front of it.
- The logo, `art/logo.png`, is the model for how stone is drawn: warm
  sandstone, fine cracks, and a dark navy outline and shadow.

References: `ref/stone-wall.png`, `ref/ore-blocks.png`, `ref/logo-crop.png`.

## Industrial: the player's equipment

The paddle, its flames and smoke, the ball, the energy bar, and the
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

References: `ref/sled-kit.png` for the paddle and its parts,
`ref/ui-kit.png` for the energy bar and the upgrade screen.

## Rules for both

- The light comes from the upper left.
- Sprites have a dark outline, near-black navy, like the logo and the
  text panels.
- The pieces in play, the bricks, the ball, and the paddle, have the
  strongest contrast. The backdrop stays in the darker half of the values.
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
| main | the text, the panels, and the menus |
| backdrop | the backdrop of a stage, one row for each stage that differs |
| logo | the title logo |
| sled | the paddle, and the machinery on the upgrade screen |
| flames | the thruster flames |
| hud | the ball, the ball icons, the smoke, and the energy bar |
| one per ore | the brick, its break frames, its nugget, and its nugget icon |

With 4 backdrops, that is 9 rows, which leaves 23 for ores.

Today `palettes_t` has `main`, `bricks[BRICK_COLORS]`, `fx`, and `logo`.
It changes to the rows above as the new art comes in.

## The Backdrop

The tiled background goes away. Each stage gets one painted backdrop,
an organic quarry wall like `ref/stone-wall.png`, with the walls of the
playfield painted into it.

The proposed way to draw it, which is still a code change to make:

- A mode 3 bitmap, 320x240 at 4 bits a pixel, which is 38,400 bytes of
  XRAM and one palette row.
- It replaces the tile layer, the 17 tiles and the tile map.
- Each stage's backdrop is a ROM asset. The game loads it into XRAM when
  the stage starts, so only one is in XRAM at a time. With it, about
  50 KB of the 64 KB of XRAM is in use.

Retro Diffusion's RD Pro styles make images up to 256 pixels wide. A
320-wide backdrop is a 256x240 image with 32 pixels added to each side by
outpainting, or with plain stone on the sides where the panels cover it.

## Sizes

| Art | Size |
| --- | --- |
| brick | 24x8 |
| break frames | 2 frames, 24x16 |
| nugget, nugget icon | 8x8 |
| ball, ball icon | 8x8 |
| paddle pieces | 8x8 each: left end, middle, right end |
| flames | 3 frames, 8x8 |
| smoke | 3 frames, 8x8 |
| energy bar | 5 pieces, 28x4 |
| logo | 3 pieces, 64x64, as one 192x64 image |
| backdrop | 320x240 |

The sizes come from `src/xram.h`. RD Pro styles start at 12x12, so art 8
pixels tall is made as a larger study, then redrawn by hand at its size.

## Making Art with Retro Diffusion

1. Choose the style: `rd_pro__default` for one piece or a backdrop,
   `rd_pro__spritesheet` for a family of small pieces in one image, and
   `rd_pro__ui_panel` for the parts of the upgrade screen. Each image
   costs $0.18, and the cost estimate is free.
2. Write the subject, then add the block of its look from below. The
   style draws the pixels, so the prompt never says "pixel art". For a
   single piece, give a plain background, such as "on a plain black
   background", and remove it with `remove_bg`.
3. Pass a reference: `ref/logo-crop.png` for stone, or a crop of up to
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
   backdrop, not as a loose image.

The blocks of the looks:

- **Stone:** "rough matte quarried stone, chipped edges, dark outline,
  light from the upper left"
- **Ore:** the stone block, then the ore, such as "granite with
  copper-green malachite veins", then "matte stone, not polished gems"
- **Backdrop:** "the whole wall dark and muted like a backdrop behind
  gameplay"
- **Industrial:** "heavy modern mining machinery, safety-yellow paint over
  graphite steel, black and yellow hazard chevrons, bolted plates, scuffed
  edges and worn paint but clean and well maintained, slightly futuristic,
  light from the upper left"

## The Reference Images

| File | What to take from it |
| --- | --- |
| `ref/logo-crop.png` | The Q of the logo: how stone is drawn. The reference for every stone prompt. |
| `ref/stone-wall.png` | The organic shapes of the wall, and the warm sandstone turning to cool granite. It is too bright to sit behind play as it is. |
| `ref/ore-blocks.png` | Matte ore rock and the pairing of each brick with its nugget. Eight candidate ores: limestone, gold-flecked sandstone, malachite in granite, iron ore, coal, silver in slate, rose quartz, and amber in basalt. Stage 1's white is the limestone. |
| `ref/sled-kit.png` | The colors, the chevrons, the bolts, and the end caps of the paddle. Keep the scuffs and leave out the rust specks. |
| `ref/ui-kit.png` | Graphite panels with yellow trim, gauges, and meters, for the energy bar and the upgrade screen. |

The prompts that made them, all RD Pro, with no seed returned:

- `stone-wall.png`, `rd_pro__default`, 256x240, with `logo-crop.png` as a
  reference: "Looking straight at the inner wall of a deep open-pit
  quarry: an organic face of rough, fractured stone that fills the whole
  image, stacked broken ledges, angular boulders and deep vertical cracks,
  warm weathered sandstone blending into cool blue-grey granite, a few
  faint dull ore streaks, soft light from the upper left, the whole wall
  dark and muted like a backdrop behind gameplay"
- `ore-blocks.png`, `rd_pro__spritesheet`, 256x256, with `logo-crop.png`
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
