/* RP6502 XRAM Mapping */

#ifndef XRAM_H
#define XRAM_H

#include <backdrop.h>
#include <carts.h>
#include <menus.h>
#include <rp6502.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <title_panels.h>

/* Keyboard, from the RIA datasheet. */

#define KEYBOARD_NO_KEY 0
#define KEYBOARD_NUM_LOCK 1
#define KEYBOARD_CAPS_LOCK 2
#define KEYBOARD_SCROLL_LOCK 3

#define KEYBOARD_PRESSED(keys, code) ((keys)[(code) >> 3] & (1 << ((code) & 7)))

#define xreg_ria_keyboard(...) xreg(0, 0, 0, __VA_ARGS__)

typedef struct
{
    uint8_t keys[32];
} keyboard_t; /* layout */

/* Gamepads, from the RIA datasheet. */

#define GAMEPAD_PLAYERS 4

#define GAMEPAD_DPAD_UP 0x01
#define GAMEPAD_DPAD_DOWN 0x02
#define GAMEPAD_DPAD_LEFT 0x04
#define GAMEPAD_DPAD_RIGHT 0x08

#define GAMEPAD_FEAT_TYPE_MASK 0x30
#define GAMEPAD_TYPE_UNKNOWN 0x00
#define GAMEPAD_TYPE_WESTERN 0x10
#define GAMEPAD_TYPE_EASTERN 0x20
#define GAMEPAD_TYPE_PLAYSTATION 0x30
#define GAMEPAD_FEAT_STICKS 0x40
#define GAMEPAD_FEAT_CONNECTED 0x80

#define GAMEPAD_LSTICK_UP 0x01
#define GAMEPAD_LSTICK_DOWN 0x02
#define GAMEPAD_LSTICK_LEFT 0x04
#define GAMEPAD_LSTICK_RIGHT 0x08
#define GAMEPAD_RSTICK_UP 0x10
#define GAMEPAD_RSTICK_DOWN 0x20
#define GAMEPAD_RSTICK_LEFT 0x40
#define GAMEPAD_RSTICK_RIGHT 0x80

#define GAMEPAD_BTN0_A 0x01
#define GAMEPAD_BTN0_B 0x02
#define GAMEPAD_BTN0_C 0x04
#define GAMEPAD_BTN0_X 0x08
#define GAMEPAD_BTN0_Y 0x10
#define GAMEPAD_BTN0_Z 0x20
#define GAMEPAD_BTN0_L1 0x40
#define GAMEPAD_BTN0_R1 0x80

#define GAMEPAD_BTN1_L2 0x01
#define GAMEPAD_BTN1_R2 0x02
#define GAMEPAD_BTN1_SELECT 0x04
#define GAMEPAD_BTN1_START 0x08
#define GAMEPAD_BTN1_HOME 0x10
#define GAMEPAD_BTN1_L3 0x20
#define GAMEPAD_BTN1_R3 0x40

#define xreg_ria_gamepad(...) xreg(0, 0, 2, __VA_ARGS__)

typedef struct
{
    uint8_t dpad;
    uint8_t sticks;
    uint8_t btn0;
    uint8_t btn1;
    int8_t lx;
    int8_t ly;
    int8_t rx;
    int8_t ry;
    uint8_t l2;
    uint8_t r2;
} gamepad_player_t;

typedef struct
{
    gamepad_player_t player[GAMEPAD_PLAYERS];
} gamepad_t; /* layout */

/* Programmable Sound Generator, from the RIA datasheet. */

#define PSG_CHANNELS 8

#define PSG_WAVE_SINE 0x00
#define PSG_WAVE_SQUARE 0x10
#define PSG_WAVE_SAWTOOTH 0x20
#define PSG_WAVE_TRIANGLE 0x30
#define PSG_WAVE_NOISE 0x40

#define PSG_GATE 0x01

#define PSG_FREQ_HZ(hz) ((hz) * 3u)
#define PSG_PAN(pan) ((uint8_t)((pan) * 2))

#define xreg_ria_psg(...) xreg(0, 1, 0, __VA_ARGS__)

typedef struct
{
    uint16_t freq;
    uint8_t duty;
    uint8_t attack;
    uint8_t decay;
    uint8_t release_wave;
    uint8_t pan_gate;
    uint8_t reserved;
} psg_channel_t;

typedef struct
{
    psg_channel_t channel[PSG_CHANNELS];
} psg_t; /* layout */

