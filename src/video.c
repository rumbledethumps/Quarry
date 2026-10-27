#include "video.h"
#include "xram.h"
#include <string.h>

/* Every sprite starts hidden, and the fill layers start blank, so nothing
   but what the game sets up is drawn when the modes are programmed. */
void video_init(void)
{
    mode2_config_t tile_config;
    mode3_config_t texture_config;
    mode1_config_t text_config;

    video_hide_sprites();

    xram0_set(XRAM_TILE_MAP, TILE_ROCK, sizeof(((xram_layout_t *)0)->art.menu.tile_map));
    video_text_clear();

    memset(&tile_config, 0, sizeof tile_config);
    tile_config.width_tiles = TILE_MAP_COLS;
    tile_config.height_tiles = TILE_MAP_ROWS;
    tile_config.xram_data_ptr = XRAM_TILE_MAP;
    tile_config.xram_palette_ptr = XRAM_PALETTE_MAIN;
    tile_config.xram_tile_ptr = XRAM_TILES;
    xram0_write(XRAM_TILE_CONFIG, &tile_config, sizeof tile_config);

    memset(&texture_config, 0, sizeof texture_config);
    texture_config.x_wrap = true;
    texture_config.y_wrap = true;
    texture_config.width_px = TEXTURE_W;
    texture_config.height_px = TEXTURE_H;
    texture_config.xram_data_ptr = XRAM_TEXTURE;
    texture_config.xram_palette_ptr = XRAM_PALETTE_TEXTURE;
    xram0_write(XRAM_TEXTURE_CONFIG, &texture_config, sizeof texture_config);

    memset(&text_config, 0, sizeof text_config);
    text_config.width_chars = TEXT_COLS;
    text_config.height_chars = TEXT_ROWS;
    text_config.xram_data_ptr = XRAM_TEXT;
    text_config.xram_palette_ptr = XRAM_PALETTE_MAIN;
    text_config.xram_font_ptr = 0xFFFF;
    xram0_write(XRAM_TEXT_CONFIG, &text_config, sizeof text_config);
}

/* Planes, back to front:
   0: the rock tiles of the upgrade screen, or the texture of the title and
      a stage, which each screen programs itself, with the scenery and the
      bricks over it.
   1: the paddle, its flames and smoke, and the ball.
   2: menu text, with the gauge, the counts and the upgrade screen's
      pictures over it. */
void video_start(void)
{
    xreg_vga_canvas(CANVAS_320X240);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_SCENERY,
                   sizeof(scenery_t) / sizeof(mode5_csprite_t) + BRICKS_MAX, 0);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_ACTORS, sizeof(actors_t) / sizeof(mode5_csprite_t), 1);
    xreg_vga_mode1(MODE1_4BPP, XRAM_TEXT_CONFIG, 2);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_HUD, sizeof(hud_t) / sizeof(mode5_csprite_t), 2);
}

/* A kind of rock for each cell, from a hash of the cell, so the rock has
   no pattern that repeats across or down. */
static uint8_t rock_at(uint8_t col, uint8_t row)
{
    uint8_t h = col * 151 + row * 101;

    h ^= h >> 3;
    h *= 37;
    h ^= h >> 2;
    return TILE_ROCK + h % TILE_ROCKS;
}

/* Rock all over, for a screen with no playfield. */
void video_rock(void)
{
    uint8_t cells[TILE_MAP_COLS];
    uint8_t col, row;

    for (row = 0; row < TILE_MAP_ROWS; row++)
    {
        for (col = 0; col < TILE_MAP_COLS; col++)
            cells[col] = rock_at(col, row);
        xram0_write(XRAM_TILE_MAP + row * TILE_MAP_COLS, cells, TILE_MAP_COLS);
    }
    xram0_poke16(XRAM_TILE_CONFIG + offsetof(mode2_config_t, x_pos_px), -16); /* a tile */
}

/* Every sprite of every plane, as a plain hidden sprite. Whatever shows a
   sprite again sets it up first. */
