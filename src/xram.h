/* RP6502 XRAM Mapping */

#ifndef XRAM_H
#define XRAM_H

#include <rp6502.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

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

/* Canvas, from the VGA datasheet. */

#define xreg_vga_canvas(...) xreg(1, 0, 0, __VA_ARGS__)

#define CANVAS_CONSOLE 0
#define CANVAS_320X240 1
#define CANVAS_320X180 2
#define CANVAS_640X480 3
#define CANVAS_640X360 4

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

typedef struct
{
    int16_t x_pos_px;
    int16_t y_pos_px;
    uint16_t xram_sprite_ptr;
    uint16_t palette_ptr;
    uint8_t width_height;
    uint8_t options;
} mode5_csprite_t; /* layout */

/* Quarry. */

#define TEXT_COLS 40
#define TEXT_ROWS 30
#define TILE_MAP_COLS 21 /* one more than the canvas, to scroll the walls into place */
#define TILE_MAP_ROWS 15

#define BRICKS_MAX 48      /* plane 0 sprites */
#define PADDLE_PIECES_MAX 8
#define ACTORS_MAX (1 + PADDLE_PIECES_MAX) /* plane 1: ball, paddle */
#define BALL_ICONS_MAX 36  /* plane 2 sprites */

/* Background tiles, 16x16, in the order of art/tiles.png. Each wall tile
   is followed by the same tile with a rivet plate on its girder. */
#define TILE_FLOOR 0
#define TILE_WALL_LEFT 1
#define TILE_WALL_RIGHT 3
#define TILE_WALL_TOP 5
#define TILE_CORNER_LEFT 7
#define TILE_CORNER_RIGHT 8
#define TILE_ROCK 9 /* the first of TILE_ROCKS kinds of rock */
#define TILE_ROCKS 8
#define TILES_COUNT (TILE_ROCK + TILE_ROCKS)

/* Paddle pieces, in the order of art/paddle.png. */
#define PADDLE_LEFT 0
#define PADDLE_MIDDLE 1
#define PADDLE_RIGHT 2

typedef MODE2_TILE(4, 16) tile_t;
typedef MODE5_CUSTOM_IMAGE(4, 24, 8) brick_image_t;
typedef MODE5_CUSTOM_IMAGE(4, 8, 8) piece_image_t;

/* The palettes, in the order of the rows of art/palettes.png. */
typedef struct
{
    uint16_t main[16];
    uint16_t brick_white[16];
} palettes_t;

typedef struct
{
    keyboard_t keyboard;
    gamepad_t gamepad;
    mode2_config_t tile_config;
    mode1_config_t text_config;
    palettes_t palettes;
    mode5_csprite_t bricks[BRICKS_MAX];
    mode5_csprite_t actors[ACTORS_MAX];
    mode5_csprite_t ball_icons[BALL_ICONS_MAX];
    mode1_4bpp_data_t text[TEXT_ROWS][TEXT_COLS];
    tile_t tiles[TILES_COUNT];
    brick_image_t brick_image;
    piece_image_t ball_image;
    piece_image_t paddle_images[3];
    uint8_t tile_map[TILE_MAP_ROWS][TILE_MAP_COLS]; /* an odd size, so last */
} xram_layout_t;

#define XRAM_KEYBOARD offsetof(xram_layout_t, keyboard)
#define XRAM_GAMEPAD offsetof(xram_layout_t, gamepad)
#define XRAM_TILE_CONFIG offsetof(xram_layout_t, tile_config)
#define XRAM_TEXT_CONFIG offsetof(xram_layout_t, text_config)
#define XRAM_PALETTES offsetof(xram_layout_t, palettes)
#define XRAM_PALETTE_MAIN offsetof(xram_layout_t, palettes.main)
#define XRAM_PALETTE_BRICK_WHITE offsetof(xram_layout_t, palettes.brick_white)
#define XRAM_BRICKS offsetof(xram_layout_t, bricks)
#define XRAM_ACTORS offsetof(xram_layout_t, actors)
#define XRAM_BALL_ICONS offsetof(xram_layout_t, ball_icons)
#define XRAM_TILE_MAP offsetof(xram_layout_t, tile_map)
#define XRAM_TEXT offsetof(xram_layout_t, text)
#define XRAM_TILES offsetof(xram_layout_t, tiles)
#define XRAM_BRICK_IMAGE offsetof(xram_layout_t, brick_image)
#define XRAM_BALL_IMAGE offsetof(xram_layout_t, ball_image)
#define XRAM_PADDLE_IMAGES offsetof(xram_layout_t, paddle_images)

_Static_assert(sizeof(palettes_t) / sizeof(uint16_t) <= 512,
               "palettes_t holds more than 512 colors.");

/* video_init() hides every sprite from XRAM_BRICKS up to XRAM_TEXT. */
_Static_assert(XRAM_TEXT == XRAM_BRICKS +
                   (BRICKS_MAX + ACTORS_MAX + BALL_ICONS_MAX) * sizeof(mode5_csprite_t),
               "The sprite lists must lie together, before the text.");

#endif
