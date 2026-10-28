#include "shop.h"
#include "bricks.h"
#include "cursor.h"
#include "debug.h"
#include "input.h"
#include "machines.h"
#include "menu.h"
#include "nuggets.h"
#include "paddle.h"
#include "save.h"
#include "scene.h"
#include "sfx.h"
#include "talk.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"
#include <carts.h>
#include <panels.h>
#include <string.h>

/* The upgrade screen, a working mock with stand-in art. Panels hang from
   a rail across the top, one for each upgrade, and slide along it, so the
   one picked is always in the middle, lit, with the others dim to its
   sides. The levels are a train of mine carts
   along the bottom, which slides the same way. Up and down move the
   holographic cursor between the panels and the carts, and left and right
   move the pick, repeating while held. The button buys the upgrade picked,
   again and again while held, or asks to begin the level picked. Esc asks to go back to the title. A level newly open is
   still locked when the screen opens: the padlock on its cart shakes and
   breaks, and its number lights.

   The panels are 8-bit tiles on plane 1, and the carts 4-bit tiles on its
   scanlines below them, each sliding on its own, and the panels' pictures,
   the trolleys their hangers ride the rail on, and the carts' padlocks are
   plane 2 sprites that move with them. The rail is in the backdrop. Only
   the panels' contents dim: the frames stay lit. The counts down the left stay in front of them.
   shop_step() works out where everything goes, and shop_draw() moves it
   there at the start of the next frame, so nothing moves while the frame
   is drawn. */

#define SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))

/* Each panel has PANEL_SPRITES sprites: its picture, then an icon for
   each of up to 4 currencies of its cost, then the trolley over each of
   its hangers, which rides the rail. The locks are on plane 1, in the
   actors' place: the two halves of the lock that breaks, and the padlocks
   of the carts. The cart picked is open and in the middle, so the locked
   ones are all to its right, and no more than LOCKS of them show. */
#define PANEL_SPRITES (PICTURE_SPRITES + 4 + PANEL_HANGERS)
#define PICTURE_SPRITES 4
#define TROLLEY_SPRITES (PICTURE_SPRITES + 4) /* a panel's first trolley */
#define PANEL_SPRITE(p, i) SPRITE((p) * PANEL_SPRITES + (i))
#define HALF_SPRITE(i) (XRAM_HALF_SPRITES + (i) * sizeof(mode5_csprite_t))
#define LOCK_SPRITE(i) (XRAM_LOCK_SPRITES + (i) * sizeof(mode5_csprite_t))

_Static_assert(PANELS * PANEL_SPRITES <= MENU_SPRITES, "MENU_SPRITES is too few.");

/* The unlock of a level newly open, on the cart beside the level just
   cleared, which is picked: a wait, the lock shaking harder and harder,
   then it breaks, and its halves fly apart and fall away. Then the new
   level is picked, with a chime, and the train slides over to it. The
   halves' speeds are in 1/16 px a step. */
#define UNLOCK_WAIT 20
#define UNLOCK_SHAKE 60
#define UNLOCK_FALL 45
#define HALF_DX 24
#define HALF_DY -40
#define HALF_GRAVITY 4

/* Where the panels are. The one picked is centered, PANEL_COLS cells
   wide, and the others are side by side with it. A frame is
   PANEL_BORDER cells thick all around, which leaves PANEL_INSIDE cells
   across inside. The rows of the panel cells: the hangers, the top of the
   frame, the picture, the title, the pips, what the next rank does, and
   two lines of cost. Each panel's frame is as tall as art/panels.py makes
   it. */
#define PANEL_LEFT ((SCREEN_W - PANEL_COLS * 8) / 2)
#define PANEL_STEP (PANEL_PITCH * 8)
#define PANEL_BORDER 2
#define PANEL_INSIDE (PANEL_COLS - 2 * PANEL_BORDER)
#define TOP_ROW 1
#define PICTURE_ROW 3 /* 6 rows, 48 px */
#define PICTURE_H 48
#define TITLE_ROW 9
#define PIPS_ROW 10
#define EFFECT_ROW 12
#define COST_ROW 14
static const uint8_t panel_heights[PANELS] = PANEL_HEIGHTS; /* the rows of each frame */
static const uint8_t hanger_x[PANEL_HANGERS] = PANEL_HANGER_X;  /* from a panel's left */

_Static_assert(PANEL_LAYOUTS == PANELS, "art/panels.py needs a layout for each panel.");

/* The first panels are the upgrades; the rest are stand-ins. */
static const char *const panel_titles[PANELS] = {"WIDER SLED", "FASTER SLED", "MORE ENERGY",
                                                 "SPECIAL BRICKS"};

