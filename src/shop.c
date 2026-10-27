#include "shop.h"
#include "bricks.h"
#include "debug.h"
#include "input.h"
#include "menu.h"
#include "nuggets.h"
#include "paddle.h"
#include "save.h"
#include "scene.h"
#include "sfx.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"
#include <carts.h>
#include <panels.h>
#include <string.h>

/* The upgrade screen, a working mock with stand-in art. Panels hang from
   a rail across the top, one for each upgrade, and slide along it, so the
   one picked is always in the middle, lit, flickering on as it comes,
   with the others dim to its sides. The stages are a train of mine carts
   along the bottom, which slides the same way. Up and down move the
   holographic cursor between the panels and the carts, and left and right
   move the pick. The button buys the upgrade picked, or asks to begin the
   stage picked. Esc asks to go back to the title. A stage newly open is
   still locked when the screen opens: the padlock on its cart shakes and
   breaks, and its number lights.

   The panels are 8-bit tiles on plane 1, and the carts 4-bit tiles on its
   scanlines below them, each sliding on its own, and the panels' pictures
   are plane 2 sprites that move with them. Only the panels' contents dim:
   the frames stay lit. The counts down the left stay in front of them.
   shop_step() works out where everything goes, and shop_draw() moves it
   there at the start of the next frame, so nothing moves while the frame
   is drawn. */

#define SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))

/* Each panel has PANEL_SPRITES sprites: its picture, then an icon for
   each of up to 4 currencies of its cost. The cursor's 4 corners follow,
   then the two halves of a lock. */
#define PANEL_SPRITES 8
#define PICTURE_SPRITES 4
#define PANEL_SPRITE(p, i) SPRITE((p) * PANEL_SPRITES + (i))
#define CURSOR_SPRITE(i) SPRITE(PANELS * PANEL_SPRITES + (i))
#define LOCK_SPRITE(i) SPRITE(PANELS * PANEL_SPRITES + 4 + (i))

_Static_assert(PANELS * PANEL_SPRITES + 4 + 2 <= MENU_SPRITES, "MENU_SPRITES is too few.");

/* The unlock of a stage newly open: a wait, the lock shaking harder and
   harder, then it breaks, and its halves fly apart and fall away. Their
   speeds are in 1/16 px a step. */
#define UNLOCK_WAIT 20
#define UNLOCK_SHAKE 60
#define UNLOCK_FALL 45
#define UNLOCK_CHIME 8 /* steps after it breaks */
#define HALF_DX 24
#define HALF_DY -40
#define HALF_GRAVITY 4

/* Where the panels are. The one picked is centered, PANEL_COLS cells
   wide, and the others are side by side with it. A frame is
   PANEL_BORDER cells thick all around, which leaves PANEL_INSIDE cells
   across inside. The rows of the panel cells: the hangers, the top of the
   frame, the picture, the title, the pips, what the next level does, and
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

_Static_assert(PANEL_LAYOUTS == PANELS, "art/panels.py needs a layout for each panel.");

/* The first panels are the upgrades; the rest are stand-ins. */
static const char *const panel_titles[PANELS] = {"WIDER SLED", "FASTER SLED", "MORE ENERGY",
                                                 "SPECIAL BRICKS"};

/* A panel coming to the middle flickers on, like a fluorescent tube: lit
   or dim each step, then lit. */
static const char flicker[] = "110001000011";

/* The stages are a train of mine carts along the bottom, the one picked
   in the middle, its number lit. A cart is 4 cells across, with its
   coupling after it: a heap of ore for a stage cleared, the rim, the body
   with the number plate in its middle two cells, and the wheels. Its top
   two rows come with the heap and without. The track
   under them is text cells of code page 437, for now. */
#define CART_W 32
#define CART_STEP (CART_COLS * 8)
#define CART_LEFT ((SCREEN_W - CART_W) / 2)
#define CART_TOP 10 /* the rim, under any heap */
#define PLATE_ROW 2
#define TRACK_ROW ((CART_Y + CART_ROWS * 8) / 8)
#define RAIL_ROW 1

