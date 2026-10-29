# Quarry Art Style

Quarry has two looks. The levels are **stone**: rough, organic quarry
walls. The player's equipment is **industrial**: heavy modern mining
machinery, used every day and well looked after. Every new piece of art
belongs to one of the two, but the bricks, which are plain colors, as in
a classic brick breaker: see [Bricks](#bricks).

The images in `ref/` set the look. Pass them as references when making new
art, and compare new art against them.

## The Words

What the game calls things, on its screens and in what the dwarves say,
always in capitals. The code calls fuel energy, and how much of an upgrade is
bought its rank.

| Word | What it is |
| --- | --- |
| LEVEL | One playfield of bricks. Mines are dug in levels, each deeper than the last. Its cart on the upgrade screen begins it. |
| BRICK | A block of rock, broken by the ball. |
| NUGGET | The token that comes out of a broken brick, a ball of its color, and flies to the counts. Nuggets buy upgrades. |
| COIN | One for the first clear of each level, never again. Coins will open the upgrades' next tiers. |
| SLED | The paddle, which floats on its jets. |
| FUEL | What the gauge on the right shows. When it runs out, the sled falls, and the level ends once the balls in play have fallen off the screen too. |
| BALL | The ball, and the count of those left. |
| HITS | What breaks a brick: each hit of the ball does its DAMAGE, and the brick breaks once the damage reaches its hits. |
| THE DRY | The upgrade screen, as the menus and the dwarves call it: the change house at a mine, where miners change into their work clothes, hang their wet gear to dry, and wait for their shift. The code and this guide still call it the upgrade screen. |
| UPGRADE | A panel on the rail in THE DRY, and what it buys. |
| CART | A level, on the train of mine carts under the rail. |

## The Screen

A level's playfield is framed in steel: a post on each side and a cap beam
across the top, where the ball bounces. Outside the posts are the
curtains, the rock walls of the quarry. Each level places its walls, to
the pixel, each side on its own: level 1 is 4 bricks across with half a
brick of space at each wall. The widest can be about 10 bricks, with a
little rock left on each side. Each level is laid out fresh, so the
curtains never move while anyone watches.

The counts float over the curtains, with no panels behind them:

- **Upper left:** a count for each kind of nugget, with a sprite of the
  nugget beside it, a line for each, room for 8 or more.
- **Lower left:** the count of balls, with a sprite of the ball beside it,
  in the same presentation as the nuggets.
- **Right:** the energy gauge, a sight glass down the right edge, from
  the top of the screen to its foot: see [The Energy Gauge](#the-energy-gauge).

The digits are sprites, 6x8 with a 1 px black outline, so they read over
any rock or steel. Each digit's outline overlaps the last one's, so a
5-digit count with its nugget is about 45 px wide. On the widest levels
the counts reach into the playfield, and those levels leave them room.

Each screen has an XRAM layout of its own. The keyboard, the gamepads,
the PSG, the sprite lists, and the small shared images stay put, and the
screens share the rest of XRAM as a union. A screen loads its art from
the ROM's assets when it starts, in a fraction of a second, so its art has
most of XRAM to itself.

## The Title

The title has the same cave as a level, with no frame: a texture behind
everything and a curtain set, both picked at random each time, with the
curtains just outside the word QUARRY. Under the logo are the menu,
RESUME and NEW GAME, and under it a box as wide as the menu with the
progress of the save, as a percent. There is no sled on the title, and no
way to exit the game: every menu leads to another screen. More decoration
comes later.

## Stone: the levels

The curtains and the logo.

- Rough, matte stone with chipped, irregular edges, not cut gems: no
  facets, no glassy shine.
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

### Bricks

The bricks are plain colors, gray, red, green, blue and gold, in that
order, picked with simulations of each kind of color blindness so every
pair stays apart, and none white, as the ball is. Gray is a light gray,
so it stands out from the steel of the frames and the machinery, as the
colors do, and light enough that it is never taken for the red. `art/bricks.py` draws every piece
of them by rule, and nothing is touched up by hand:

- **Brick:** 24x8 with no gap of its own, its face the plain color and a
  1 px bevel all round, light on the top and the left, dark on the bottom
  and the right. Widths are multiples of 4. Each level, in
  `levels/levels.py`, places its bricks, 2 px apart on levels 1 and 2.
- **Cracks:** sprites over the brick, so they flip either way: black lines
  with a gray lip under them, in sets of ten, a step for each 10% of a
  brick broken, rounded up, so any damage shows the first. One crack grows
  from inside the brick, up and down, a pixel or more each step, to reach
  both edges, through the bevels, at the last. A second starts beside it
  once the brick has 59% left, and grows faster, to reach both edges at
  the last too.
- **Chunks:** rough lumps of the brick's colors, lit like it, that fly up
  and out when it breaks, fall, and turn over as they go.
- **Nugget:** a sphere of the brick's color, lit from the upper left,
  with a dark outline: 7 px across as it flies, and as tall as the digits
  beside its count.
- **Coin:** the same circle as the big nugget, in the sled row's gold,
  beveled, with a square hole cut in the middle, clear inside an outline
  of its own, as every edge is outlined.
- **Ball:** a sphere shaded as the nuggets are, but a very bright white,
  8 px across in play, and as tall as the digits by its count.

### Behind the Playfield

Behind the bricks is the faintest texture, so the playfield is not plain
black: two octaves of Perlin noise, cut into four very dark colors of
equal area, in large soft patches. `art/texture.py` makes it at build
time. It is a mode 3 bitmap at 2 bits a pixel, the size of the screen,
19 KB, and it wraps. There are four, one for each seed of
`QUARRY_TEXTURE_SEEDS` in `CMakeLists.txt`, and each level picks one at
random and shows it from a random place, so it never seems to repeat. To
add one, add a seed there and raise `TEXTURES` in `src/scene.c`.

The texture's four colors come from the curtain set, so the floor matches
the walls: `art/curtain.py` takes the hue of the darker half of the rock,
at four faint levels.

In front of the texture, behind the ball, stand the supports and the
machines of the mine:

- a knee brace in each top corner, from the post up to the beam, the frame
  set's own, so dark it is barely there, and nobody takes it for something
  to bounce off;
- a machine bolted to the inside of the right wall. It is not explained.
  It hints that it powers the energy gauge. Upgrades may add more machines
  along the walls.

### Curtain Sets

A curtain set is one Retro Diffusion image, split into the two curtains.
There can be many, and a level picks one at random. To make one:

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
The rock is darkened, since this is underground, and cut to 13 colors of
its own palette, and the texture's four colors are made from it: first to
15, merging the closest colors, then to 13, merging the least used, which
changes the fewest pixels. Merging the closest all the way to 13 joined
big areas of the rock and changed the texture's tint. The row's other two
colors are for the sight glass of the energy gauge. Each
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
- Nothing looks broken or dangerous: no cracks, bends, gouges, or missing
  rivets and bolts. Competent engineers built it and keep it up.
- Built for someone who gets their hands dirty and does a professional
  job. It looks heavy, solid, and dependable.
- The ball is part of the kit: forged steel.

References: `ref/sled-kit.png` for the sled and its parts,
`ref/ui-kit.png` for the energy gauge and the upgrade screen.

### The Frame

The posts and the cap beam are steel girders, gray, with no yellow and
no hazard stripes, so the frame never competes with the menus' caution
tape. They are drawn like the rest of the screen: crisp line art, a dark
outline around every piece, a bright flange along each edge, and evenly
spaced rivets. Used but maintained, never damaged: no cracks, dents, or
gouges. They come in frame sets, and each new level picks one at random,
as it picks its curtains; a level played again keeps its frame. Each set's
art is in `art/frames/frame-n.png`, drawn at the game's scale by Retro
Diffusion or by hand, and `art/frames.py` cuts it to the game's sizes.

- The ball bounces off bright steel: the dark outline of a post or the
  beam, with bright steel just inside it. No rubber strip or shadow on
  the edge it hits.
- A post shows up to 20 columns, from its inside, and the beam is 16
  tall, so the ball bounces where it always has. Where the
  art is wider, plain columns or rows of its web are left out, and where
  it is narrower, plain ones repeat, never a rivet, a brace or an edge.
- A post is one image 48 rows tall, down the screen again and again. A
  playfield can be any width, to the pixel. The beam runs behind the
  posts' caps, in pieces 48 wide, its art repeating every few px, 8 or 12,
  from the middle of the screen, so it looks the same at both posts and
  the posts can slide in and out over it. Each cap is solid across as
  many of its inside columns as the beam's repeat, so the beam never
  shows through it; a truss's cap is filled with its darkest steel behind
  its bars. Retro Diffusion spaces rivets unevenly, so a girder's post and
  beam are each one 8 px cell of its art, a rivet and its plate, repeated:
  the rivets fall every 8, one at the middle of the screen.
- The knee braces stand behind the ball and are barely there, so nobody
  takes one for something to bounce off: the set's colors darkened,
  without the rock or the shadows around them. Nothing behind the ball is
  brighter than the machine on the right wall, and `art/frames.py` stops
  the build if a brace is.
- Set 1 is a riveted girder showing 16, its knee braces gusset plates.
- Set 2 is an open truss of welded steel bars showing 18, X bracing in
  square cells that the rock shows through, like lighting truss built
  heavy for construction, drawn by hand in `art/frames/frame-2.png`. A bay
  is 12: a bar 2 wide between outlines, then an X in an 8x8 opening, each
  stroke outlined on both sides. Its chords are 5 wide, an outline, three
  of steel and an outline, each lit on its outer side, so a tower is the
  same inside and out, and a pixel heavier than its bars. The beam is the tower laid on its side, each bay from
  half an upright to half an upright, so every level's beam ends the same
  at both towers, and its top chord runs off the top of the screen; the
  towers run on up past it. Its brace is the gusset Retro Diffusion drew
  for the truss it was chosen from, gone gray.
- The concepts in `art/style/ref/frame-*.png` hold more looks for the next
  sets, such as the mine shaft frames of D1, D3 and D4.

`art/screen.py` draws the machine, the digits, and the old energy bar, now
only the upgrade screen's stand-in picture of the gauge.
The machine uses the shade row, so its brightness is set there, not in its
picture. Run it after a change there, then touch up any piece by hand.

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
to look at. A picture holds the sled flat, then tilted twice for its
fall. Once the widths settle, the pictures can move into `art/` to be
touched up by hand.

The jets are sprites of their own, a nozzle and its flame, in
`art/jet.png`, so they can swivel. A jet leans a little to push the sled
the way it moves, and `MODE5_HFLIP` mirrors the lean for the other way.

A ball that clips the side of the machinery may count for something
later, such as a rare bonus. The art leaves room for it.

### The Energy Gauge

The energy gauge is a sight glass down the right of the screen, the one
instrument the operator watches all day: a glass tube with the fuel in
it, between two brass fittings, each a pipe off the edge of the screen
into a hex nut that grips the glass. It is 16 wide, 4 px in from the
edge, over the right curtain, and `levels/levels.py` keeps every level's
post clear of it.

- The glass is 12 wide with its outline, and exactly 200 tall: a row for
  each step of the fuel's level, which moves a pixel at a time.
- The glass shows the rock behind it, a little tinted, and that is what
  makes it. As a level starts, `src/energy.c` copies the right curtain's
  pixels under it into its image, and draws them in the glass row: the
  curtain's 13 colors 15% of the way to a pale blue, which
  `art/curtain.py` makes with each curtain set. Where the shaft is clear
  behind it, it shows the darkest rock.
- A glint runs down the glass 2 px in from its left, a flat color. A glint
  that showed the rock through it too cost 400 bytes, and nobody could
  tell.
- The fuel is a pale blue, cool rocket fuel in the hue of the holographic
  cursor, lit from the upper left, in 7 shades across: a rim at its left
  wall, the glint, the brightest just past it, and darker to its right
  wall. Its surface is a bright line, and it climbs a pixel up each wall.
  It is in a row of its own, the liquid row, so its color can change, as
  it may. `art/gauge.py` draws it and the fittings.
- Each time the ball bounces off the sled, a bubble rises from the foot of
  the fuel to its surface, a pale ring 3 across that sways a pixel either
  way, while one of the 3 is free. At the surface it pops and throws up a
  single drop of the fuel, which hops 3 px into the air and falls back in,
  as a real bubble does breaking through. A bubble is never taken from
  another: every one rises all the way, and is free again once its drop
  is back in.
- The fittings are stand-ins, in a dull brass, not gold, to be replaced.
- Still to come: more bubbles at other times, the fuel sloshing, and a
  look for low fuel. The
  beeps and the machine's lamp warn of it now.
- The Oracle, `ref/oracle.png`, was the design before: a steel scale with
  a cursor riding it, a sight glass in the cursor and a clockwork chevron.
  It is parked, as no model could draw its cursor at its size.

### The Upgrade Panels

The upgrade screen's panels hang from a rail and slide across it. Each is
20 cells by up to 18, in an 8-bit tile layer of its own, with 256 colors
and 256 tiles. The frame is two cells thick, drawn 3 px in from the edge of
its cells, so two panels side by side have a 6 px gap. The frame is
graphite steel with no yellow: there is nothing to be careful of here.

- `art/panel-frame.png` is frame 1 of the reference images, fitted to the
  cells: a few repeated rows and columns of steel taken out, so its inner
  bevel ends 16 px in. Its bottom edge came out of Retro Diffusion cut
  short, so the build uses its top half turned over for the bottom.
- `art/panels.py` builds each panel's frame from its cells: the corners,
  with their clamps, as they are, and plain steel, bolts and hangers along
  each edge, as `LAYOUTS` says for each panel. The plain steel walks
  through frame 1's own plain cells in their order, each edge of each
  panel from a place of its own, so the grain of the steel never repeats
  cell after cell as if cloned. The inner ring's plain steel is one cell
  repeated, the one most like the others, since it hardly varies in
  frame 1 and its tiles come twice. The clamps stand a pixel proud, out into
  the gap. Panels of any height share the same tiles, each can have its
  own bolts, and heights step by two rows, a line of text. The build fails
  past 256 tiles, and says how many the frames take.
- `art/panel-font.png`, from `art/panel_font.py`, is the font on the
  plates: chunky 6x7 capitals, cream fading toward the foot, with a shadow,
  plus short digits in red for a cost not yet paid, and the pips.
- A panel's display dims, and its steel doesn't: the font, the plate and
  its corners come lit and dim, and so does the frame's inner ring, which
  holds the display's bevel, but there only what is inside frame 1's black
  outline dims. So an unlit display is dark right to the frame. The outer
  ring comes once.
- The contents take 122 tiles, the inner rings 66 and the outer rings 66,
  so 1 is left: a new glyph, lit and dim, has to free two.
  Retro Diffusion can't make variants that join frame 1: at a low strength
  it copies it, at a high one it redraws its steel, and inpainting ignored
  its mask. New corners or edge pieces are drawn here, on frame 1's steel.

### The Backdrop

Behind the upgrade screen is a workshop wall: the rail the panels hang
from across the top, plain dark wall and a few gray pipes in the middle,
and machinery along the floor, behind the carts. It is one picture,
`art/backdrop.png`, in three bands of 16x16 tiles on plane 0, each with a
palette of its own:

- The top, 16 px, the rail, in 15 colors, shared with the trolleys. The
  art's own truss was too coarse for the strip of it that shows over the
  panels, so the wall from under it takes its place, and `art/backdrop.py`
  draws the rail over it: a steel I-beam in the panels' graphite, a little
  darker, with a rivet every 16 px and a plate joint every 64, its foot
  flange just over `PANEL_Y`, so it follows the panels if they move. A
  trolley rides it over each hanger, two wheels on the foot flange and a
  side plate in safety paint, and its wheels turn as the panels slide.
- The middle, from 16, behind the panels, in 4 grays at 2 bits a pixel, the nearest
  of the top's and the bottom's colors, so the bands join without a seam.
  It shows only between the panels and beside the first and the last, so
  it needs no color: nothing red or yellow belongs up there. The cells
  always behind the middle panel while the panels are still are one plain
  tile.
- The bottom, from 128, the machinery, in 15 colors, with the red valve
  wheel and the yellow paint and hazard stripes, and the track.

`art/backdrop.py` darkens it, a little cool, so the panels and the carts
stand out in front. The two cogs at the left of the floor turn all the
time, and now and then the vent by the piston puffs steam, without a
sound, which would wear thin:
the builder draws the cogs anew over the art's own, in four frames a tooth
apart, and cuts the steam drawn in the art into five frames that grow from
the vent and thin out. Both are plane 0 sprites over the bottom band.

- The picture came from `rd_pro__default`, 256x240, three at a time, with
  the strips of an earlier try as references, and this prompt: "Looking
  straight at the back wall of a mining machine workshop, side view,
  filling the frame edge to edge. Across the very top, a steel truss
  girder under the ceiling. The whole middle of the wall is plain and
  quiet: flat dark graphite steel wall panels with faint seams, and a few
  plain gray vertical pipes and steel columns running straight down from
  the girder to the machines below, with no valves, no gauges, no lights,
  no color and nothing interesting. All the machinery is low, in the
  bottom third, along the floor: big interlocking cogwheels, a hydraulic
  piston beside a small steam vent, a squat ore crusher, pipes with red
  valve wheels, safety-yellow paint and black and yellow hazard chevrons,
  and riveted steel floor plates along the bottom edge. Heavy modern
  mining machinery of graphite steel, bolted plates, scuffed edges but
  clean and well maintained, slightly futuristic, light from the upper
  left, the whole scene dark and muted like a backdrop behind gameplay".
  Without "plain and quiet" and the machinery kept low, the color lands in
  the middle, where it never shows.
- Retro Diffusion makes 256 wide at most, and its `tile_x` doesn't wrap
  cleanly, so the last 64 columns are outpainted: the right 192 columns,
  expanded 64 to the right, which fits its 256 window.

### The Mine Carts

The level select is a train of mine carts on a track along the foot of the
upgrade screen, the picked one in the middle. Each cart is 4 cells across
by 5 down, in a 4-bit tile layer of 16 colors, with its coupling in a
fifth cell at its axles. The level's number is on a plate in the cart's
middle two cells, lit on the cart picked. A locked level's plate is blank
under a padlock, a 16x16 sprite with its own 16 colors, its body over the
plate and its shackle over the rim; it comes in two halves too, to break
in two.

- `art/cart.png` is the cart, from `rd_pro__default`, 32x24, four at a
  time, `remove_bg`: "A small sturdy ore mine cart seen straight from the
  side: a riveted graphite steel tub with slightly sloped sides and a
  thick rolled rim, a safety-yellow band along the rim, a plain dark
  rectangular plate in the middle of its side, two small spoked steel
  wheels underneath, empty, scuffed but clean and well maintained, light
  from the upper left, on a plain white background". `art/carts.py` draws
  its own plate over the art's, wide enough for two digits, and the heap.
- `art/padlock.png` is the padlock, the same way at 16x16: "A heavy
  industrial padlock seen straight from the front: a squat safety-yellow
  steel body with a dark keyhole in its middle and a thick polished steel
  shackle on top, a dark outline, light from the upper left, on a plain
  white background". The builder clears the white inside its shackle and
  outlines its foot.
- The number sits in the middle of the cart, across and down, never a
  pixel off: rim to foot, the cart is centered on it, so the cart stands
  low in its cells, and its wheels need a fifth row.
- The number is stencilled on, as a real cart's would be painted: bold
  7x7 numerals of the carts' own, with a stencil's bridges, drawn by hand
  in `art/carts.py`, in the rim's safety yellow with a dark shadow on the
  cart picked, and a dull ochre on the rest.
- A level cleared carries a small heap of ore over the rim. A cart's top
  two rows come with the heap and without.
- The track is in the backdrop: `art/backdrop.py` draws a steel rail on
  sleepers in the panels' graphite at `CART_Y` plus the cart's foot, so it
  follows the carts if they move.

### The Menus

The menus are boxes in a 4-bit tile layer of 8x8 cells on plane 2, with
16 colors of their own, over everything but plane 2's sprites. A box is
dark navy inside, with its text in the panels' font, and framed in black
and yellow caution tape set in gray steel: from the outside in, a black
outline, a light steel edge, 4 px of tape, a dark steel edge, and a black
line. A menu stops play, and the tape says so. Its stripes run at 45
degrees, 4 px of each color, and march along the frame while the menu
shows, as the tape's 4 palette entries turn round.

- `art/menus.py` builds the tiles: a glyph for each letter of the font,
  the frame's 4 corners and 4 edges, whose stripes join from cell to
  cell, and the rule.
- A menu's title is set off from its items by a thin rule of light steel
  over its shadow, in the gap under it, two cells in from each side.
- The holographic cursor of the upgrade screen picks in the menus too, a
  cell in from the frame and as tall as the item. Its corners are one
  bright bracket, `art/cursor.png`, turned for each: two lines that fade
  out along the arms, the inner one shorter, 11 px across in a 12x12
  sprite. `art/screen.py` draws it at 8 px and stretches its lines, so it
  keeps that fade. It breathes 2 px out and back while its two brightest
  colors pulse. On the upgrade screen it
  slides into a question and back out; elsewhere it appears at once.
- Nothing is grayed out: an item that doesn't apply is left off.
- The title's boxes are plain, with no tape, until the title is
  redesigned.

## The Dwarves

Now and then a cartoon dwarf comes up from the foot of the screen with
something to say, in a speech bubble that comes in from the right at the
same time, the two stopping together. Half a second later the OK shows at
the end of the last line, with the holographic cursor close round it, and the
button sends them back the way they came. Only one dwarf shows at a time,
and the cursor is off while they come and go. They show when a screen
opens, never in the middle of play, and the screen under them carries on:

- the first level of a new game starts with a welcome;
- each first clear of a level has a dwarf hand over its coin, before the
  menu opens;
- on the upgrade screen, as level 2 unlocks, one says what an unlock
  means, as the unlock goes on over the carts, and the first time there,
  another says what the screen is for, after any other.

- A dwarf is a head-and-shoulders portrait, 80x80, in the outlined
  cartoon look of the sleds: bold shapes, a crisp dark outline, flat
  shading in a few colors, light from the upper left, facing a little to
  the right, toward his bubble. He stands in the lower left corner, his
  shoulders on the foot of the screen, and covers the counts there. On the
  upgrade screen his bubble's foot is just over the carts, so they show.
- Each dwarf is a portrait in `art/dwarves/` as Retro Diffusion drew it,
  in a frame of its own on a plain background. `art/talk.py` cuts off the
  frame, clears the background from the edges in, and brings him down to
  15 colors of his own. He is up to 3 sprites, a band across his head and
  a band across his shoulders, each as narrow as he is there, in 2816
  bytes at most, so every dwarf keeps to about his outline.
- The miner, `art/dwarves/miner.png`, the third of four, `rd_pro__default`,
  96x96: "Head and shoulders of a friendly cartoon dwarf miner, as a
  character portrait in a 16-bit game's dialogue, facing a little to the
  right as if talking to someone: a big bushy beard, a rounded steel
  mining helmet with a lamp on the front, bright eyes under bushy brows,
  sturdy work clothes with suspenders, a cheerful knowing expression,
  clean bold shapes with a crisp dark outline, smooth flat shading in a
  few colors, light from the upper left, on a plain flat pure green
  background". Other dwarves, a schoolmaster or a general, are to be the
  same dwarf in other clothes, each a talk of its own.
- The bubble is a comic speech bubble in 4 colors: near-black ink, cream
  paper, and a darker cream along the inside of its foot. Its corners are
  rounded, its outline a pixel wide, and its tail reaches out of its left
  side, low down, to tuck under his beard. Its corners, edges and tail
  are drawn by hand in `art/talk.py`.
- His lines are the panels' font in ink, a blank row of cells between
  them, in capitals: the font has `, ' !` for the dwarves' speech too.
  The bubble is as wide as the longest line, and as wide again as the
  last line needs for the OK, with a cell clear all round the OK for the
  cursor.

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
| main | the ball |
| bricks | one per color: the brick, its cracks and chunks, and its nuggets |
| fx | the smoke, and the old energy bar of the upgrade screen's picture |
| logo | the title logo |
| sled | the sleds, their jets and flames, the machine, the digits, and the coin |
| texture | the texture behind the playfield, its first 4 colors, loaded with each curtain set |
| curtain | the curtain set of the level, loaded with it |
| shade | the sled row at half, for the machine behind the ball and a dim sled |
| holo | the holographic cursor of the upgrade screen and the menus, whose colors shimmer |
| liquid | the fuel in the energy gauge |
| brass | the gauge's fittings |
| glass | the curtain row through the gauge's glass, and its outline and glint, loaded with each curtain set |

The upgrade panels have a palette of their own, 256 colors, outside these rows, since they are a tile layer, and so do the menus, 16 colors. Each frame set brings its own 16 colors, and the same darkened for its braces, with its pieces. Each talk brings its dwarf's 16 colors and its bubble's 4.

A jet's nozzle and its flame are one sprite, so the flames share the sled
row. Every curtain set brings its own palette into the one curtain row,
and the glass row from it. That is 11 rows and the 5 brick colors, so 16
rows are left.

## Sizes

| Art | Size |
| --- | --- |
| brick | 24x8, 2 bits a pixel |
| cracks | 6 sets of 10, 16x8, 2 bits a pixel, as many across a brick as fit |
| chunks | 16, 8x8, 2 bits a pixel |
| nugget | 8x8 as it flies, and 10 across in a 12x12 sprite by its count |
| coin | 10 across in a 12x12 sprite, by its count |
| ball | 8x8, and 10 across in a 12x12 sprite by its count |
| digit | 8x12 sprite, a 6x8 digit with its outline |
| texture | 320x240 at 2 bits a pixel |
| post | 20 wide, up to 20 of it showing, in pieces 48 tall |
| cap beam | 16 tall, in pieces 48 wide, and a cap 20x16 over each post |
| brace | 32x32 |
| machine | 24x40 |
| sled | the widths of `TUNE_WIDTHS`, up to 64, rounded up to 4 for the sprite; 8 tall, then its two tilts, 24 tall each |
| jet | 7 frames, 8x12: the nozzle alone, 3 flames, 3 swiveled flames |
| smoke | 3 frames, 8x8 |
| energy gauge | 16 wide, the screen tall: the fittings 16x20, the glass 12x200 in 4 sprites, made for each level, the fuel in runs of 12x16 under its surface, and a bubble and its drop, 4x4 each; 1,728 bytes of a level's art |
| logo | 3 pieces, 64x64, as one 192x64 image |
| curtains | 100x240 each, cut from a 256x240 curtain set |
| cursor | 4 corners, 12x12, one image turned |
| dwarf | 80x80, in up to 3 sprites |
| speech bubble | up to 28x10 cells of 8x8, the tail's column with them |

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
3. Pass references: whole images from `ref/`, as they are, never cut
   down: `ref/rock-crop.png` for stone, `ref/sled-kit.png` for
   industrial, and the others of [The Reference Images](#the-reference-images)
   for what they show. Pass them as RGB PNGs: the API refused the indexed
   `art/logo.png`.
4. Reduce the colors to 15 with Retro Diffusion's `color_reducer`, which
   is free, or map them onto a row with its `palette_converter`.
5. Convert it with `art/rd2png.py`:

   ```bash
   python3 art/rd2png.py piece.png art/piece.png --palette-out row.png
   python3 art/rd2png.py piece.png art/piece.png --palette art/palettes.png --row 8
   ```

   The first writes the colors as a palette row, to add to
   `art/palettes.png`. The second puts a piece on a row that is already
   there.
6. Build the game, and judge the art in the emulator, in front of the
   curtains and the texture, not as a loose image.

The blocks of the looks:

- **Stone:** "rough matte quarried stone, chipped edges, dark outline,
  light from the upper left"
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
| `ref/panel-frame.png` | Frame 1, the upgrade panel's frame as Retro Diffusion made it: `rd_pro__default`, 154x138, with a 64x64 crop of a gauge frame from `ui-kit.png`: "A single heavy mechanical display panel seen straight on, filling the whole image: a thick frame of dark graphite gunmetal steel around all four edges, the frame about a tenth of the panel's width, built from bolted steel plates with seams and rivets, a different mechanical bracket or clamp at each corner, a thin bright bevel along the inner edge, worn edges but clean and well maintained, no yellow, no hazard stripes, no rust, the inside one plain flat dark blue-grey plate with nothing on it, slightly futuristic heavy machinery, light from the upper left". Chosen for its simplicity. |
| `ref/old-logo-qu.png` | 64x64 of the old logo's QU: fine, flecked rock at a small scale. The reference for the curtain sets, and the one that made the first. |
| `ref/rock-crop.png` | 64x64 of the rock of the first curtain set: how stone is drawn. A reference for a stone piece, such as the logo. Not for a curtain set: it is zoomed in, so the rock comes out too big. |
| `ref/logo-stone.png` | The logo as Retro Diffusion made it, before `art/logo.py`: `rd_pro__typography`, 192x64, with `rock-crop.png` and `old-logo-qu.png` as references: "\"QUARRY\" in big bold blocky capital letters, carefully carved from solid stone by a master stonemason: clean even letterforms with crisp chiseled bevels and flat faces, every letter whole and unbroken, only a few small natural chips and fine hairline marks, all the letters the same warm weathered sandstone with subtle flecks like the reference rock, cool blue-grey stone only in the shadowed bevels, a dark outline and a dark shadow under the letters, light from the upper left, on a plain white background". One of three, and the one with moss, which `art/logo.py` turns to rock; the others were plainer, or cracked with stray dots. |
| `ref/stone-wall.png` | The organic shapes of the curtains, and the warm sandstone turning to cool granite. It is too bright as it is. |
| `ref/ore-blocks.png` | Matte ore rock and the pairing of each brick with its nugget. Eight candidate ores: limestone, gold-flecked sandstone, malachite in granite, iron ore, coal, silver in slate, rose quartz, and amber in basalt. The bricks became plain colors instead. |
| `ref/sled-kit.png` | The colors, the chevrons, the bolts, and the thrusters. Keep the scuffs and leave out the rust specks. Its tops are not flat: the new sled has the flat, overhanging top plate of [The Sled](#the-sled). |
| `ref/ui-kit.png` | Graphite panels with yellow trim, gauges, and meters. Its vertical meter was the start for the energy gauge. |
| `ref/oracle.png`, `ref/oracle-cursor.png` | The Oracle, a design for the energy gauge, parked, drawn to the pixel as a layout for a model to make finer, not as final art: the scale with its pips and rack, and the cursor at 70%, 33x23, with its sight glass, the chevron notch, the coloured chevron, and the gear. `oracle-cursor.png` is the cursor on level 1, the cave wall showing through its glass. |
| `ref/frame-B2.png`, `ref/frame-B3.png` | Concepts for the playfield's frame: lattice towers of angle iron with X bracing, a zigzag truss beam, bolted gussets. Gray steel, see-through. |
| `ref/frame-C1.png`, `ref/frame-C3.png` | Concepts for the frame: riveted I-beam columns, a riveted plate girder, gusset plates in the corners, in the panels' graphite steel. |
| `ref/frame-D1.png`, `ref/frame-D3.png`, `ref/frame-D4.png` | Concepts for the frame: a mine shaft frame of plain steel posts, a crossbeam and knee braces. D1 drew a whole mine around it; only its frame counts. A first frame set redrawn from D3 at the game's scale came out muddy, its edges noise, and was dropped. |

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
- `frame-B2.png` and `frame-B3.png`, two of four, `rd_pro__default`,
  256x240: "Seen straight on from the front, a sturdy steel lattice frame
  inside a dark quarry pit: a tall narrow lattice tower of grey steel
  angle iron on the far left edge and another on the far right edge, each
  running the full height of the image and about a sixteenth of its
  width, with criss-cross bracing between their two chords, joined across
  the very top by a lattice truss girder with a zigzag web, bolted gusset
  plates at the joints, a short diagonal brace in each top corner, dark
  gunmetal grey steel, worn but well maintained, the inner edges straight
  and clean, no yellow, no hazard stripes, the whole middle an empty flat
  dark space, light from the upper left"
- `frame-C1.png` and `frame-C3.png`, the same, with a 64x64 corner of
  `panel-frame.png` as a reference: "Seen straight on from the front, a
  heavy riveted steel frame inside a dark quarry pit: a tall riveted
  I-beam column on the far left edge and another on the far right edge,
  each running the full height of the image and about a sixteenth of its
  width, joined across the very top by a heavy riveted plate girder, big
  riveted gusset plates at the two top corners, dark graphite gunmetal
  steel like the reference with seams, rivets and bolts, worn edges but
  clean and well maintained, a thin bright bevel along the inner edges,
  no yellow, no hazard stripes, the whole middle an empty flat dark space,
  light from the upper left"
- `frame-D1.png`, `frame-D3.png` and `frame-D4.png`, `rd_pro__platformer`,
  256x240: "Seen straight on, an industrial steel mine shaft frame inside
  a dark quarry: two tall steel posts at the far left and right edges
  running the full height of the image, each about a sixteenth of its
  width, joined across the very top by a steel crossbeam, the inside faces
  of both posts and the underside of the crossbeam lined with thick dark
  rubber bumper rails held on by bolts, cool grey steel, sturdy and worn
  but well maintained, a short diagonal brace in each top corner, no
  yellow, no hazard stripes, the whole middle an empty flat dark space,
  light from the upper left"
- `art/frames/frame-1.png`, `rd_pro__default`, 128x120, the last of four,
  with no reference: "Seen straight on, a clean new steel girder frame: a
  riveted steel I-beam column down the far left edge and another down the
  far right edge, each an eighth of the image's width, joined across the
  very top by a riveted steel I-beam as tall as the columns are wide, each
  I-beam with a bright flange along both of its edges and one neat row of
  evenly spaced round rivets down its middle, a small riveted gusset plate
  in each top corner, cool grey steel with a crisp dark outline around
  every piece, smooth flat shading, no scratches, no dents, no rust, no
  damage, brand new and well maintained, light from the upper left, the
  whole middle a plain flat black space". At this size it drew the
  columns 18 wide, as it would a frame at the game's scale. Redrawing a
  concept smaller with it as a reference goes muddy: a reference at half
  size passes its noise on, and one of only a corner gets a close-up of
  the beam.
- Set 2's truss, `rd_pro__default`, 128x120, the first of four, with no
  reference, "Seen straight on, a heavy-duty open steel truss frame like
  construction scaffolding: an open lattice tower down the far left edge
  and another down the far right edge, each an eighth of the image's
  width, two square steel tube chords with X-shaped cross bracing bars
  welded between them in square cells so you can see right through,
  joined across the very top by a matching open truss beam with X
  bracing, as tall as the towers are wide, welded gusset plates where they
  meet, grey steel with a crisp dark outline around every bar, smooth flat
  shading, used but well maintained, no rust, no cracks, no damage, light
  from the upper left, on a plain flat pure green background that shows
  through every gap and fills the whole middle", was the look chosen. Its
  towers came out 25 wide. The same prompt, with each tower a fifth of the
  image's width, drew towers 19 wide at 80x76
  but with uneven bays, at 64 and 68 the bracing turned to mush, and
  Retro Diffusion would not draw strips 16 wide to repeat. So the truss
  is drawn by hand in its look, with only the gusset of the 80x76 take.
- `ui-kit.png`, `rd_pro__ui_panel`, 256x256: "Control panel parts for
  heavy modern mining machinery: riveted graphite steel panels with
  safety-yellow trim, chunky industrial push buttons and toggle switches,
  a round analog pressure gauge, a vertical segmented energy meter, hazard
  stripe bars, worn edges and scuffed paint but clean and well maintained,
  built for hard daily work"