/* The levels are a train of mine carts along the bottom, the one picked
   in the middle, its number lit. A cart is 4 cells across, with its
   coupling after it: a heap of ore for a level cleared, the rim, the body
   with the number plate in its middle two cells, and the wheels, as
   art/carts.py lays them out. Its top two rows come with the heap and
   without. The track under them is in the backdrop. */
#define CART_W 32
#define CART_STEP (CART_COLS * 8)
#define CART_LEFT ((SCREEN_W - CART_W) / 2)

_Static_assert(LEVELS <= CARTS_MAX, "CARTS_MAX in xram.h is too few for the levels.");
_Static_assert(CART_TILES <= CART_TILES_MAX, "CART_TILES_MAX in xram.h is too few.");

/* What the cursor is on, as shop_open() takes it. */
#define ON_RAIL SHOP_ON_UPGRADES
#define ON_LEVELS SHOP_ON_LEVELS

/* What is being asked, if anything. */
#define ASK_NONE 0
#define ASK_BEGIN 1
#define ASK_TITLE 2

static const char *const yes_no[] = {"YES", "NO"};
static char begin_title[] = "BEGIN LEVEL 00?";
static const menu_t begin_menu = {20, 11, BOX_TAPE, begin_title, yes_no, 2};
static const menu_t title_menu = {20, 11, BOX_TAPE, "RETURN TO TITLE?", yes_no, 2};

static uint8_t panel_picked; /* the panel in the middle */
static uint8_t cursor_on;     /* ON_RAIL or ON_LEVELS */
static uint8_t asking;
static int16_t panel_scroll; /* how far the panels have slid, in px */
static int16_t cart_scroll;  /* how far the carts have slid, in px */
static int16_t drawn_cart_scroll;
static uint8_t locks_dirty; /* the padlocks to show have changed */
static uint8_t panel_lit[PANELS]; /* whether each panel's contents are lit */

/* What shop_draw() has to do: draw the pictures again, from scratch, or
   move them and the panels to scroll. */
static uint8_t pictures_dirty;
static int16_t drawn_scroll;
static int16_t picture_x[PANELS * PANEL_SPRITES]; /* from the panel's left */
static uint8_t picture_shown[PANELS * PANEL_SPRITES];

/* The pictures of the panels near the one picked are in slots of XRAM,
   panel p's in slot p % PICTURE_SLOTS: the three that show, and the next
   one the way the rail last moved, which loads before it slides into
   view. Those are four panels side by side, so each has a slot. */
static uint8_t slot_panel[PICTURE_SLOTS]; /* whose picture each slot holds, or PANELS */
static uint8_t slot_rank[PICTURE_SLOTS]; /* and at which rank */
static int8_t heading = 1; /* the way the rail last moved: 1 to the panels on the right, -1 to the left */

_Static_assert(PICTURE_SLOTS >= 4, "A slot for each of the four panels near the one picked.");

static uint8_t unlocking; /* the level being unlocked, or 0 */
static uint8_t unlock_steps;
static int16_t half_x[2], half_y[2], half_dx[2], half_dy[2]; /* in 1/16 px, from the cart */
static uint8_t lock_dirty;

static char *put_text(char *at, const char *s)
{
    while (*s)
        *at++ = *s++;
    return at;
}

static char *put_number(char *at, uint16_t n)
{
    char digits[5];
    uint8_t len = 0;

    do
    {
        digits[len++] = '0' + n % 10;
        n /= 10;
    } while (n);
    while (len)
        *at++ = digits[--len];
    return at;
}

/* The lit tile of a character, from the panels' font; the plate for one
   it doesn't have. */
static uint8_t glyph(char c)
{
    const char *at = c ? strchr(PANEL_FONT, c) : 0;

    return PANEL_TILE_GLYPH + (at ? at - PANEL_FONT : 0);
}

/* A row inside panel p: the plate, with n tiles of contents centered on it,
   lit or dim as the panel is. */
static void row_draw(uint8_t p, uint8_t row, const uint8_t *tiles, uint8_t n)
{
    uint8_t line[PANEL_INSIDE], first = (PANEL_INSIDE - n) / 2, i;
    uint8_t dim = panel_lit[p] ? 0 : PANEL_TILE_DIM;

    for (i = 0; i < PANEL_INSIDE; i++)
        line[i] = (i >= first && i < first + n ? tiles[i - first] : PANEL_TILE_GLYPH) + dim;
    xram0_write(XRAM_PANELS + row * PANEL_MAP_COLS + p * PANEL_PITCH + PANEL_BORDER, line, sizeof line);
}