void video_hide_sprites(void)
{
    unsigned sprite;

    for (sprite = XRAM_SCENERY; sprite < XRAM_TEXT; sprite += sizeof(mode5_csprite_t))
        sprite_set(sprite, XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
}

/* Blank cells are glyph 0 with transparent colors. */
void video_text_clear(void)
{
    xram0_set(XRAM_TEXT, 0, sizeof(((xram_layout_t *)0)->text));
}

/* Blank cells from left, top to right, bottom. */
void video_clear(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom)
{
    uint8_t row;

    if (right < left || right >= TEXT_COLS || bottom >= TEXT_ROWS)
        return;
    for (row = top; row <= bottom; row++)
        xram0_set(XRAM_TEXT + (row * TEXT_COLS + left) * sizeof(mode1_4bpp_data_t), 0,
                  (right - left + 1) * sizeof(mode1_4bpp_data_t));
}

/* Text in fg, on bg. */
void video_text(uint8_t col, uint8_t row, const char *s, uint8_t fg, uint8_t bg)
{
    mode1_4bpp_data_t cells[TEXT_COLS];
    uint8_t n = 0;

    while (s[n] && col + n < TEXT_COLS)
    {
        cells[n].glyph_code = s[n];
        cells[n].bg_fg_index = MODE1_BG_FG(bg, fg);
        n++;
    }
    xram0_write(XRAM_TEXT + (row * TEXT_COLS + col) * sizeof(mode1_4bpp_data_t),
                cells, n * sizeof(mode1_4bpp_data_t));
}

/* A number, left aligned in width cells, spaces after it. */
void video_number(uint8_t col, uint8_t row, uint16_t n, uint8_t width, uint8_t fg, uint8_t bg)
{
    char text[6];
    uint8_t i, len = 0;

    do
    {
        text[len++] = '0' + n % 10;
        n /= 10;
    } while (n);
    for (i = 0; i < len / 2; i++)
    {
        char c = text[i];
        text[i] = text[len - 1 - i];
        text[len - 1 - i] = c;
    }
    while (len < width)
        text[len++] = ' ';
    text[len] = 0;
    video_text(col, row, text, fg, bg);
}

/* Draws a dark box with a frame in color, in text cells from left, top to
   right, bottom. The frame is the line-drawing glyphs of code page 437. A
   frame in BOX_FILL can't be seen. */
void video_box(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom, uint8_t color)
{
    mode1_4bpp_data_t cells[TEXT_COLS];
    uint8_t row, col, n = right - left + 1;

    for (row = top; row <= bottom; row++)
    {
        for (col = 0; col < n; col++)
        {
            uint8_t end = col == 0 ? 0 : col == n - 1 ? 2 : 1;
            static const uint8_t top_glyphs[] = {0xDA, 0xC4, 0xBF};
            static const uint8_t middle_glyphs[] = {0xB3, ' ', 0xB3};
            static const uint8_t bottom_glyphs[] = {0xC0, 0xC4, 0xD9};
            cells[col].glyph_code = row == top      ? top_glyphs[end]
                                    : row == bottom ? bottom_glyphs[end]
                                                    : middle_glyphs[end];
            cells[col].bg_fg_index = MODE1_BG_FG(BOX_FILL, color);
        }
        xram0_write(XRAM_TEXT + (row * TEXT_COLS + left) * sizeof(mode1_4bpp_data_t),
                    cells, n * sizeof(mode1_4bpp_data_t));
    }
}

/* A 4-bit custom sprite, hidden until it is moved. */
void sprite_set(unsigned sprite, unsigned image, unsigned palette, uint8_t width_height)
{
    mode5_csprite_t s;

    s.x_pos_px = 0;
    s.y_pos_px = SPRITE_HIDDEN_Y;
    s.xram_sprite_ptr = image;
    s.palette_ptr = palette;
    s.width_height = width_height;
    s.attributes = MODE5_4BPP;
    xram0_write(sprite, &s, sizeof s);
}

void sprite_move(unsigned sprite, int16_t x, int16_t y)
{
    int16_t pos[2];

    pos[0] = x;
    pos[1] = y;
    xram0_write(sprite, pos, sizeof pos);
}

void sprite_hide(unsigned sprite)
{
    xram0_poke16(sprite + offsetof(mode5_csprite_t, y_pos_px), SPRITE_HIDDEN_Y);
}

/* Mirrors a sprite left to right. */
void sprite_flip(unsigned sprite)
{
    sprite_attributes(sprite, MODE5_HFLIP);
}

/* A 4-bit sprite's flips and doubling: MODE5_HFLIP, MODE5_VFLIP,
   MODE5_HDOUBLE and MODE5_VDOUBLE. */
void sprite_attributes(unsigned sprite, uint8_t attributes)
{
    xram0_poke8(sprite + offsetof(mode5_csprite_t, attributes), MODE5_4BPP | attributes);
}

/* A count in outlined digits, from the count sprites from first, with its
   top left at x, y. Each digit's outline overlaps the last one's, and the
   sprites it doesn't need are hidden. */
void video_count(unsigned first, uint8_t sprites, int16_t x, int16_t y, uint16_t n)
{
    uint8_t digits[5];
    uint8_t len = 0, i;

    do
    {
        digits[len++] = n % 10;
        n /= 10;
    } while (n && len < sizeof digits);
    for (i = 0; i < sprites; i++)
    {
        unsigned sprite = first + i * sizeof(mode5_csprite_t);
        sprite_set(sprite, XRAM_DIGIT_IMAGES + (i < len ? digits[len - 1 - i] : 0) * sizeof(digit_image_t),
                   XRAM_PALETTE_SLED, MODE5_SIZE(8, 12));
        if (i < len)
            sprite_move(sprite, x + i * DIGIT_ADVANCE, y);
    }
}
