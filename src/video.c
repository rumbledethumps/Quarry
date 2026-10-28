#include "video.h"
#include "xram.h"
#include <string.h>

/* Every sprite starts hidden, and the fill layers start blank, so nothing
   but what the game sets up is drawn when the modes are programmed. */
void video_init(void)
{
    mode3_config_t texture_config;
    mode2_config_t menu_config;

    video_hide_sprites();

    video_text_clear();

    memset(&texture_config, 0, sizeof texture_config);
    texture_config.x_wrap = true;
    texture_config.y_wrap = true;
    texture_config.width_px = TEXTURE_W;
    texture_config.height_px = TEXTURE_H;
    texture_config.xram_data_ptr = XRAM_TEXTURE;
    texture_config.xram_palette_ptr = XRAM_PALETTE_TEXTURE;
    xram0_write(XRAM_TEXTURE_CONFIG, &texture_config, sizeof texture_config);

    memset(&menu_config, 0, sizeof menu_config);
    menu_config.width_tiles = TEXT_COLS;
    menu_config.height_tiles = TEXT_ROWS;
    menu_config.xram_data_ptr = XRAM_MENU_MAP;
    menu_config.xram_palette_ptr = XRAM_MENU_PALETTE;
    menu_config.xram_tile_ptr = XRAM_MENU_TILES;
    xram0_write(XRAM_MENU_CONFIG, &menu_config, sizeof menu_config);
}

/* A blank canvas: every plane off, so nothing is left of the last screen,
   such as the upgrade screen's panels on plane 1, and nothing shows until
   the next one programs its planes. */
void video_blank(void)
{
    xreg_vga_canvas(CANVAS_320X240);
}

/* The sprites and the menus on a blank canvas. Planes, back to front:
   0: the backdrop of the upgrade screen, or the texture of the title and
      a level, which each screen programs itself, with the scenery and the
      bricks over it.
   1: the upgrade screen's panels and carts, and the paddle, its flames
      and smoke, and the ball.
   2: the menus, or a dwarf's speech bubble in their place, with the
      gauge, the counts, the upgrade screen's pictures, the dwarf and the
      holographic cursor over them. */
void video_start(void)
{
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_SCENERY,
                   sizeof(scenery_t) / sizeof(mode5_csprite_t) + BRICKS_MAX, 0);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_ACTORS, sizeof(actors_t) / sizeof(mode5_csprite_t), 1);
    video_menus();
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_HUD, sizeof(hud_t) / sizeof(mode5_csprite_t), 2);
}

/* Plane 2's fill: the menus, 4-bit tiles. */
void video_menus(void)
{
    xreg_vga_mode2(MODE2_4BPP | MODE2_8X8, XRAM_MENU_CONFIG, 2);
}

/* Plane 2's fill: a dwarf's speech bubble, 2-bit tiles, in the menus'
   place. */
void video_talk(void)
{
    xreg_vga_mode2(MODE2_2BPP | MODE2_8X8, XRAM_TALK_CONFIG, 2);
}

/* Every sprite of every plane, as a plain hidden sprite. Whatever shows a
   sprite again sets it up first. */
void video_hide_sprites(void)
{
    unsigned sprite;

    for (sprite = XRAM_SCENERY; sprite < XRAM_MENU_MAP; sprite += sizeof(mode5_csprite_t))
        sprite_set(sprite, XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
}

/* Every cell of the menus clear, tile 0. */
void video_text_clear(void)
{
    xram0_set(XRAM_MENU_MAP, 0, sizeof(((xram_layout_t *)0)->menu_map));
}

/* Clear cells from left, top to right, bottom. */
void video_clear(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom)
{
    uint8_t row;

    if (right < left || right >= TEXT_COLS || bottom >= TEXT_ROWS)
        return;
    for (row = top; row <= bottom; row++)
        xram0_set(XRAM_MENU_MAP + row * TEXT_COLS + left, 0, right - left + 1);
}

/* Text in the menus' font, on the inside of a box. A letter the font
   doesn't have is a space. */
void video_text(uint8_t col, uint8_t row, const char *s)
{
    static const char font[] = MENU_FONT;
    uint8_t cells[TEXT_COLS];
    uint8_t n = 0;

    while (s[n] && col + n < TEXT_COLS)
    {
        const char *at = strchr(font, s[n]);
        cells[n] = MENU_TILE_GLYPH + (at && s[n] ? at - font : 0);
        n++;
    }
    xram0_write(XRAM_MENU_MAP + row * TEXT_COLS + col, cells, n);
}

/* A number, left aligned in width cells, spaces after it. */
void video_number(uint8_t col, uint8_t row, uint16_t n, uint8_t width)
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
    video_text(col, row, text);
}

/* A thin steel rule across the cells from left to right, on row. */
void video_rule(uint8_t left, uint8_t right, uint8_t row)
{
    xram0_set(XRAM_MENU_MAP + row * TEXT_COLS + left, MENU_TILE_RULE, right - left + 1);
}

/* A dark box in cells from left, top to right, bottom: framed in caution
   tape and steel, or BOX_PLAIN, without. */
void video_box(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom, uint8_t frame)
{
    uint8_t cells[TEXT_COLS];
    uint8_t row, col, n = right - left + 1;

    for (row = top; row <= bottom; row++)
    {
        for (col = 0; col < n; col++)
        {
            /* The frame's tiles: the corners, then the edges, as art/menus.py
               lays them out. */
            uint8_t edge_row = row == top ? 0 : row == bottom ? 2 : 1;
            uint8_t edge_col = col == 0 ? 0 : col == n - 1 ? 2 : 1;
            static const uint8_t pieces[3][3] = {{0, 4, 1}, {6, 0xFF, 7}, {2, 5, 3}};
            uint8_t piece = pieces[edge_row][edge_col];
            cells[col] = frame == BOX_PLAIN || piece == 0xFF ? MENU_TILE_GLYPH : MENU_TILE_FRAME + piece;
        }
        xram0_write(XRAM_MENU_MAP + row * TEXT_COLS + left, cells, n);
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