/* Text centered on a row inside panel p. */
static void text_draw(uint8_t p, uint8_t row, const char *s)
{
    uint8_t tiles[PANEL_INSIDE], n = 0;

    while (s[n] && n < PANEL_INSIDE)
    {
        tiles[n] = glyph(s[n]);
        n++;
    }
    row_draw(p, row, tiles, n);
}

/* Lights or dims the display of panel p: every tile of its contents, and
   of the inner ring of its frame, swaps for its lit or dim copy. The outer
   ring of the frame stays as it is. */
static void panel_light(uint8_t p, uint8_t on)
{
    uint8_t line[PANEL_COLS - 2], row, i;

    panel_lit[p] = on;
    for (row = TOP_ROW + 1; row < TOP_ROW + panel_heights[p] - 1; row++)
    {
        unsigned at = XRAM_PANELS + row * PANEL_MAP_COLS + p * PANEL_PITCH + 1;
        xram0_read(line, at, sizeof line);
        for (i = 0; i < sizeof line; i++)
        {
            uint8_t t = line[i];
            if (on && t > PANEL_TILE_DIM && t < PANEL_TILE_FRAMES)
                line[i] = t - PANEL_TILE_DIM;
            else if (!on && t && t <= PANEL_TILE_DIM)
                line[i] = t + PANEL_TILE_DIM;
        }
        xram0_write(at, line, sizeof line);
    }
}

static uint8_t lit(uint8_t p)
{
    return panel_lit[p];
}

static uint8_t can_buy(uint8_t u)
{
    uint16_t cost = upgrades_cost(u);

    return cost && nuggets[BRICK_WHITE] >= cost;
}

/* What the next rank does, as the numbers now and then, with the units. */
static void effect_draw(uint8_t p)
{
    char text[PANEL_INSIDE + 1];
    char *at = text;
    uint8_t rank = upgrade_ranks[p], max = rank >= upgrades_max(p);
    const char *units = p == UPGRADE_WIDTH ? " PX" : " PX/S";
    /* A speed is in 1/256 px a step, at 60 steps a second. */
#define VALUE(l) (p == UPGRADE_WIDTH ? upgrades_width_at(l) : (uint16_t)(upgrades_speed_at(l) * 60u / 256))

    at = put_number(at, VALUE(rank));
    if (!max)
    {
        at = put_text(at, " \x10 ");
        at = put_number(at, VALUE(rank + 1));
    }
    at = put_text(at, units);
    *at = 0;
    text_draw(p, EFFECT_ROW, text);
#undef VALUE
}

/* A panel's contents: its title, a pip for each rank, filled for each
   bought, what the next rank does, and its cost, in short digits while it
   can't be paid, or MAX. A stand-in says it is coming. The frame is the
   map's, as art/panels.py made it. */
static void panel_draw(uint8_t p)
{
    uint8_t tiles[PANEL_INSIDE], i;

    text_draw(p, TITLE_ROW, panel_titles[p]);
    if (p >= UPGRADES)
    {
        text_draw(p, PIPS_ROW + 1, "COMING SOON");
        return;
    }
    {
        uint8_t max = upgrades_max(p), rank = upgrade_ranks[p];
        for (i = 0; i < max; i++)
            tiles[i] = i < rank ? PANEL_TILE_PIP_ON : PANEL_TILE_PIP_OFF;
        row_draw(p, PIPS_ROW, tiles, max);
    }
    effect_draw(p);
    if (upgrades_cost(p))
    {
        char number[6];
        uint8_t n = put_number(number, upgrades_cost(p)) - number;
        /* The cost's icon is a sprite in the cell before it. */
        tiles[0] = tiles[1] = PANEL_TILE_GLYPH;
        for (i = 0; i < n; i++)
            tiles[2 + i] = can_buy(p) ? glyph(number[i]) : PANEL_TILE_SHORT + number[i] - '0';
        row_draw(p, COST_ROW, tiles, 2 + n);
    }
    else
        text_draw(p, COST_ROW, "MAX");
}

/* The left edge of panel p, as it slides. */
static int16_t panel_x(uint8_t p)
{
    return PANEL_LEFT + p * PANEL_STEP - panel_scroll;
}

/* The image of a trolley at x, its wheels turned for where it is. */
static unsigned trolley_image(int16_t x)
{
    return XRAM_BACKDROP_SPRITES + BACKDROP_TROLLEY_AT +
           (x / 2 & (BACKDROP_TROLLEY_FRAMES - 1)) * (BACKDROP_TROLLEY_W * BACKDROP_TROLLEY_H / 2);
}

/* Whether panel p's picture is in its slot. The width and speed panels'
   pictures are the sled of the width bought. */