_Static_assert(STAGES <= CARTS_MAX, "CARTS_MAX in xram.h is too few for the stages.");
_Static_assert(CART_TILES <= CART_TILES_MAX, "CART_TILES_MAX in xram.h is too few.");

/* What the cursor is on. */
#define ON_RAIL 0
#define ON_STAGES 1

/* What is being asked, if anything. */
#define ASK_NONE 0
#define ASK_BEGIN 1
#define ASK_TITLE 2

static const char *const yes_no[] = {"YES", "NO"};
static char begin_title[] = "BEGIN LEVEL 00?";
static const menu_t begin_menu = {20, 11, BOX_COLOR, begin_title, yes_no, 2};
static const menu_t title_menu = {20, 11, BOX_COLOR, "RETURN TO TITLE?", yes_no, 2};

static uint8_t panel_picked; /* the panel in the middle */
static uint8_t cursor_on;     /* ON_RAIL or ON_STAGES */
static uint8_t asking;
static int16_t panel_scroll; /* how far the panels have slid, in px */
static int16_t cart_scroll;  /* how far the carts have slid, in px */
static int16_t drawn_cart_scroll;
static int16_t cursor[4], cursor_to[4]; /* left, top, right, bottom */
static uint8_t steps;
static uint8_t panel_lit[PANELS]; /* whether each panel's contents are lit */
static uint8_t flicker_steps;     /* into the flicker of the panel picked */

/* What shop_draw() has to do: draw the pictures again, from scratch, or
   move them and the panels to scroll, and move the cursor. */
static uint8_t pictures_dirty;
static uint8_t cursor_dirty;
static int16_t drawn_scroll;
static int16_t picture_x[PANELS * PANEL_SPRITES]; /* from the panel's left */
static uint8_t picture_shown[PANELS * PANEL_SPRITES];

static uint8_t unlocking; /* the stage being unlocked, or 0 */
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

/* Lights or dims the whole inside of panel p: every tile of its contents
   swaps for its lit or dim copy, and the frame stays as it is. */