/* After the XRAM_ names: PSG_PAGE_CHECK(XRAM_PSG); */
#define PSG_PAGE_CHECK(addr) \
    _Static_assert((addr) % 256 + sizeof(psg_t) <= 256, #addr " crosses a page.")

/* Canvas, from the VGA datasheet. */

#define xreg_vga_canvas(...) xreg(1, 0, 0, __VA_ARGS__)

#define CANVAS_CONSOLE 0
#define CANVAS_320X240 1
#define CANVAS_320X180 2
#define CANVAS_640X480 3
#define CANVAS_640X360 4

/* Colors, from the VGA datasheet. */

#define COLOR_FROM_RGBA(r, g, b, alpha)                             \
    ((((unsigned)(b) >> 3) << 11) | (((unsigned)(g) >> 3) << 6) | \
     (((unsigned)(alpha) >> 7) << 5) | ((unsigned)(r) >> 3))

/* Mode 1: Character, from the VGA datasheet. */

#define xreg_vga_mode1(...) xreg(1, 0, 1, 1, __VA_ARGS__)

#define MODE1_1BPP 0x00
#define MODE1_4BPPR 0x01
#define MODE1_4BPP 0x02
#define MODE1_8BPP 0x03
#define MODE1_16BPP 0x04

#define MODE1_8X8 0x00
#define MODE1_8X16 0x08

#define MODE1_FG_BG(fg, bg) ((uint8_t)(((fg) << 4) | (bg)))
#define MODE1_BG_FG(bg, fg) ((uint8_t)(((bg) << 4) | (fg)))

typedef struct
{
    bool x_wrap;
    bool y_wrap;
    int16_t x_pos_px;
    int16_t y_pos_px;
    int16_t width_chars;
    int16_t height_chars;
    uint16_t xram_data_ptr;
    uint16_t xram_palette_ptr;
    uint16_t xram_font_ptr;
} mode1_config_t; /* layout */

typedef struct
{
    uint8_t glyph_code;
    uint8_t bg_fg_index;
} mode1_4bpp_data_t; /* layout */

/* Mode 2: Tile, from the VGA datasheet. */

#define xreg_vga_mode2(...) xreg(1, 0, 1, 2, __VA_ARGS__)

#define MODE2_1BPP 0x00
#define MODE2_2BPP 0x01
#define MODE2_4BPP 0x02
#define MODE2_8BPP 0x03

#define MODE2_8X8 0x00
#define MODE2_16X16 0x08

#define MODE2_X_TRIM(cols) ((cols) << 4)
#define MODE2_Y_TRIM(rows) ((rows) << 8)

#define MODE2_TILE(bpp, size)                 \
    struct                                    \
    {                                         \
        struct                                \
        {                                     \
            uint8_t cols[(size) * (bpp) / 8]; \
        } rows[size];                         \
    }

typedef struct
{
    bool x_wrap;
    bool y_wrap;
    int16_t x_pos_px;
    int16_t y_pos_px;
    int16_t width_tiles;
    int16_t height_tiles;
    uint16_t xram_data_ptr;
    uint16_t xram_palette_ptr;
    uint16_t xram_tile_ptr;
} mode2_config_t; /* layout */

/* Mode 3: Bitmap, from the VGA datasheet. */

#define xreg_vga_mode3(...) xreg(1, 0, 1, 3, __VA_ARGS__)

#define MODE3_1BPP 0x00
#define MODE3_2BPP 0x01
#define MODE3_4BPP 0x02
#define MODE3_8BPP 0x03
#define MODE3_16BPP 0x04

#define MODE3_REVERSE_BITS 0x08

typedef struct
{
    bool x_wrap;
    bool y_wrap;
    int16_t x_pos_px;
    int16_t y_pos_px;
    int16_t width_px;
    int16_t height_px;
    uint16_t xram_data_ptr;
    uint16_t xram_palette_ptr;
} mode3_config_t; /* layout */

/* Mode 5: Sprite 1,2,4,8-bit, from the VGA datasheet. */

#define xreg_vga_mode5(...) xreg(1, 0, 1, 5, __VA_ARGS__)

#define MODE5_1BPP 0x00
#define MODE5_2BPP 0x01
#define MODE5_4BPP 0x02
#define MODE5_8BPP 0x03

#define MODE5_8X8 0x00
#define MODE5_16X16 0x08
#define MODE5_32X32 0x10
#define MODE5_64X64 0x18
#define MODE5_128X128 0x20
#define MODE5_256X256 0x28
#define MODE5_512X512 0x30
#define MODE5_CUSTOM 0x38

#define MODE5_HFLIP 0x10
#define MODE5_VFLIP 0x20
#define MODE5_HDOUBLE 0x40
#define MODE5_VDOUBLE 0x80

#define MODE5_SIZE(width, height) \
    ((((height) / 4 - 1) << 4) | ((width) / 4 - 1))

#define MODE5_CUSTOM_IMAGE(bpp, width, height)       \
    struct                                           \
    {                                                \
        struct                                       \
        {                                            \
            uint8_t cols[((width) * (bpp) + 7) / 8]; \
        } rows[height];                              \
    }

#define MODE5_PALETTE_CHECK(type) \
    _Static_assert(sizeof(type) / sizeof(uint16_t) <= 512, #type " holds more than 512 colors.")

typedef struct
{
    int16_t x_pos_px;
    int16_t y_pos_px;
    uint16_t xram_sprite_ptr;
    uint16_t palette_ptr;
    uint8_t width_height;
    uint8_t attributes;
} mode5_csprite_t; /* layout */

/* Quarry. */

#define TEXT_COLS 40
#define TEXT_ROWS 30

#define SPRITE_BYTES sizeof(mode5_csprite_t) /* for the tests, which step through the lists */
#define BRICKS_MAX 48
#define BRICK_COLORS 5 /* gray, red, green, blue, gold */
/* A brick's palette from here holds its cracks' 4 colors. */
#define BRICK_CRACK_COLORS 8
#define JETS_MAX 3 /* under one sled */
#define NUGGETS_MAX 16 /* in flight at once */
#define MENU_SPRITES 40
#define LOCKS 4 /* padlocks on the carts of the levels after the one picked */
#define CURSOR_SIZE 12 /* each of its 4 corners, square */
#define COUNT_DIGITS 5 /* of a nugget count */
#define ICON_SIZE 12   /* the sprite of the nugget, coin or ball by a count, as tall as its digits */
#define ICON_ROUND 10  /* its circle, across, at the sprite's top left */
#define BALL_DIGITS 2  /* of the count of balls */

/* The panels of the upgrade screen hang from a rail and slide across it.
   They are a map of 8-bit tiles on plane 1, PANEL_ROWS down, the top row
   for the hangers, and PANEL_MAP_COLS across, which wraps: PANEL_SLOTS
   slots PANEL_COLS wide, side by side, panel p in slot p % PANEL_SLOTS,
   which holds the four around the one picked, so any number of panels
   need no more. The art of their frames leaves the gap between them.
   art/panels.py makes the tiles, their palette and each panel's frame,
   and writes build/panels.h. */
#define PANELS 4
#define PANEL_COLS 20
#define PANEL_PITCH PANEL_COLS
#define PANEL_SLOTS 4 /* the panels around the one picked, each in a slot of the map */
#define PANEL_MAP_COLS (PANEL_SLOTS * PANEL_PITCH)
#define PANEL_ROWS 19
#define PANEL_Y 16 /* the top of the hangers */

/* The level select is a train of mine carts along the bottom: a map of
   4-bit tiles on plane 1 too, on the scanlines under the panels, which
   slides on its own. Each cart is CART_COLS cells with its coupling, and
   CART_ROWS down. art/carts.py makes the tiles and their palette, and the
   padlock over a locked level, whole and in halves, and writes
   build/carts.h. */
#define CARTS_MAX 10
#define CART_COLS 5
#define CART_ROWS CART_CELL_ROWS
#define CART_MAP_COLS (CARTS_MAX * CART_COLS)
/* The top of the carts' cells, so the track their wheels sit on, at
   CART_Y + CART_FOOT, is a little up from the foot of the screen. */
#define CART_Y 191
#define CART_TILES_MAX 64

/* The backdrop of the upgrade screen, from art/backdrop.py, on plane 0:
   a workshop wall in three bands of 16x16 tiles, each with its own palette,
   tiles and map, which build/backdrop.h sizes. The top and the bottom show,
   in 15 colors, and the middle is behind the panels, in 4 grays. */
#define BACKDROP_BANDS 3

/* The pictures of the panels nearest the middle, each up to PICTURE_BYTES:
   the three that show, and the next one the way the rail moves, which
   loads before it slides into view. For now a picture is a flat sled. */
#define PICTURE_SLOTS 4
#define PICTURE_BYTES 1024

/* The texture behind a level's playfield, from art/texture.py: a bitmap at
   2 bits a pixel that wraps. */
#define TEXTURE_W 320
#define TEXTURE_H 240

/* The frame of the playfield, a frame set from art/frames.py: a post
   POST_W wide on each side, in POST_SPRITES pieces POST_H rows tall, the
   cap beam BEAM_H tall across the top, in up to BEAM_SPRITES pieces BEAM_W
   columns wide, enough for a playfield as wide as the screen, and a cap
   over each post. A set's post shows some of its columns, from its
   inside, and the rest are clear. The beam's art repeats every few px,
   and it runs behind the caps, so a playfield can be any width. Behind
   them are a knee brace in each top corner, and a machine on the right
   wall, from art/screen.py. */
#define POST_W 20
#define POST_H 48
#define POST_SPRITES 5
#define BEAM_H 16
#define BEAM_W 48
#define BEAM_SPRITES 7
#define BRACE_SIZE 32
#define MACHINE_W 24
#define MACHINE_H 40

/* A curtain set, from art/curtain.py: its palette, then the left and the
   right curtain, each CURTAIN_W wide and CURTAIN_H tall, in CURTAIN_TILES
   sprite images. */
#define CURTAIN_W 100
#define CURTAIN_H 240
#define CURTAIN_TILES 8
#define CURTAIN_BYTES (CURTAIN_W * CURTAIN_H / 2)

/* The sleds that art/sled.py draws, one for each width of TUNE_WIDTHS, up
   to SLEDS. A sled's images are the sled flat, 8 rows, then tilted 1 and
   2 px in 8 to the right as it falls, SLED_TILT_ROWS each, all its width
   rounded up to 4 wide. Each sled has a slot of SLED_SLOT bytes, which
   art/sled.py gives too. */
#define SLEDS 11
#define SLED_WIDTH_MAX 64
#define SLED_TILT_ROWS 24
#define SLED_SLOT (SLED_WIDTH_MAX * (8 + 2 * SLED_TILT_ROWS) / 2)

/* Frames of a jet, in the order of art/jet.png: the nozzle alone, then
   with its short, medium and long flame, straight down, then the flames
   swiveled to push the sled right. MODE5_HFLIP swivels them to push it
   left. */
#define JET_FRAMES 7
#define JET_NOZZLE 0
#define JET_FLAME 1
#define JET_SWIVEL 3

/* The cracks over a brick, from art/bricks.py: pieces CRACK_W wide, as
   many as fit across it, each from one of CRACK_SETS sets, flipped either
   way, a set an image for each of CRACK_STATES, each step of a brick
   more broken. */
#define CRACK_W 16
#define CRACK_H 8
#define CRACK_SETS 6
#define CRACK_STATES 10
#define CRACKS_MAX 48 /* a sprite each, over the bricks */

/* A brick breaks into chunks that fly, CHUNK_IMAGES of them in
   art/chunks.png, and CHUNKS_MAX sprites for them, the oldest giving way to
   a new break. */
#define CHUNK_IMAGES 16
#define CHUNKS_MAX 32

/* Frames of the smoke, in the order of art/smoke.png. */
#define SMOKE_FRAMES 3

/* The energy gauge is a sight glass down the right of the screen, from
   src/energy.c: a fitting FITTING_H tall at each end, a pipe off the edge
   of the screen and the ring that grips the glass, from art/gauge.py, the
   bottom one the top one turned over, and between them
   GLASS_H rows of glass, a row for each step of the fuel's level, which
   shows the rock behind it. The glass is made as a level starts: the right
   curtain's pixels under it, in the glass palette, the curtain's colors
   tinted, and an outline down each side. A glint runs down it GLINT_COL
   in, the glass palette's flat GLASS_GLINT. The fuel is LIQUID_SEGMENTS
   sprites of one image of liquid LIQUID_H tall, up from the foot of the
   glass, under one of its surface, and up to BUBBLES bubbles rise through
   it. Sprites are 64 tall at most, so the glass is in pieces. */
#define GAUGE_W 16
#define FITTING_H 20
#define GLASS_X 2 /* from the gauge's left */
#define GLASS_W 12
#define GLASS_H 200
#define GLASS_PIECES 4 /* GLASS_H in pieces of 64, the last one shorter */
#define GLINT_COL 2    /* of the glass */
#define GLASS_ROCK 1     /* the glass palette's darkest rock, where the shaft is clear */
#define GLASS_OUTLINE 14 /* its colors past the curtain's 13 */
#define GLASS_GLINT 15
#define LIQUID_H 16
#define LIQUID_SEGMENTS (GLASS_H / LIQUID_H) /* the rows above them, the surface's alone */
#define BUBBLES 16 /* rising through the fuel at once, a sprite each */
#define BUBBLE_SIZE 4

/* The machine on the right wall shows how the fuel stands through a
   clear window, as an old parking meter does: a paddle METER_W by
   METER_H, green, yellow or red, behind the machine, which slides down
   out of sight and up again in its new color as the fuel falls. It rises
   METER_RISE px from down to up. It is the fitting palette's
   METER_PADDLE and METER_SHADE, which the game sets. */
#define METER_W 12
#define METER_H 8
#define METER_RISE 7
#define METER_PADDLE 10
#define METER_SHADE 11

/* Pieces of the old energy bar, in the order of art/energy.png, the
   upgrade screen's stand-in picture of the gauge. */
#define ENERGY_TOP 0
#define ENERGY_FULL 1
#define ENERGY_LOW 2
#define ENERGY_EMPTY 3
#define ENERGY_BOTTOM 4

/* A dwarf with something to say, from art/talk.py. He and his speech
   bubble take the menus' place in XRAM, as the two never show together:
   the dwarf a portrait DWARF_SIZE square, in up to DWARF_PIECES sprites
   on plane 2 in his own colors, and the bubble a map of 2-bit tiles on
   plane 2's fill, BUBBLE_COLS by up to BUBBLE_ROWS, in place of the
   menus. The committeeman's bubble has the coin he hands over in it,
   art/big-coin.png, BIG_COIN_SIZE square, a sprite on plane 2 in its own
   colors. Only a level has room for it, in its own art. */
#define DWARF_SIZE 80
#define DWARF_PIECES 3
#define DWARF_BYTES 2816
#define BUBBLE_COLS 28
#define BUBBLE_ROWS 10
#define BIG_COIN_SIZE 44
#define BUBBLE_TILES 48

typedef MODE2_TILE(8, 8) panel_tile_t;
typedef MODE2_TILE(4, 8) cart_tile_t;
typedef MODE2_TILE(4, 8) menu_tile_t;
typedef MODE2_TILE(4, 8) title_tile_t;
typedef MODE2_TILE(2, 8) bubble_tile_t;
typedef MODE5_CUSTOM_IMAGE(2, 24, 8) brick_image_t;
typedef MODE5_CUSTOM_IMAGE(2, CRACK_W, CRACK_H) crack_image_t;
typedef MODE5_CUSTOM_IMAGE(2, 8, 8) chunk_image_t;
#define CRACK_IMAGE_BYTES sizeof(crack_image_t) /* for the tests */
typedef MODE5_CUSTOM_IMAGE(4, 8, 8) piece_image_t;
typedef MODE5_CUSTOM_IMAGE(4, ICON_SIZE, ICON_SIZE) icon_image_t;
typedef MODE5_CUSTOM_IMAGE(4, CURSOR_SIZE, CURSOR_SIZE) cursor_image_t;
typedef MODE5_CUSTOM_IMAGE(4, 8, 12) jet_image_t;
typedef MODE5_CUSTOM_IMAGE(4, 8, 12) digit_image_t;
#define JET_IMAGE_BYTES sizeof(jet_image_t) /* these two for the tests */
#define DIGIT_IMAGE_BYTES sizeof(digit_image_t)
typedef MODE5_CUSTOM_IMAGE(4, 8, 8) energy_image_t;
typedef MODE5_CUSTOM_IMAGE(4, GAUGE_W, FITTING_H) fitting_image_t;
typedef MODE5_CUSTOM_IMAGE(4, GLASS_W, LIQUID_H) liquid_image_t;
typedef MODE5_CUSTOM_IMAGE(4, GLASS_W, GLASS_H) glass_image_t;
typedef MODE5_CUSTOM_IMAGE(4, BUBBLE_SIZE, BUBBLE_SIZE) bubble_image_t;
typedef MODE5_CUSTOM_IMAGE(4, METER_W, METER_H) meter_image_t;
typedef MODE5_CUSTOM_IMAGE(4, 64, 64) logo_image_t; /* a third of art/logo.png */
typedef MODE5_CUSTOM_IMAGE(4, POST_W, POST_H) post_image_t;
typedef MODE5_CUSTOM_IMAGE(4, BEAM_W, BEAM_H) beam_image_t;
typedef MODE5_CUSTOM_IMAGE(4, POST_W, BEAM_H) cap_image_t;
typedef MODE5_CUSTOM_IMAGE(4, BRACE_SIZE, BRACE_SIZE) brace_image_t;
typedef MODE5_CUSTOM_IMAGE(4, MACHINE_W, MACHINE_H) machine_image_t;
typedef MODE5_CUSTOM_IMAGE(4, 16, 16) lock_image_t;
typedef MODE5_CUSTOM_IMAGE(4, BIG_COIN_SIZE, BIG_COIN_SIZE) big_coin_image_t;
typedef MODE5_CUSTOM_IMAGE(4, 8, 16) half_lock_image_t;

/* The palettes, in the order of the rows of art/palettes.png. */
typedef struct
{
    uint16_t main[16];
    uint16_t bricks[BRICK_COLORS][16]; /* bricks, their cracks and chunks, and nuggets, a palette a color */
    uint16_t fx[16];                   /* smoke and the energy gauge */
    uint16_t logo[16];
    uint16_t sled[16];    /* the sleds, their jets, the digits, and the coin */
    uint16_t texture[16]; /* the first 4, loaded with each curtain set */
    uint16_t curtain[16]; /* loaded with each curtain set */
    uint16_t shade[16];   /* the sled row at half, for the machine and a dim sled */
    uint16_t holo[16];    /* the cursor of the upgrade screen and the menus, which shimmers */
    uint16_t liquid[16];  /* the fuel in the gauge's sight glass */
    uint16_t fitting[16]; /* the gauge's fittings, and the meter's paddle */
    uint16_t glass[16];   /* the curtain row seen through the glass, loaded with each curtain set */
} palettes_t;

/* Plane 0 sprites, in front of the texture and behind the bricks, back to
   front. */
typedef struct
{
    mode5_csprite_t braces[2];
    mode5_csprite_t meter; /* behind the machine's window */
    mode5_csprite_t machine;
    mode5_csprite_t curtains[2][CURTAIN_TILES];
    mode5_csprite_t posts[2][POST_SPRITES];
    mode5_csprite_t beam[BEAM_SPRITES];
    mode5_csprite_t caps[2];
} scenery_t;

/* Plane 1 sprites, over its tiles and under plane 2's: on the title and
   the upgrade screen, the locks over its carts, under the menus and a
   dwarf's bubble, and on a level, from the level's own art, the cracks
   over the bricks, the chunks of the bricks breaking, the ball and the
   sled. */
typedef struct
{
    mode5_csprite_t halves[2]; /* of the lock that breaks */
    mode5_csprite_t padlocks[LOCKS];
} locks_t;

typedef struct
{
    mode5_csprite_t ball;
    mode5_csprite_t sled;
    mode5_csprite_t jets[JETS_MAX];
    mode5_csprite_t smoke[JETS_MAX]; /* a puff under each jet */
} actors_t;

typedef struct
{
    mode5_csprite_t cracks[CRACKS_MAX];
    mode5_csprite_t chunks[CHUNKS_MAX];
    actors_t actors;
} level_sprites_t;

#define LEVEL_SPRITES (sizeof(level_sprites_t) / sizeof(mode5_csprite_t))

/* The energy gauge's sprites, back to front: the glass, the fuel over it,
   the bubbles rising through the fuel, and the fittings over the ends of
   them all. */
typedef struct
{
    mode5_csprite_t glass[GLASS_PIECES];
    mode5_csprite_t liquid[LIQUID_SEGMENTS];
    mode5_csprite_t surface;
    mode5_csprite_t bubbles[BUBBLES];
    mode5_csprite_t fittings[2]; /* top, bottom */
} gauge_sprites_t;

/* Plane 2 sprites, over the menus, back to front, as a plane draws its
   list: the gauge, the upgrade screen's pictures and trolleys, which
   slide under the counts, the nuggets in flight, which land under them
   too, the counts with their nugget, coin or ball, a dwarf, and last, over
   them all, the holographic cursor's 4 corners. On a level the first of
   the pictures' is the big coin in the committeeman's bubble. */
typedef struct
{
    gauge_sprites_t gauge;
    mode5_csprite_t menu[MENU_SPRITES];   /* the upgrade screen's pictures */
    mode5_csprite_t nuggets[NUGGETS_MAX]; /* in flight */
    mode5_csprite_t coin_icon;
    mode5_csprite_t coin_digits[COUNT_DIGITS];
    mode5_csprite_t nugget_icons[BRICK_COLORS];
    mode5_csprite_t nugget_digits[BRICK_COLORS][COUNT_DIGITS];
    mode5_csprite_t ball_icon;
    mode5_csprite_t ball_digits[BALL_DIGITS];
    mode5_csprite_t dwarf[DWARF_PIECES];  /* over the counts, when he talks */
    mode5_csprite_t cursor[4];
} hud_t;

/* A band of the backdrop, as ROM:backdrop holds it. */
#define BACKDROP_BAND(band)                                       \
    struct                                                        \
    {                                                             \
        uint16_t palette[1 << BACKDROP_##band##_BPP];             \
        MODE2_TILE(BACKDROP_##band##_BPP, 16) tiles[BACKDROP_##band##_TILES]; \
        uint8_t map[BACKDROP_##band##_ROWS][BACKDROP_COLS];       \
    }

/* The art of the upgrade screen. */
typedef struct
{
    BACKDROP_BAND(TOP) top; /* these three, as ROM:backdrop holds them */
    BACKDROP_BAND(MIDDLE) middle;
    BACKDROP_BAND(BOTTOM) bottom;
    uint8_t backdrop_sprites[BACKDROP_SPRITE_BYTES]; /* the cogs' frames and the steam's */
    uint8_t pictures[PICTURE_SLOTS][PICTURE_BYTES];
    uint16_t panel_palette[256]; /* these two, as ROM:panels holds them, then its frames */
    panel_tile_t panel_tiles[256];
    uint8_t panels[PANEL_ROWS][PANEL_MAP_COLS]; /* the slots */
    uint16_t cart_palette[16]; /* these five, as ROM:carts holds them */
    uint16_t lock_palette[16];
    lock_image_t lock_image;
    half_lock_image_t lock_halves[2];
    cart_tile_t cart_tiles[CART_TILES_MAX];
    uint8_t cart_map[CART_ROWS][CART_MAP_COLS];
} menu_art_t;

/* A frame set, as ROM:frame1 and on hold it: its palette, the same colors
   darkened for the braces, then its pieces. */
typedef struct
{
    uint16_t palette[16];
    uint16_t shade[16];
    uint8_t shows;  /* how many of the post's columns show */
    uint8_t repeat; /* the px the beam's art repeats every, from its first column */
    post_image_t post;
    beam_image_t beam;
    cap_image_t cap;
    brace_image_t brace;
} frame_set_t;

/* The energy gauge's images: the fitting, the fuel, a bubble and its
   drop, and the meter's paddle, as ROM:gauge holds them, then the glass,
   made for each level. */
typedef struct
{
    fitting_image_t fitting; /* the top one, and turned over, the bottom */
    liquid_image_t liquid;
    liquid_image_t surface;
    bubble_image_t bubble;
    bubble_image_t drop; /* that a bubble throws up as it pops */
    meter_image_t meter;
    glass_image_t glass;
} gauge_art_t;

/* A level's own art: its frame set, the cracks and the chunks, as
   ROM:cracks and ROM:chunks hold them, its sprites on plane 1, the
   energy gauge's images, and the coin in the committeeman's bubble, its
   colors and its image, as ROM:big_coin_colors and ROM:big_coin hold
   them, which load with his bubble. */
typedef struct
{
    frame_set_t frame;
    crack_image_t cracks[CRACK_SETS][CRACK_STATES];
    chunk_image_t chunks[CHUNK_IMAGES];
    level_sprites_t sprites;
    gauge_art_t gauge;
    uint16_t big_coin_palette[16];
    big_coin_image_t big_coin;
} level_art_t;

/* A piece of a dwarf: where it goes, from his top left, and its image,
   from the start of his. */
typedef struct
{
    int16_t x, y;
    uint16_t image;
    uint8_t size; /* MODE5_SIZE */
    uint8_t unused;
} dwarf_piece_t;

/* Where a dwarf stands once he is in, on his side of the screen, and his
   pieces. */
typedef struct
{
    int16_t x, y;
    uint8_t pieces;
    uint8_t unused;
    dwarf_piece_t piece[DWARF_PIECES];
} dwarf_head_t;

/* A dwarf, as ROM:dwarves holds them, one after another from 1: his head,
   then his colors and his image. */
typedef struct
{
    dwarf_head_t head;
    uint16_t palette[16];
    uint8_t images[DWARF_BYTES];
} dwarf_t;

/* Where a speech bubble stands once it is in, how many rows and columns of
   cells it has, the cell of its OK and the OK's two tiles, which go in
   when it shows, and where the big coin is in it, from its top left, if
   it has the coin, or 0, 0. */
typedef struct
{
    int16_t x, y;
    uint8_t rows, cols;
    uint8_t ok_col, ok_row;
    uint8_t ok_tiles[2];
    uint8_t coin_x, coin_y;
} bubble_head_t;

/* A speech bubble, as ROM:bubbles holds them, one after another from 1:
   its head, then its 4 colors, its tiles and its map. */
typedef struct
{
    bubble_head_t head;
    uint16_t palette[4];
    bubble_tile_t tiles[BUBBLE_TILES];
    uint8_t map[BUBBLE_ROWS][BUBBLE_COLS];
} bubble_t;

/* A dwarf talking, and his bubble up. */
typedef struct
{
    dwarf_t dwarf;
    bubble_t bubble;
} talk_t;

/* The title's own art: the logo, then its panels, from
   art/title_panels.py, a map of 4-bit tiles on plane 1, TITLE_COLS by
   TITLE_ROWS cells under the logo: their palette and tiles, as
   ROM:title_panels holds them, then the map, which the title loads from
   the maps after them. */
typedef struct
{
    logo_image_t logo_images[3];
    uint16_t panel_palette[16];
    title_tile_t panel_tiles[TITLE_TILES];
    uint8_t panel_map[TITLE_ROWS][TITLE_COLS];
} title_art_t;

/* The art of the title and of a level: the texture and a curtain set, the
   level's sled, then the title's own art or, in its place, the level's.
   Each screen loads its own when it starts. */
typedef struct
{
    uint8_t texture[TEXTURE_H][TEXTURE_W / 4];
    uint8_t curtains[2][CURTAIN_BYTES];
    uint8_t sled_images[SLED_SLOT]; /* the sled of a level */
    union
    {
        title_art_t title;
        level_art_t level; /* a level's own */
    };
} cave_art_t;

typedef struct
{
    keyboard_t keyboard;
    gamepad_t gamepad;
    psg_t psg;
    mode2_config_t backdrop_configs[BACKDROP_BANDS];
    mode3_config_t texture_config;
    mode2_config_t menu_config;
    mode2_config_t talk_config; /* the bubble, on plane 2 in the menus' place */
    mode2_config_t panel_config; /* the upgrade screen's panels, or the title's */
    mode2_config_t cart_config;
    palettes_t palettes;
    scenery_t scenery;
    mode5_csprite_t bricks[BRICKS_MAX];
    locks_t locks;
    hud_t hud;
    union
    {
        struct
        {
            uint8_t menu_map[TEXT_ROWS][TEXT_COLS]; /* the menus' tiles, a byte a cell */
            uint16_t menu_palette[16];              /* these two, as ROM:menus holds them */
            menu_tile_t menu_tiles[MENU_TILES];
        };
        talk_t talk; /* a dwarf talking, in the menus' place */
    };
    brick_image_t brick_image;
    piece_image_t nugget_image;
    icon_image_t nugget_icon_image;
    piece_image_t ball_image;
    icon_image_t ball_icon_image;
    icon_image_t coin_image;
    cursor_image_t cursor_image;
    jet_image_t jet_images[JET_FRAMES];
    piece_image_t smoke_images[SMOKE_FRAMES];
    energy_image_t energy_images[5];
    digit_image_t digit_images[10];
    machine_image_t machine_image;
    union
    {
        menu_art_t menu;
        cave_art_t cave;
    } art; /* each screen loads its own, from the ROM */
} xram_layout_t;

#define XRAM_KEYBOARD offsetof(xram_layout_t, keyboard)
#define XRAM_GAMEPAD offsetof(xram_layout_t, gamepad)
#define XRAM_PSG offsetof(xram_layout_t, psg)
#define XRAM_BACKDROP_CONFIG(band) (offsetof(xram_layout_t, backdrop_configs) + (band) * sizeof(mode2_config_t))
#define XRAM_TEXTURE_CONFIG offsetof(xram_layout_t, texture_config)
#define XRAM_MENU_CONFIG offsetof(xram_layout_t, menu_config)
#define XRAM_TALK_CONFIG offsetof(xram_layout_t, talk_config)
#define XRAM_PANEL_CONFIG offsetof(xram_layout_t, panel_config)
#define XRAM_CART_CONFIG offsetof(xram_layout_t, cart_config)
#define XRAM_PALETTES offsetof(xram_layout_t, palettes)
#define XRAM_PALETTE_MAIN offsetof(xram_layout_t, palettes.main)
#define XRAM_PALETTE_BRICKS offsetof(xram_layout_t, palettes.bricks)
#define XRAM_PALETTE_BRICK(color) (XRAM_PALETTE_BRICKS + (color) * 16 * sizeof(uint16_t))
#define XRAM_PALETTE_FX offsetof(xram_layout_t, palettes.fx)
#define XRAM_PALETTE_LOGO offsetof(xram_layout_t, palettes.logo)
#define XRAM_PALETTE_SLED offsetof(xram_layout_t, palettes.sled)
#define XRAM_PALETTE_TEXTURE offsetof(xram_layout_t, palettes.texture)
#define XRAM_PALETTE_CURTAIN offsetof(xram_layout_t, palettes.curtain)
#define XRAM_PALETTE_SHADE offsetof(xram_layout_t, palettes.shade)
#define XRAM_PALETTE_HOLO offsetof(xram_layout_t, palettes.holo)
#define XRAM_PALETTE_LIQUID offsetof(xram_layout_t, palettes.liquid)
#define XRAM_PALETTE_FITTING offsetof(xram_layout_t, palettes.fitting)
#define XRAM_PALETTE_GLASS offsetof(xram_layout_t, palettes.glass)
#define XRAM_SCENERY offsetof(xram_layout_t, scenery)
#define XRAM_BRACE_SPRITES offsetof(xram_layout_t, scenery.braces)
#define XRAM_METER_SPRITE offsetof(xram_layout_t, scenery.meter)
#define XRAM_MACHINE_SPRITE offsetof(xram_layout_t, scenery.machine)
#define XRAM_CURTAIN_SPRITES offsetof(xram_layout_t, scenery.curtains)
#define XRAM_POST_SPRITES offsetof(xram_layout_t, scenery.posts)
#define XRAM_BEAM_SPRITES offsetof(xram_layout_t, scenery.beam)
#define XRAM_CAP_SPRITES offsetof(xram_layout_t, scenery.caps)
#define XRAM_BRICKS offsetof(xram_layout_t, bricks)
#define XRAM_LOCKS offsetof(xram_layout_t, locks)
#define XRAM_HALF_SPRITES offsetof(xram_layout_t, locks.halves)
#define XRAM_LOCK_SPRITES offsetof(xram_layout_t, locks.padlocks)
#define XRAM_HUD offsetof(xram_layout_t, hud)
#define XRAM_GAUGE_SPRITES offsetof(xram_layout_t, hud.gauge)
#define XRAM_GLASS_SPRITES offsetof(xram_layout_t, hud.gauge.glass)
#define XRAM_LIQUID_SPRITES offsetof(xram_layout_t, hud.gauge.liquid)
#define XRAM_SURFACE_SPRITE offsetof(xram_layout_t, hud.gauge.surface)
#define XRAM_BUBBLE_SPRITES offsetof(xram_layout_t, hud.gauge.bubbles)
#define XRAM_FITTING_SPRITES offsetof(xram_layout_t, hud.gauge.fittings)
#define XRAM_COIN_ICON offsetof(xram_layout_t, hud.coin_icon)
#define XRAM_COIN_DIGITS offsetof(xram_layout_t, hud.coin_digits)
#define XRAM_NUGGET_ICONS offsetof(xram_layout_t, hud.nugget_icons)
#define XRAM_NUGGET_DIGITS offsetof(xram_layout_t, hud.nugget_digits)
#define XRAM_BALL_ICON offsetof(xram_layout_t, hud.ball_icon)
#define XRAM_BALL_DIGITS offsetof(xram_layout_t, hud.ball_digits)
#define XRAM_NUGGET_SPRITES offsetof(xram_layout_t, hud.nuggets)
#define XRAM_MENU_SPRITES offsetof(xram_layout_t, hud.menu)
#define XRAM_BIG_COIN_SPRITE XRAM_MENU_SPRITES /* the first, which a level leaves free */
#define XRAM_DWARF_SPRITES offsetof(xram_layout_t, hud.dwarf)
#define XRAM_CURSOR_SPRITES offsetof(xram_layout_t, hud.cursor)
#define XRAM_MENU_MAP offsetof(xram_layout_t, menu_map)
#define XRAM_MENU_PALETTE offsetof(xram_layout_t, menu_palette)
#define XRAM_MENU_TILES offsetof(xram_layout_t, menu_tiles)
#define XRAM_TALK_DWARF offsetof(xram_layout_t, talk.dwarf)
#define XRAM_DWARF_PALETTE offsetof(xram_layout_t, talk.dwarf.palette)
#define XRAM_DWARF_IMAGES offsetof(xram_layout_t, talk.dwarf.images)
#define XRAM_TALK_BUBBLE offsetof(xram_layout_t, talk.bubble)
#define XRAM_BUBBLE_PALETTE offsetof(xram_layout_t, talk.bubble.palette)
#define XRAM_BUBBLE_TILES offsetof(xram_layout_t, talk.bubble.tiles)
#define XRAM_BUBBLE_MAP offsetof(xram_layout_t, talk.bubble.map)
#define XRAM_BRICK_IMAGE offsetof(xram_layout_t, brick_image)
#define XRAM_NUGGET_IMAGE offsetof(xram_layout_t, nugget_image)
#define XRAM_NUGGET_ICON_IMAGE offsetof(xram_layout_t, nugget_icon_image)
#define XRAM_BALL_IMAGE offsetof(xram_layout_t, ball_image)
#define XRAM_BALL_ICON_IMAGE offsetof(xram_layout_t, ball_icon_image)
#define XRAM_COIN_IMAGE offsetof(xram_layout_t, coin_image)
#define XRAM_CURSOR_IMAGE offsetof(xram_layout_t, cursor_image)
#define XRAM_JET_IMAGES offsetof(xram_layout_t, jet_images)
#define XRAM_SMOKE_IMAGES offsetof(xram_layout_t, smoke_images)
#define XRAM_ENERGY_IMAGES offsetof(xram_layout_t, energy_images)
#define XRAM_DIGIT_IMAGES offsetof(xram_layout_t, digit_images)
#define XRAM_MACHINE_IMAGE offsetof(xram_layout_t, machine_image)
#define XRAM_ART offsetof(xram_layout_t, art)
#define XRAM_BACKDROP offsetof(xram_layout_t, art.menu.top)
#define XRAM_BAND_PALETTE(band) offsetof(xram_layout_t, art.menu.band.palette)
#define XRAM_BAND_TILES(band) offsetof(xram_layout_t, art.menu.band.tiles)
#define XRAM_BAND_MAP(band) offsetof(xram_layout_t, art.menu.band.map)
#define XRAM_BACKDROP_SPRITES offsetof(xram_layout_t, art.menu.backdrop_sprites)
#define XRAM_PICTURE(slot) (offsetof(xram_layout_t, art.menu.pictures) + (slot) * PICTURE_BYTES)
#define XRAM_PANEL_PALETTE offsetof(xram_layout_t, art.menu.panel_palette)
#define XRAM_PANEL_TILES offsetof(xram_layout_t, art.menu.panel_tiles)
#define XRAM_PANELS offsetof(xram_layout_t, art.menu.panels)
#define XRAM_CART_PALETTE offsetof(xram_layout_t, art.menu.cart_palette)
#define XRAM_CART_TILES offsetof(xram_layout_t, art.menu.cart_tiles)
#define XRAM_LOCK_PALETTE offsetof(xram_layout_t, art.menu.lock_palette)
#define XRAM_LOCK_IMAGE offsetof(xram_layout_t, art.menu.lock_image)
#define XRAM_LOCK_HALVES offsetof(xram_layout_t, art.menu.lock_halves)
#define XRAM_CART_MAP offsetof(xram_layout_t, art.menu.cart_map)
#define XRAM_TEXTURE offsetof(xram_layout_t, art.cave.texture)
#define XRAM_CURTAINS offsetof(xram_layout_t, art.cave.curtains)
#define XRAM_FRAME offsetof(xram_layout_t, art.cave.level.frame)
#define XRAM_FRAME_PALETTE offsetof(xram_layout_t, art.cave.level.frame.palette)
#define XRAM_FRAME_SHADE offsetof(xram_layout_t, art.cave.level.frame.shade)
#define XRAM_FRAME_SHOWS offsetof(xram_layout_t, art.cave.level.frame.shows) /* and the repeat after it */
#define XRAM_POST_IMAGE offsetof(xram_layout_t, art.cave.level.frame.post)
#define XRAM_BEAM_IMAGE offsetof(xram_layout_t, art.cave.level.frame.beam)
#define XRAM_CAP_IMAGE offsetof(xram_layout_t, art.cave.level.frame.cap)
#define XRAM_BRACE_IMAGE offsetof(xram_layout_t, art.cave.level.frame.brace)
#define XRAM_CRACK_IMAGES offsetof(xram_layout_t, art.cave.level.cracks)
#define XRAM_CHUNK_IMAGES offsetof(xram_layout_t, art.cave.level.chunks)
#define XRAM_LEVEL_SPRITES offsetof(xram_layout_t, art.cave.level.sprites)
#define XRAM_CRACK_SPRITES offsetof(xram_layout_t, art.cave.level.sprites.cracks)
#define XRAM_CHUNK_SPRITES offsetof(xram_layout_t, art.cave.level.sprites.chunks)
#define XRAM_BALL_SPRITE offsetof(xram_layout_t, art.cave.level.sprites.actors.ball)
#define XRAM_SLED_SPRITE offsetof(xram_layout_t, art.cave.level.sprites.actors.sled)
#define XRAM_JET_SPRITES offsetof(xram_layout_t, art.cave.level.sprites.actors.jets)
#define XRAM_SMOKE_SPRITES offsetof(xram_layout_t, art.cave.level.sprites.actors.smoke)
#define XRAM_GAUGE_ART offsetof(xram_layout_t, art.cave.level.gauge)
#define XRAM_FITTING_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.fitting)
#define XRAM_LIQUID_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.liquid)
#define XRAM_SURFACE_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.surface)
#define XRAM_BUBBLE_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.bubble)
#define XRAM_DROP_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.drop)
#define XRAM_METER_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.meter)
#define XRAM_GLASS_IMAGE offsetof(xram_layout_t, art.cave.level.gauge.glass)
#define XRAM_BIG_COIN_PALETTE offsetof(xram_layout_t, art.cave.level.big_coin_palette)
#define XRAM_BIG_COIN_IMAGE offsetof(xram_layout_t, art.cave.level.big_coin)
#define XRAM_LEVEL_SLED offsetof(xram_layout_t, art.cave.sled_images)
#define XRAM_LOGO_IMAGES offsetof(xram_layout_t, art.cave.title.logo_images)
#define XRAM_TITLE_PALETTE offsetof(xram_layout_t, art.cave.title.panel_palette)
#define XRAM_TITLE_TILES offsetof(xram_layout_t, art.cave.title.panel_tiles)
#define XRAM_TITLE_MAP offsetof(xram_layout_t, art.cave.title.panel_map)

MODE5_PALETTE_CHECK(palettes_t);

#define PALETTES_BYTES sizeof(palettes_t) /* for tests/assets.py */

PSG_PAGE_CHECK(XRAM_PSG);

_Static_assert(sizeof(xram_layout_t) <= 0x10000, "XRAM holds 64 KB.");

/* video_init() hides every sprite from XRAM_SCENERY up to XRAM_MENU_MAP, and
   plane 0 draws the scenery and the bricks as one list. A level's plane 1
   sprites are in its own art, and it hides them itself. */
_Static_assert(XRAM_BRICKS == XRAM_SCENERY + sizeof(scenery_t), "The bricks must follow the scenery.");
_Static_assert(XRAM_MENU_MAP == XRAM_BRICKS + (BRICKS_MAX * sizeof(mode5_csprite_t) +
                                               sizeof(locks_t) + sizeof(hud_t)),
               "The sprite lists must lie together, before the menus' map.");

#endif