static uint8_t picture_ready(uint8_t p)
{
    uint8_t slot = p % PICTURE_SLOTS;

    return slot_panel[slot] == p && slot_rank[slot] == upgrade_ranks[UPGRADE_WIDTH];
}

/* Loads the pictures of the panels near the one picked that aren't in
   their slots yet. */
static void pictures_load(void)
{
    int8_t first = panel_picked - (heading < 0 ? 2 : 1);
    uint8_t p = first > 0 ? first : 0;

    for (; p <= first + 3 && p < PANELS; p++)
        if ((p == UPGRADE_WIDTH || p == UPGRADE_SPEED) && !picture_ready(p))
        {
            uint8_t slot = p % PICTURE_SLOTS;
            scene_picture_sled(slot, upgrade_ranks[UPGRADE_WIDTH]);
            slot_panel[slot] = p;
            slot_rank[slot] = upgrade_ranks[UPGRADE_WIDTH];
        }
}

/* A panel's picture and cost icons, where it is now. The pictures are
   stand-ins, doubled: the sled for width, the sled with its flames lit
   for speed, the energy gauge, and a brick. */
static void pictures_draw(uint8_t p)
{
    int16_t x = panel_x(p), top = PANEL_Y + PICTURE_ROW * 8;
    uint8_t dim = lit(p) ? 0 : SLED_DIM, i;

    for (i = 0; i < PANEL_SPRITES; i++)
        sprite_hide(PANEL_SPRITE(p, i));
    for (i = 0; i < PANEL_HANGERS; i++)
    {
        int16_t tx = x + hanger_x[i] - BACKDROP_TROLLEY_W / 2;
        sprite_set(PANEL_SPRITE(p, TROLLEY_SPRITES + i), trolley_image(tx), XRAM_BAND_PALETTE(top),
                   MODE5_SIZE(BACKDROP_TROLLEY_W, BACKDROP_TROLLEY_H));
        sprite_move(PANEL_SPRITE(p, TROLLEY_SPRITES + i), tx, BACKDROP_TROLLEY_Y);
    }
    if (p == UPGRADE_WIDTH || p == UPGRADE_SPEED)
    {
        uint8_t rank = upgrade_ranks[UPGRADE_WIDTH];
        uint8_t w = upgrades_width_at(rank) * 2;
        if (picture_ready(p))
            sled_show(PANEL_SPRITE(p, 0), PICTURE_SPRITES, x + (PANEL_COLS * 8 - w) / 2, top + 7, rank,
                      SLED_DOUBLE | dim | (p == UPGRADE_SPEED ? SLED_FLAMES : 0), XRAM_PICTURE(p % PICTURE_SLOTS));
    }
    else if (p == 2)
    {
        static const uint8_t pieces[] = {ENERGY_TOP, ENERGY_FULL, ENERGY_BOTTOM};
        for (i = 0; i < sizeof pieces; i++)
        {
            sprite_set(PANEL_SPRITE(p, i), XRAM_ENERGY_IMAGES + pieces[i] * sizeof(energy_image_t),
                       XRAM_PALETTE_FX, MODE5_SIZE(8, 8));
            sprite_attributes(PANEL_SPRITE(p, i), MODE5_HDOUBLE | MODE5_VDOUBLE);
            sprite_move(PANEL_SPRITE(p, i), x + PANEL_COLS * 4 - 8, top + i * 16);
        }
    }
    else
    {
        sprite_set(PANEL_SPRITE(p, 0), XRAM_BRICK_IMAGE, XRAM_PALETTE_BRICK(BRICK_WHITE),
                   MODE5_SIZE(BRICK_W, BRICK_H));
        sprite_attributes(PANEL_SPRITE(p, 0), MODE5_HDOUBLE | MODE5_VDOUBLE);
        sprite_move(PANEL_SPRITE(p, 0), x + PANEL_COLS * 4 - BRICK_W, top + (PICTURE_H - 2 * BRICK_H) / 2);
    }
    if (p < UPGRADES && upgrades_cost(p) && !talk_busy())
    {
        /* In the first cell of the cost's row, as panel_draw() centers it,
           but not while a dwarf talks, as it would show over his bubble. */
        char number[6];
        uint8_t first = (PANEL_INSIDE - 2 - (put_number(number, upgrades_cost(p)) - number)) / 2;
        sprite_set(PANEL_SPRITE(p, PICTURE_SPRITES), XRAM_NUGGET_IMAGE, XRAM_PALETTE_BRICK(BRICK_WHITE),
                   MODE5_SIZE(8, 8));
        sprite_move(PANEL_SPRITE(p, PICTURE_SPRITES), x + (PANEL_BORDER + first) * 8, PANEL_Y + COST_ROW * 8);
    }
}