static void panel_light(uint8_t p, uint8_t on)
{
    uint8_t line[PANEL_INSIDE], row, i;

    panel_lit[p] = on;
    for (row = TOP_ROW + PANEL_BORDER; row <= panel_heights[p] - PANEL_BORDER; row++)
    {
        unsigned at = XRAM_PANELS + row * PANEL_MAP_COLS + p * PANEL_PITCH + PANEL_BORDER;
        xram0_read(line, at, sizeof line);
        for (i = 0; i < PANEL_INSIDE; i++)
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

/* What the next level does, as the numbers now and then, with the units. */
static void effect_draw(uint8_t p)
{
    char text[PANEL_INSIDE + 1];
    char *at = text;
    uint8_t level = upgrade_levels[p], max = level >= upgrades_max(p);
    const char *units = p == UPGRADE_WIDTH ? " PX" : " PX/S";
    /* A speed is in 1/256 px a step, at 60 steps a second. */
#define VALUE(l) (p == UPGRADE_WIDTH ? upgrades_width_at(l) : (uint16_t)(upgrades_speed_at(l) * 60u / 256))

    at = put_number(at, VALUE(level));
    if (!max)
    {
        at = put_text(at, " \x10 ");
        at = put_number(at, VALUE(level + 1));
    }
    at = put_text(at, units);
    *at = 0;
    text_draw(p, EFFECT_ROW, text);
#undef VALUE
}

/* A panel's contents: its title, a pip for each level, filled for each
   bought, what the next level does, and its cost, in short digits while it
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
        uint8_t max = upgrades_max(p), level = upgrade_levels[p];
        for (i = 0; i < max; i++)
            tiles[i] = i < level ? PANEL_TILE_PIP_ON : PANEL_TILE_PIP_OFF;
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

/* A panel's picture and cost icons, where it is now. The pictures are
   stand-ins, doubled: the sled for width, the sled with its flames lit
   for speed, the energy gauge, and a brick. */
static void pictures_draw(uint8_t p)
{
    int16_t x = panel_x(p), top = PANEL_Y + PICTURE_ROW * 8;
    uint8_t dim = lit(p) ? 0 : SLED_DIM, i;

    for (i = 0; i < PANEL_SPRITES; i++)
        sprite_hide(PANEL_SPRITE(p, i));
    if (p == UPGRADE_WIDTH || p == UPGRADE_SPEED)
    {
        uint8_t level = upgrade_levels[UPGRADE_WIDTH];
        uint8_t w = upgrades_width_at(level) * 2;
        sled_show(PANEL_SPRITE(p, 0), PICTURE_SPRITES, x + (PANEL_COLS * 8 - w) / 2, top + 7, level,
                  SLED_DOUBLE | dim | (p == UPGRADE_SPEED ? SLED_FLAMES : 0));
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
    if (p < UPGRADES && upgrades_cost(p))
    {
        /* In the first cell of the cost's row, as panel_draw() centers it. */
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
                xram0_poke16(PANEL_SPRITE(p, i) + offsetof(mode5_csprite_t, x_pos_px),
                             panel_x(p) + picture_x[p * PANEL_SPRITES + i]);
    drawn_scroll = panel_scroll;
}

/* The stages shown open: all that are, but one being unlocked until its
   lock breaks. */
static uint8_t shown_open(void)
{
    return unlocking > stages_shown ? unlocking - 1 : save_stages_open();
}

/* The left edge of stage s's cart, as the train slides. */
static int16_t cart_x(uint8_t s)
{
    return CART_LEFT + (s - 1) * CART_STEP - cart_scroll;
}

/* Every stage's cart: a heap on each one cleared, its number on its plate,
   lit on the one picked, or a padlock on each that isn't open yet. */
static void carts_draw(void)
{
    uint8_t open = shown_open(), s, r, c;

    for (s = 1; s <= STAGES; s++)
    {
        uint8_t cells[CART_ROWS][CART_COLS], t = CART_TILE_BODY;
        for (r = 0; r < CART_ROWS; r++)
            for (c = 0; c < CART_COLS; c++)
                cells[r][c] = 0;
        for (r = 1; r < CART_ROWS; r++)
            for (c = 0; c < 4; c++)
                if (r != PLATE_ROW || c == 0 || c == 3)
                    cells[r][c] = t++;
        if (s <= stages_cleared && s <= open)
            for (c = 0; c < 4; c++)
            {
                cells[0][c] = CART_TILE_HEAP + c;
                cells[1][c] = CART_TILE_HEAP + 4 + c;
            }
        if (s > open)
        {
            cells[PLATE_ROW][1] = CART_TILE_LOCK;
            cells[PLATE_ROW][2] = CART_TILE_LOCK + 1;
        }
        else
        {
            uint8_t digits = s == stage_picked ? CART_TILE_DIGIT : CART_TILE_DIM;
            cells[PLATE_ROW][1] = digits + s / 10;
            cells[PLATE_ROW][2] = digits + s % 10;
        }
        if (s < STAGES)
            cells[CART_ROWS - 1][4] = CART_TILE_COUPLING;
        for (r = 0; r < CART_ROWS; r++)
            xram0_write(XRAM_CART_MAP + r * CART_MAP_COLS + (s - 1) * CART_COLS, cells[r], CART_COLS);
    }
}

/* The carts, slid to cart_scroll. */
static void carts_move(void)
{
    xram0_poke16(XRAM_CART_CONFIG + offsetof(mode2_config_t, x_pos_px), CART_LEFT - cart_scroll);
    drawn_cart_scroll = cart_scroll;
}

/* Where the cursor goes: around the panel in the middle, or the cart in
   the middle, a few pixels out. */
static void cursor_aim(void)
{
    if (cursor_on == ON_RAIL)
    {
        cursor_to[0] = PANEL_LEFT - 3;
        cursor_to[1] = PANEL_Y + TOP_ROW * 8 - 3;
        cursor_to[2] = PANEL_LEFT + PANEL_COLS * 8 + 3;
        cursor_to[3] = PANEL_Y + (panel_heights[panel_picked] + 1) * 8 + 3;
    }
    else
    {
        cursor_to[0] = CART_LEFT - 3;
        cursor_to[1] = CART_Y + CART_TOP - 3;
        cursor_to[2] = CART_LEFT + CART_W + 3;
        cursor_to[3] = CART_Y + CART_ROWS * 8 + 3;
    }
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

/* The cursor's corners: one image, flipped for each corner. */
static void cursor_set(void)
{
    static const uint8_t flips[] = {0, MODE5_HFLIP, MODE5_VFLIP, MODE5_HFLIP | MODE5_VFLIP};
    uint8_t i;

    for (i = 0; i < 4; i++)
    {
        sprite_set(CURSOR_SPRITE(i), XRAM_CURSOR_IMAGE, XRAM_PALETTE_HOLO, MODE5_SIZE(8, 8));
        sprite_attributes(CURSOR_SPRITE(i), flips[i]);
    }
}

static void cursor_move(void)
{
    uint8_t i;

    for (i = 0; i < 4; i++)
        sprite_move(CURSOR_SPRITE(i), i & 1 ? cursor[2] - 8 : cursor[0], i & 2 ? cursor[3] - 8 : cursor[1]);
}

/* The cursor shimmers: its two brightest colors pulse. */
static void shimmer(void)
{
    static const uint16_t bright[] = {
        COLOR_FROM_RGBA(200, 251, 255, 255), COLOR_FROM_RGBA(150, 240, 255, 255),
        COLOR_FROM_RGBA(110, 220, 245, 255), COLOR_FROM_RGBA(150, 240, 255, 255)};
    static const uint16_t middle[] = {
        COLOR_FROM_RGBA(79, 216, 240, 255), COLOR_FROM_RGBA(60, 190, 220, 255),
        COLOR_FROM_RGBA(40, 160, 200, 255), COLOR_FROM_RGBA(60, 190, 220, 255)};
    uint8_t phase = steps / 6 % 4;

    xram0_poke16(XRAM_PALETTE_HOLO + 4 * sizeof(uint16_t), bright[phase]);
    xram0_poke16(XRAM_PALETTE_HOLO + 3 * sizeof(uint16_t), middle[phase]);
}

/* The lock over the plate of the cart being unlocked, in two halves. */
static void lock_start(void)
{
    uint8_t i;

    for (i = 0; i < 2; i++)
    {
        sprite_set(LOCK_SPRITE(i), XRAM_LOCK_IMAGES + i * sizeof(lock_image_t), XRAM_PALETTE_SLED,
                   MODE5_SIZE(8, 16));
        half_x[i] = (8 + i * 8) * 16;
        half_y[i] = (CART_Y + PLATE_ROW * 8 - 4) * 16;
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
        sprite_move(LOCK_SPRITE(i), cart_x(unlocking) + half_x[i] / 16 + shake, half_y[i] / 16);
}

/* Ends an unlock at once, the stage shown open. */
static void unlock_finish(void)
{
    sprite_hide(LOCK_SPRITE(0));
    sprite_hide(LOCK_SPRITE(1));
    stages_shown = unlocking;
    unlocking = 0;
    lock_dirty = 0;
    carts_draw();
}

/* A step of the unlock: the shake rattles, the break snaps and shows the
   button lit, the halves fall, and a chime plays. At the end the screen
   has shown the stage open, and the game saves. */
static void unlock_step(void)
{
    uint8_t t = unlock_steps++, i;

    lock_dirty = 1;
    if (t >= UNLOCK_WAIT && t < UNLOCK_WAIT + UNLOCK_SHAKE && (t - UNLOCK_WAIT) % 6 == 0)
        sfx_play(SFX_RATTLE, cart_x(unlocking));
    if (t == UNLOCK_WAIT + UNLOCK_SHAKE)
    {
        sfx_play(SFX_SNAP, cart_x(unlocking));
        stages_shown = unlocking;
        carts_draw();
    }
    if (t == UNLOCK_WAIT + UNLOCK_SHAKE + UNLOCK_CHIME)
        sfx_play(SFX_UNLOCK, cart_x(unlocking));
    if (t > UNLOCK_WAIT + UNLOCK_SHAKE)
        for (i = 0; i < 2; i++)
        {
            half_x[i] += half_dx[i];
            half_y[i] += half_dy[i];
            half_dy[i] += HALF_GRAVITY;
        }
    if (t == UNLOCK_WAIT + UNLOCK_SHAKE + UNLOCK_FALL)
    {
        unlock_finish();
        save_write();
        DEBUG_LOG("unlocked %u\n", stages_shown);
    }
}

#ifndef NDEBUG
/* The cheats of a debug build, with Shift and right or left, which repeat
   while held. On the rail, they raise or lower the upgrade picked, for
   nothing. On the stages, they open the next stage, with its unlock, or
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
        if (u >= UPGRADES || (up ? upgrade_levels[u] >= upgrades_max(u) : !upgrade_levels[u]))
            return;
        upgrade_levels[u] += up ? 1 : -1;
        for (i = 0; i < UPGRADES; i++)
            panel_draw(i);
        pictures_dirty = 1;
        DEBUG_LOG("cheat: %s %u\n", u == UPGRADE_WIDTH ? "width" : "speed", upgrade_levels[u]);
        return;
    }
    if (up && stages_cleared < STAGES)
    {
        stages_cleared++;
        if (save_stages_open() > stages_shown)
        {
            stage_picked = unlocking = save_stages_open();
            lock_start();
        }
    }
    else if (!up && stages_cleared)
    {
        stages_cleared--;
        if (stage_picked > save_stages_open())
            stage_picked = save_stages_open();
        if (stages_shown > save_stages_open())
            stages_shown = save_stages_open();
    }
    else
        return;
    carts_draw();
    cursor_aim();
    DEBUG_LOG("cheat: %u stages cleared\n", stages_cleared);
}
#endif

static void sprites_hide(void)
{
    uint8_t i;

    for (i = 0; i < PANELS * PANEL_SPRITES + 4; i++)
        sprite_hide(SPRITE(i));
}

/* A question over the screen. The pictures and the cursor would show over
   its box, so they hide until it goes. */
static void ask(uint8_t what)
{
    if (what == ASK_BEGIN)
    {
        begin_title[12] = stage_picked >= 10 ? '0' + stage_picked / 10 : '0' + stage_picked % 10;
        begin_title[13] = stage_picked >= 10 ? '0' + stage_picked % 10 : '?';
        begin_title[14] = stage_picked >= 10 ? '?' : 0;
    }
    asking = what;
    sprites_hide();
    menu_open(what == ASK_BEGIN ? &begin_menu : &title_menu, 0, 0, 0);
    DEBUG_LOG("asked %s\n", what == ASK_BEGIN ? "begin" : "title");
}

static void unask(void)
{
    menu_close();
    asking = ASK_NONE;
    pictures_dirty = cursor_dirty = 1;
}

void shop_open(void)
{
    uint8_t p;

    video_hide_sprites();
    scene_menu();
    video_rock();
    video_text_clear();
    {
        char rail[TEXT_COLS + 1];
        uint8_t i;
        for (i = 0; i < TEXT_COLS; i++)
            rail[i] = '\xCD';
        rail[TEXT_COLS] = 0;
        video_text(0, RAIL_ROW, rail, BOX_COLOR, CLEAR);
        video_text(0, TRACK_ROW, rail, BOX_COLOR, CLEAR);
    }
    nuggets_start(1);
    cursor_on = ON_RAIL;
    asking = ASK_NONE;
    unlocking = save_stages_open() > stages_shown ? save_stages_open() : 0;
    panel_scroll = panel_picked * PANEL_STEP;
    cart_scroll = (stage_picked - 1) * CART_STEP;
    /* The map comes lit. Every panel dims, and the one picked flickers on. */
    for (p = 0; p < PANELS; p++)
    {
        panel_lit[p] = 1;
        panel_draw(p);
        panel_light(p, 0);
    }
    flicker_steps = 0;
    pictures_place();
    carts_draw();
    cursor_aim();
    for (p = 0; p < 4; p++)
        cursor[p] = cursor_to[p];
    cursor_set();
    cursor_move();
    pictures_dirty = cursor_dirty = 0;
    carts_move();
    if (unlocking)
        lock_start();
    save_write();
    DEBUG_LOG("upgrades\n");
}

/* At the start of a frame: the cursor shimmers, and the panels, their
   pictures and the cursor move to where shop_step() put them. While a
   question is up, the pictures and the cursor stay hidden. */
void shop_draw(void)
{
    shimmer();
    if (flicker_steps < sizeof flicker)
    {
        uint8_t on = flicker_steps + 1 == sizeof flicker || flicker[flicker_steps] == '1';
        flicker_steps++;
        if (on != panel_lit[panel_picked])
        {
            panel_light(panel_picked, on);
            pictures_dirty = 1;
        }
    }
    if (asking)
        return;
    if (pictures_dirty)
        pictures_place();
    else if (panel_scroll != drawn_scroll)
        pictures_move();
    if (cart_scroll != drawn_cart_scroll)
        carts_move();
    if (cursor_dirty)
        cursor_move();
    if (lock_dirty)
        lock_move();
    pictures_dirty = cursor_dirty = lock_dirty = 0;
}

/* Returns SHOP_BEGIN when the stage picked is to begin, SHOP_TITLE to go
   back to the title, and SHOP_STAY until then. */
uint8_t shop_step(void)
{
    uint8_t moved = 0, i;

    steps++;
#ifndef NDEBUG
    cheats_step();
#endif
    if (unlocking)
    {
        unlock_step();
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
    else if (input_pressed & INPUT_DOWN && cursor_on != ON_STAGES)
    {
        cursor_on = ON_STAGES;
        moved = 1;
    }
    else if (input_pressed & (INPUT_LEFT | INPUT_RIGHT))
    {
        uint8_t right = input_pressed & INPUT_RIGHT;
        if (cursor_on == ON_RAIL && (right ? panel_picked + 1 < PANELS : panel_picked > 0))
        {
            panel_light(panel_picked, 0);
            panel_picked += right ? 1 : -1;
            flicker_steps = 0;
            pictures_dirty = 1;
            moved = 1;
        }
        else if (cursor_on == ON_STAGES && (right ? stage_picked < save_stages_open() : stage_picked > 1))
        {
            stage_picked += right ? 1 : -1;
            carts_draw();
            moved = 1;
        }
    }
    else if (input_pressed & INPUT_CHOOSE)
    {
        if (cursor_on == ON_STAGES)
            ask(ASK_BEGIN);
        else if (panel_picked < UPGRADES && upgrades_buy(panel_picked))
        {
            sfx_play(SFX_BUY, SFX_CENTER);
            for (i = 0; i < UPGRADES; i++)
                panel_draw(i);
            nuggets_start(1);
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
    cart_scroll = ease(cart_scroll, (stage_picked - 1) * CART_STEP);
    for (i = 0; i < 4; i++)
        if (cursor[i] != cursor_to[i])
        {
            cursor[i] = ease(cursor[i], cursor_to[i]);
            cursor_dirty = 1;
        }
    return SHOP_STAY;
}
