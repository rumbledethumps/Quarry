#include "video.h"
#include "xram.h"
#include <string.h>

/* Every sprite starts hidden, and the fill layers start blank, so nothing
   but what the game sets up is drawn when the modes are programmed. */
void video_init(void)
{
    mode2_config_t tile_config;
    mode1_config_t text_config;
    unsigned sprite;

    for (sprite = XRAM_BRICKS; sprite < XRAM_TEXT; sprite += sizeof(mode5_csprite_t))
        sprite_set(sprite, XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));

    xram0_set(XRAM_TILE_MAP, TILE_ROCK, sizeof(((xram_layout_t *)0)->tile_map));
    video_text_clear();

    memset(&tile_config, 0, sizeof tile_config);
    tile_config.width_tiles = TILE_MAP_COLS;
    tile_config.height_tiles = TILE_MAP_ROWS;
    tile_config.xram_data_ptr = XRAM_TILE_MAP;
    tile_config.xram_palette_ptr = XRAM_PALETTE_MAIN;
    tile_config.xram_tile_ptr = XRAM_TILES;
    xram0_write(XRAM_TILE_CONFIG, &tile_config, sizeof tile_config);

    memset(&text_config, 0, sizeof text_config);
    text_config.width_chars = TEXT_COLS;
    text_config.height_chars = TEXT_ROWS;
    text_config.xram_data_ptr = XRAM_TEXT;
    text_config.xram_palette_ptr = XRAM_PALETTE_MAIN;
    text_config.xram_font_ptr = 0xFFFF;
    xram0_write(XRAM_TEXT_CONFIG, &text_config, sizeof text_config);
}

/* Planes, back to front:
   0: background tiles, with the bricks over them.
   1: the paddle and the ball.
   2: panel and menu text, with the panel icons over it. */
void video_start(void)
{
    xreg_vga_canvas(CANVAS_320X240);
    xreg_vga_mode2(MODE2_4BPP | MODE2_16X16, XRAM_TILE_CONFIG, 0);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_BRICKS, BRICKS_MAX, 0);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_ACTORS, ACTORS_MAX, 1);
    xreg_vga_mode1(MODE1_4BPP, XRAM_TEXT_CONFIG, 2);
    xreg_vga_mode5(MODE5_CUSTOM, XRAM_BALL_ICONS, BALL_ICONS_MAX, 2);
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

/* Draws the walls around a playfield with these inner edges, which must
   be a whole number of tiles apart. The tile map scrolls left by up to a
   tile, so the tiles line up with the walls. The top wall is the first row
   of tiles, and the side walls run to the bottom of the screen, which is
   open. Every other wall tile has a rivet plate. Outside the walls is
   rock. */
void video_walls(int16_t left, int16_t right)
{
    uint8_t cells[TILE_MAP_COLS];
    int16_t scroll = (left & (WALL_SIZE - 1)) - WALL_SIZE;
    uint8_t col, row;

    for (row = 0; row < TILE_MAP_ROWS; row++)
    {
        for (col = 0; col < TILE_MAP_COLS; col++)
        {
            int16_t x = scroll + col * WALL_SIZE;
            uint8_t plate = (row + col) & 1;
            uint8_t tile;
            if (x == left - WALL_SIZE)
                tile = row ? TILE_WALL_LEFT + plate : TILE_CORNER_LEFT;
            else if (x == right)
                tile = row ? TILE_WALL_RIGHT + plate : TILE_CORNER_RIGHT;
            else if (x >= left && x < right)
                tile = row ? TILE_FLOOR : TILE_WALL_TOP + plate;
            else
                tile = rock_at(col, row);
            cells[col] = tile;
        }
        xram0_write(XRAM_TILE_MAP + row * TILE_MAP_COLS, cells, TILE_MAP_COLS);
    }
    xram0_poke16(XRAM_TILE_CONFIG + offsetof(mode2_config_t, x_pos_px), scroll);
}

/* Blank cells are glyph 0 with transparent colors. */
void video_text_clear(void)
{
    xram0_set(XRAM_TEXT, 0, sizeof(((xram_layout_t *)0)->text));
}

void video_text(uint8_t col, uint8_t row, const char *s)
{
    mode1_4bpp_data_t cells[TEXT_COLS];
    uint8_t n = 0;

    while (s[n] && col + n < TEXT_COLS)
    {
        cells[n].glyph_code = s[n];
        cells[n].bg_fg_index = MODE1_BG_FG(0, TEXT_COLOR);
        n++;
    }
    xram0_write(XRAM_TEXT + (row * TEXT_COLS + col) * sizeof(mode1_4bpp_data_t),
                cells, n * sizeof(mode1_4bpp_data_t));
}

/* Draws a dark box with a frame, in text cells from left, top to right,
   bottom. The frame is the line-drawing glyphs of code page 437. */
void video_box(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom)
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
            cells[col].bg_fg_index = MODE1_BG_FG(BOX_FILL, BOX_COLOR);
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
    s.options = MODE5_4BPP;
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