/* Every panel's pictures, drawn from scratch where the panels are now,
   and where each sprite is in its panel, to move it with the panel. */
static void pictures_place(void)
{
    uint8_t p, i;

    xram0_poke16(XRAM_PANEL_CONFIG + offsetof(mode2_config_t, x_pos_px), PANEL_LEFT - panel_scroll);
    for (p = 0; p < PANELS; p++)
    {
        pictures_draw(p);
        for (i = 0; i < PANEL_SPRITES; i++)
        {
            int16_t pos[2];
            uint8_t n = p * PANEL_SPRITES + i;
            xram0_read(pos, PANEL_SPRITE(p, i), sizeof pos);
            picture_x[n] = pos[0] - panel_x(p);
            picture_shown[n] = pos[1] != SPRITE_HIDDEN_Y;
        }
    }
    drawn_scroll = panel_scroll;
}

/* The panels, and every picture shown on them, moved to scroll. */
static void pictures_move(void)
{
    uint8_t p, i;

    xram0_poke16(XRAM_PANEL_CONFIG + offsetof(mode2_config_t, x_pos_px), PANEL_LEFT - panel_scroll);
    for (p = 0; p < PANELS; p++)
        for (i = 0; i < PANEL_SPRITES; i++)
            if (picture_shown[p * PANEL_SPRITES + i])
            {
                int16_t x = panel_x(p) + picture_x[p * PANEL_SPRITES + i];
                xram0_poke16(PANEL_SPRITE(p, i) + offsetof(mode5_csprite_t, x_pos_px), x);
                if (i >= TROLLEY_SPRITES)
                    xram0_poke16(PANEL_SPRITE(p, i) + offsetof(mode5_csprite_t, xram_sprite_ptr), trolley_image(x));
            }
    drawn_scroll = panel_scroll;
}

/* The levels shown open: all that are, but one being unlocked until its
   lock breaks. */
static uint8_t shown_open(void)
{
    return unlocking > levels_shown ? unlocking - 1 : save_levels_open();
}

/* The left edge of level s's cart, as the train slides. */
static int16_t cart_x(uint8_t s)
{
    return CART_LEFT + (s - 1) * CART_STEP - cart_scroll;
}

/* Every level's cart: a heap on each one cleared, its number on its plate,
   lit on the one picked, or a blank plate on each that isn't open yet,
   for its padlock. */
static void carts_draw(void)
{
    uint8_t open = shown_open(), s, r, c;

    for (s = 1; s <= LEVELS; s++)
    {
        uint8_t cells[CART_ROWS][CART_COLS], t = CART_TILE_BODY;
        for (r = 0; r < CART_ROWS; r++)
            for (c = 0; c < CART_COLS; c++)
                cells[r][c] = 0;
        for (r = 1; r < CART_ROWS; r++)
            for (c = 0; c < 4; c++)
                if (r != CART_PLATE_ROW || c == 0 || c == 3)
                    cells[r][c] = t++;
        if (s <= levels_cleared && s <= open)
            for (c = 0; c < 4; c++)
            {
                cells[0][c] = CART_TILE_HEAP + c;
                cells[1][c] = CART_TILE_HEAP + 4 + c;
            }
        if (s > open)
        {
            cells[CART_PLATE_ROW][1] = CART_TILE_PLATE;
            cells[CART_PLATE_ROW][2] = CART_TILE_PLATE;
        }
        else
        {
            uint8_t digits = s == level_picked ? CART_TILE_DIGIT : CART_TILE_DIM;
            cells[CART_PLATE_ROW][1] = digits + s / 10;
            cells[CART_PLATE_ROW][2] = digits + s % 10;
        }
        if (s < LEVELS)
            cells[CART_COUPLING_ROW][4] = CART_TILE_COUPLING;
        for (r = 0; r < CART_ROWS; r++)
            xram0_write(XRAM_CART_MAP + r * CART_MAP_COLS + (s - 1) * CART_COLS, cells[r], CART_COLS);
    }
    locks_dirty = 1;
}

/* The carts, slid to cart_scroll, with a padlock on each of the first
   LOCKS locked, but for the one whose lock is breaking. */
static void carts_move(void)
{
    uint8_t s = shown_open() + 1, i;

    if (s == unlocking)
        s++;
    xram0_poke16(XRAM_CART_CONFIG + offsetof(mode2_config_t, x_pos_px), CART_LEFT - cart_scroll);
    for (i = 0; i < LOCKS; i++, s++)
        if (s <= LEVELS)
            sprite_move(LOCK_SPRITE(i), cart_x(s) + CART_LOCK_LEFT, CART_Y + CART_LOCK_TOP);
        else
            sprite_hide(LOCK_SPRITE(i));
    drawn_cart_scroll = cart_scroll;
    locks_dirty = 0;
}

