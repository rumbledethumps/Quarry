#include "scene.h"
#include "debug.h"
#include "video.h"
#include "xram.h"
#include <fcntl.h>
#include <rp6502.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* Each screen has art of its own in XRAM_ART, read from the ROM's assets
   when the screen starts. The upgrade screen has its backdrop, its panels
   and carts, and slots for the pictures of the panels near the middle,
   which load as the panels come near. The title has a texture, a curtain set and the logo, and a stage a
   texture, a curtain set, a frame set and its own sled. The texture, the
   curtain set and the frame set are picked at random only when the screen
   changes, so a stage played again keeps its rock and its frame, and
   nobody sees them change. */

#define SCENE_MENU 1
#define SCENE_STAGE 2
#define SCENE_TITLE 3

/* The curtain sets, ROM:curtain1 and on, and the textures, ROM:texture1
   and on. A curtain set holds its palette, then the 4 colors of the
   texture, then the curtains. */
#define CURTAIN_SETS 4 /* QUARRY_CURTAIN_SETS of CMakeLists.txt */
#define TEXTURES 4

/* The frame sets, ROM:frame1 and on, each a frame_set_t. */
#define FRAME_SETS 1 /* QUARRY_FRAME_SETS of CMakeLists.txt */

_Static_assert(CURTAIN_SETS <= 9 && TEXTURES <= 9 && FRAME_SETS <= 9, "An asset's name has one digit.");

static uint8_t scene;
static uint8_t curtain_set; /* the one shown, from 0 */
static uint8_t frame_set;   /* the one a stage shows, from 0 */
static uint8_t menu_shown;  /* whether the upgrade screen's planes are on */

/* Waits for the start of the next frame. */
static void next_frame(void)
{
    uint8_t vsync = ria_vsync();

    while (ria_vsync() == vsync)
        ;
}

/* A new screen starts on a blank canvas, so nothing is left of the last
   one, at the start of a frame, so the last one shows whole until then.
   Returns whether the screen changed. */
static uint8_t scene_change(uint8_t to)
{
    if (scene == to)
        return 0;
    scene = to;
    next_frame();
    video_blank();
    return 1;
}

/* Reads count bytes of a ROM asset, from offset, into XRAM at xaddr. */
static void load(const char *path, long offset, unsigned xaddr, unsigned count)
{
    int fd = open(path, O_RDONLY);

    if (fd < 0)
    {
        DEBUG_LOG("no %s\n", path);
        return;
    }
    if (offset)
        lseek(fd, offset, SEEK_SET);
    while (count)
    {
        int n = read_xram(xaddr, count < 0x7FFF ? count : 0x7FFF, fd);
        if (n <= 0)
            break;
        xaddr += n;
        count -= n;
    }
    close(fd);
}

/* A band of the backdrop on plane 0, from scanline top, rows of tiles down. */
static void backdrop_band(uint8_t band, unsigned palette, unsigned tiles, unsigned map, int16_t top, uint8_t rows)
{
    mode2_config_t config;

    memset(&config, 0, sizeof config);
    config.y_pos_px = top;
    config.width_tiles = BACKDROP_COLS;
    config.height_tiles = rows;
    config.xram_data_ptr = map;
    config.xram_palette_ptr = palette;
    config.xram_tile_ptr = tiles;
    xram0_write(XRAM_BACKDROP_CONFIG(band), &config, sizeof config);
}

/* The upgrade screen's art and its layers: the backdrop for plane 0, in
   its three bands, and for plane 1 the panels from PANEL_Y and the carts
   from CART_Y, which the upgrade screen slides and fills in: the panels'
   palette, tiles and the map of their frames, and the carts' palette and
   tiles. Nothing shows until scene_menu_show(), once the upgrade screen
   has put everything in its place. */
void scene_menu(void)
{
    mode2_config_t config;

    if (!scene_change(SCENE_MENU))
        return;
    load("ROM:backdrop", 0, XRAM_BACKDROP, XRAM_PICTURE(0) - XRAM_BACKDROP);
    menu_shown = 0;
    backdrop_band(0, XRAM_BAND_PALETTE(top), XRAM_BAND_TILES(top), XRAM_BAND_MAP(top), BACKDROP_TOP_Y,
                  BACKDROP_TOP_ROWS);
    backdrop_band(1, XRAM_BAND_PALETTE(middle), XRAM_BAND_TILES(middle), XRAM_BAND_MAP(middle),
                  BACKDROP_MIDDLE_Y, BACKDROP_MIDDLE_ROWS);
    backdrop_band(2, XRAM_BAND_PALETTE(bottom), XRAM_BAND_TILES(bottom), XRAM_BAND_MAP(bottom),
                  BACKDROP_BOTTOM_Y, BACKDROP_BOTTOM_ROWS);
    load("ROM:panels", 0, XRAM_PANEL_PALETTE, XRAM_CART_PALETTE - XRAM_PANEL_PALETTE);
    memset(&config, 0, sizeof config);
    config.y_pos_px = PANEL_Y;
    config.width_tiles = PANEL_MAP_COLS;
    config.height_tiles = PANEL_ROWS;
    config.xram_data_ptr = XRAM_PANELS;
    config.xram_palette_ptr = XRAM_PANEL_PALETTE;
    config.xram_tile_ptr = XRAM_PANEL_TILES;
    xram0_write(XRAM_PANEL_CONFIG, &config, sizeof config);
    load("ROM:carts", 0, XRAM_CART_PALETTE, XRAM_CART_MAP - XRAM_CART_PALETTE);
    xram0_set(XRAM_CART_MAP, 0, sizeof(((xram_layout_t *)0)->art.menu.cart_map));
    config.y_pos_px = CART_Y;
    config.width_tiles = CART_MAP_COLS;
    config.height_tiles = CART_ROWS;
    config.xram_data_ptr = XRAM_CART_MAP;
    config.xram_palette_ptr = XRAM_CART_PALETTE;
    config.xram_tile_ptr = XRAM_CART_TILES;
    xram0_write(XRAM_CART_CONFIG, &config, sizeof config);
}