/* Where the cursor goes: around the panel in the middle, or the cart in
   the middle and its heap, if it has one, a few pixels out. While a dwarf
   talks, it stays off, and comes back with shop_resume(). */
static void cursor_aim(void)
{
    if (talk_busy())
        return;
    if (cursor_on == ON_RAIL)
        cursor_place(PANEL_LEFT - 3, PANEL_Y + TOP_ROW * 8 - 3, PANEL_LEFT + PANEL_COLS * 8 + 3,
                     PANEL_Y + (panel_heights[panel_picked] + 1) * 8 + 3);
    else
        cursor_place(CART_LEFT - 3, CART_Y + (level_picked <= levels_cleared ? CART_HEAP_TOP : CART_RIM) - 3,
                     CART_LEFT + CART_W + 3, CART_Y + CART_FOOT + 3);
}

/* Steps a value a quarter of the way to where it is going, at least a
   pixel, so it slides fast and settles slowly. */
static int16_t ease(int16_t now, int16_t to)
{
    int16_t step = (to - now) / 4;

    if (!step)
        step = to > now ? 1 : to < now ? -1 : 0;
    return now + step;
}

/* The lock over the plate of the cart being unlocked, in two halves. */
static void lock_start(void)
{
    uint8_t i;

    for (i = 0; i < 2; i++)
    {
        sprite_set(HALF_SPRITE(i), XRAM_LOCK_HALVES + i * sizeof(half_lock_image_t), XRAM_LOCK_PALETTE,
                   MODE5_SIZE(8, 16));
        half_x[i] = (CART_LOCK_LEFT + i * 8) * 16;
        half_y[i] = (CART_Y + CART_LOCK_TOP) * 16;
        half_dx[i] = i ? HALF_DX : -HALF_DX;
        half_dy[i] = HALF_DY;
    }
    unlock_steps = 0;
    lock_dirty = 1;
}

static void lock_move(void)
{
    int8_t shake = 0;
    uint8_t i;

    if (unlock_steps >= UNLOCK_WAIT && unlock_steps < UNLOCK_WAIT + UNLOCK_SHAKE)
    {
        uint8_t amount = 1 + (unlock_steps - UNLOCK_WAIT) * 3 / UNLOCK_SHAKE;
        shake = unlock_steps / 2 & 1 ? amount : -amount;
    }
    for (i = 0; i < 2; i++)
        sprite_move(HALF_SPRITE(i), cart_x(unlocking) + half_x[i] / 16 + shake, half_y[i] / 16);
}

/* Ends an unlock at once: the level shows open, and is picked. */
static void unlock_finish(void)
{
    sprite_hide(HALF_SPRITE(0));
    sprite_hide(HALF_SPRITE(1));
    levels_shown = level_picked = unlocking;
    unlocking = 0;
    lock_dirty = 0;
    carts_draw();
    cursor_aim();
}

/* A step of the unlock: the shake rattles, the break snaps and shows the
   level's number, and the halves fall. At the end the level is picked, with
   a chime, and the game saves. */
static void unlock_step(void)
{
    uint8_t t = unlock_steps++, i;

    lock_dirty = 1;
    if (t >= UNLOCK_WAIT && t < UNLOCK_WAIT + UNLOCK_SHAKE && (t - UNLOCK_WAIT) % 6 == 0)
        sfx_play(SFX_RATTLE, cart_x(unlocking));
    if (t == UNLOCK_WAIT + UNLOCK_SHAKE)
    {
        sfx_play(SFX_SNAP, cart_x(unlocking));
        levels_shown = unlocking;
        carts_draw();
    }
    if (t > UNLOCK_WAIT + UNLOCK_SHAKE)
        for (i = 0; i < 2; i++)
        {
            half_x[i] += half_dx[i];
            half_y[i] += half_dy[i];
            half_dy[i] += HALF_GRAVITY;
        }
    if (t == UNLOCK_WAIT + UNLOCK_SHAKE + UNLOCK_FALL)
    {
        sfx_play(SFX_UNLOCK, cart_x(unlocking));
        unlock_finish();
        save_write();
        DEBUG_LOG("unlocked %u\n", levels_shown);
    }
}

#ifndef NDEBUG
/* The cheats of a debug build, with Shift and right or left, which repeat
   while held. On the rail, they raise or lower the upgrade picked, for
   nothing. On the levels, they open the next level, with its unlock, or
   lock the last one open again. A cheat cuts short an unlock under way. */