#define BAND_MODE(bpp) (((bpp) == 2 ? MODE2_2BPP : MODE2_4BPP) | MODE2_16X16)

/* The upgrade screen shows, all at once, at the start of a frame, once
   everything on it is in its place: its sprites and text, and its layers. */
void scene_menu_show(void)
{
    if (menu_shown)
        return;
    menu_shown = 1;
    next_frame();
    video_start();
    xreg_vga_mode2(BAND_MODE(BACKDROP_TOP_BPP), XRAM_BACKDROP_CONFIG(0), 0, BACKDROP_TOP_Y,
                   BACKDROP_TOP_Y + BACKDROP_TOP_ROWS * 16);
    xreg_vga_mode2(BAND_MODE(BACKDROP_MIDDLE_BPP), XRAM_BACKDROP_CONFIG(1), 0, BACKDROP_MIDDLE_Y,
                   BACKDROP_MIDDLE_Y + BACKDROP_MIDDLE_ROWS * 16);
    xreg_vga_mode2(BAND_MODE(BACKDROP_BOTTOM_BPP), XRAM_BACKDROP_CONFIG(2), 0, BACKDROP_BOTTOM_Y,
                   BACKDROP_BOTTOM_Y + BACKDROP_BOTTOM_ROWS * 16);
    xreg_vga_mode2(MODE2_8BPP | MODE2_8X8, XRAM_PANEL_CONFIG, 1, PANEL_Y, PANEL_Y + PANEL_ROWS * 8);
    xreg_vga_mode2(MODE2_4BPP | MODE2_8X8, XRAM_CART_CONFIG, 1, CART_Y, CART_Y + CART_ROWS * 8);
}

/* The curtain set: its palette, the colors it gives the texture, and its
   curtains. */
static void curtains_load(void)
{
    char curtain[] = "ROM:curtain1";
    unsigned palette = sizeof(((palettes_t *)0)->curtain);

    curtain[11] = '1' + curtain_set;
    load(curtain, 0, XRAM_PALETTE_CURTAIN, palette);
    load(curtain, palette, XRAM_PALETTE_TEXTURE, 4 * sizeof(uint16_t));
    load(curtain, palette + 4 * sizeof(uint16_t), XRAM_CURTAINS, 2 * CURTAIN_BYTES);
    DEBUG_LOG("curtains %u\n", curtain_set + 1);
}

/* A texture on plane 0, shown from a new place, and a curtain set, both
   picked at random, and the frame set a stage shows, too. The texture
   takes its colors from the curtain set. */
static void cave(void)
{
    char texture[] = "ROM:texture1";
    unsigned long noise = ria_attr_get(RIA_ATTR_LRAND);

    texture[11] = '1' + noise % TEXTURES;
    noise /= TEXTURES;
    curtain_set = noise % CURTAIN_SETS;
    noise /= CURTAIN_SETS;
    frame_set = noise % FRAME_SETS;
    noise /= FRAME_SETS;
    load(texture, 0, XRAM_TEXTURE, sizeof(((xram_layout_t *)0)->art.cave.texture));
    curtains_load();
    xram0_poke16(XRAM_TEXTURE_CONFIG + offsetof(mode3_config_t, x_pos_px), -(int16_t)(noise % TEXTURE_W));
    noise /= TEXTURE_W;
    xram0_poke16(XRAM_TEXTURE_CONFIG + offsetof(mode3_config_t, y_pos_px), -(int16_t)(noise % TEXTURE_H));
    xreg_vga_mode3(MODE3_2BPP, XRAM_TEXTURE_CONFIG, 0);
}

/* The title: a cave, if it comes from another screen, and the logo. */
void scene_title(void)
{
    if (scene_change(SCENE_TITLE))
    {
        video_start();
        cave();
    }
    load("ROM:logo", 0, XRAM_LOGO_IMAGES, sizeof(((xram_layout_t *)0)->art.cave.logo_images));
}

/* A stage: a cave and its frame set, if it comes from another screen, and
   the sled of a level of the width upgrade. */
void scene_stage(uint8_t sled_level)
{
    if (scene_change(SCENE_STAGE))
    {
        char frame[] = "ROM:frame1";

        video_start();
        cave();
        frame[9] = '1' + frame_set;
        load(frame, 0, XRAM_FRAME, sizeof(frame_set_t));
        DEBUG_LOG("frame %u\n", frame_set + 1);
    }
    load("ROM:sleds", (long)sled_level * SLED_SLOT, XRAM_STAGE_SLED, SLED_SLOT);
}

/* The curtain set after this one, or before it, in its place, while the
   screen shows. It loads as it shows, and may tear. */
void scene_curtains(int8_t step)
{
    curtain_set = (curtain_set + CURTAIN_SETS + step) % CURTAIN_SETS;
    curtains_load();
}

/* The flat sled of a level of the width upgrade into a slot of the upgrade
   screen's pictures. */
void scene_picture_sled(uint8_t slot, uint8_t level)
{
    load("ROM:sleds", (long)level * SLED_SLOT, XRAM_PICTURE(slot), PICTURE_BYTES);
}