static void cheats_step(void)
{
    uint8_t up = shift_pressed & SHIFT_RIGHT, i;

    if (!(shift_pressed & (SHIFT_RIGHT | SHIFT_LEFT)) || asking)
        return;
    if (unlocking)
        unlock_finish();
    if (cursor_on == ON_RAIL)
    {
        uint8_t u = panel_picked;
        if (u >= UPGRADES || (up ? upgrade_ranks[u] >= upgrades_max(u) : !upgrade_ranks[u]))
            return;
        upgrade_ranks[u] += up ? 1 : -1;
        pictures_load();
        for (i = 0; i < UPGRADES; i++)
            panel_draw(i);
        pictures_dirty = 1;
        DEBUG_LOG("cheat: %s %u\n", u == UPGRADE_WIDTH ? "width" : "speed", upgrade_ranks[u]);
        return;
    }
    if (up && levels_cleared < LEVELS)
    {
        levels_cleared++;
        if (save_levels_open() > levels_shown)
        {
            unlocking = save_levels_open();
            level_picked = unlocking - 1;
            lock_start();
        }
    }
    else if (!up && levels_cleared)
    {
        levels_cleared--;
        if (level_picked > save_levels_open())
            level_picked = save_levels_open();
        if (levels_shown > save_levels_open())
            levels_shown = save_levels_open();
    }
    else
        return;
    carts_draw();
    cursor_aim();
    DEBUG_LOG("cheat: %u levels cleared\n", levels_cleared);
}
#endif

/* The cost icons of the panel in the middle, which would show over a
   question's box. Nothing else reaches it. */
static void icons_hide(void)
{
    uint8_t i;

    for (i = PICTURE_SPRITES; i < TROLLEY_SPRITES; i++)
        sprite_hide(PANEL_SPRITE(panel_picked, i));
}

/* A question over the screen. The cost icons of the panel in the middle
   would show over its box, so they hide until it goes. The cursor slides
   into it, and back out after. */
static void ask(uint8_t what)
{
    if (what == ASK_BEGIN)
    {
        begin_title[12] = level_picked >= 10 ? '0' + level_picked / 10 : '0' + level_picked % 10;
        begin_title[13] = level_picked >= 10 ? '0' + level_picked % 10 : '?';
        begin_title[14] = level_picked >= 10 ? '?' : 0;
    }
    asking = what;
    input_repeat_stop();
    icons_hide();
    menu_open(what == ASK_BEGIN ? &begin_menu : &title_menu, 0, 0, 0);
    DEBUG_LOG("asked %s\n", what == ASK_BEGIN ? "begin" : "title");
}

static void unask(void)
{
    menu_close();
    asking = ASK_NONE;
    pictures_dirty = 1;
    cursor_aim();
}

/* The upgrade screen, its cursor on the rail of panels or the level
   select, as on says. */
void shop_open(uint8_t on)
{
    uint8_t p;

    scene_menu();
    video_hide_sprites();
    cursor_hide();
    input_repeat_stop();
    menu_clear();
    nuggets_start(1);
    cursor_on = on;
    asking = ASK_NONE;
    unlocking = save_levels_open() > levels_shown ? save_levels_open() : 0;
    if (unlocking)
        level_picked = unlocking - 1;
    /* The first unlock has a dwarf say what it means, and the first time
       here another says what the screen is for. */
    if (unlocking == 2)
        talk_once(TALK_UNLOCK);
    talk_once(TALK_UPGRADES);
    panel_scroll = panel_picked * PANEL_STEP;
    cart_scroll = (level_picked - 1) * CART_STEP;
    /* The map comes lit. Every panel dims but the one picked. */
    for (p = 0; p < PANELS; p++)
    {
        panel_lit[p] = 1;
        panel_draw(p);
        if (p != panel_picked)
            panel_light(p, 0);
    }
    for (p = 0; p < PICTURE_SLOTS; p++)
        slot_panel[p] = PANELS;
    pictures_load();
    pictures_place();
    for (p = 0; p < LOCKS; p++)
        sprite_set(LOCK_SPRITE(p), XRAM_LOCK_IMAGE, XRAM_LOCK_PALETTE, MODE5_SIZE(16, 16));
    machines_start();
    carts_draw();
    cursor_aim();
    pictures_dirty = 0;
    carts_move();
    if (unlocking)
        lock_start();
    save_write();
    scene_menu_show(); /* only now, with everything in its place */
    DEBUG_LOG("upgrades\n");
}

/* A step of the upgrade screen while a dwarf talks over it: the machines
   turn, an unlock goes on, and the rail and the train slide where they
   were going, but it takes no input. */
void shop_idle(void)
{
    machines_step();
    if (unlocking)
        unlock_step();
    panel_scroll = ease(panel_scroll, panel_picked * PANEL_STEP);
    cart_scroll = ease(cart_scroll, (level_picked - 1) * CART_STEP);
}

/* The last dwarf has gone, and the cursor comes back. A question a test
   key's dwarf took the place of goes. */
void shop_resume(void)
{
    if (asking)
        unask();
    cursor_aim();
}

/* At the start of a frame: the panels and their pictures move to where
   shop_step() put them, and then the panel picked lights and the one it
   was dims, last, as that takes the longest, so nothing moves while the
   frame is drawn. While a question is up, nothing moves but the cursor. */
void shop_draw(void)
{
    static uint8_t talking;
    uint8_t p;

    machines_draw();
    /* As a dwarf comes, or the last goes, the pictures draw again, so the
       cost icons hide from his bubble, or come back. */
    if (talk_busy() != talking)
    {
        talking = !talking;
        pictures_dirty = 1;
    }
    if (!asking)
    {
        if (pictures_dirty)
            pictures_place();
        else if (panel_scroll != drawn_scroll)
            pictures_move();
        if (cart_scroll != drawn_cart_scroll || locks_dirty)
            carts_move();
        if (lock_dirty)
            lock_move();
        pictures_dirty = lock_dirty = 0;
    }
    for (p = 0; p < PANELS; p++)
        if (panel_lit[p] != (p == panel_picked))
        {
            panel_light(p, p == panel_picked);
            pictures_dirty = 1; /* the pictures light or dim with it, next frame */
        }
}

/* Returns SHOP_BEGIN when the level picked is to begin, SHOP_TITLE to go
   back to the title, and SHOP_STAY until then. */
uint8_t shop_step(void)
{
    uint8_t moved = 0, repeated, i;

    machines_step();
#ifndef NDEBUG
    cheats_step();
#endif
    if (unlocking)
    {
        unlock_step();
        cart_scroll = ease(cart_scroll, (level_picked - 1) * CART_STEP);
        return SHOP_STAY;
    }
    if (asking)
    {
        if (input_pressed & INPUT_PAUSE)
            unask();
        else
            switch (menu_step())
            {
            case 1: /* YES */
                menu_close();
                if (asking == ASK_TITLE)
                {
                    save_write();
                    return SHOP_TITLE;
                }
                return SHOP_BEGIN;
            case 2:
                unask();
                break;
            }
        return SHOP_STAY;
    }
    repeated = input_repeat();
    if (input_pressed & INPUT_PAUSE)
    {
        ask(ASK_TITLE);
        return SHOP_STAY;
    }
    if (input_pressed & INPUT_UP && cursor_on != ON_RAIL)
    {
        cursor_on = ON_RAIL;
        moved = 1;
    }
    else if (input_pressed & INPUT_DOWN && cursor_on != ON_LEVELS)
    {
        cursor_on = ON_LEVELS;
        moved = 1;
    }
    else if (repeated & (INPUT_LEFT | INPUT_RIGHT))
    {
        uint8_t right = repeated & INPUT_RIGHT;
        if (cursor_on == ON_RAIL && (right ? panel_picked + 1 < PANELS : panel_picked > 0))
        {
            panel_picked += right ? 1 : -1;
            heading = right ? 1 : -1;
            pictures_load();
            pictures_dirty = 1;
            moved = 1;
        }
        else if (cursor_on == ON_LEVELS && (right ? level_picked < save_levels_open() : level_picked > 1))
        {
            level_picked += right ? 1 : -1;
            carts_draw();
            moved = 1;
        }
    }
    else if ((cursor_on == ON_RAIL ? repeated : input_pressed) & INPUT_CHOOSE)
    {
        if (cursor_on == ON_LEVELS)
            ask(ASK_BEGIN);
        else if (panel_picked < UPGRADES && upgrades_buy(panel_picked))
        {
            sfx_play(SFX_BUY, SFX_CENTER);
            for (i = 0; i < UPGRADES; i++)
                panel_draw(i);
            nuggets_start(1);
            pictures_load();
            pictures_dirty = 1;
            save_write();
        }
        if (asking)
            return SHOP_STAY;
    }
    if (moved)
    {
        sfx_play(SFX_MOVE, SFX_CENTER);
        cursor_aim();
    }
    panel_scroll = ease(panel_scroll, panel_picked * PANEL_STEP);
    cart_scroll = ease(cart_scroll, (level_picked - 1) * CART_STEP);
    return SHOP_STAY;
}
