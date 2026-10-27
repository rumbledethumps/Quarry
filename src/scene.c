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
   when the screen starts. The upgrade screen has the rock tiles and every
   sled. The title has a texture, a curtain set and the logo, and a stage a
   texture, a curtain set and its own sled. The texture and the curtain set
   are picked at random only when the screen changes, so a stage played
   again, or the next one, keeps its rock, and nobody sees it change. */

#define SCENE_MENU 1
#define SCENE_STAGE 2
#define SCENE_TITLE 3

/* The curtain sets, ROM:curtain1 and on, and the textures, ROM:texture1
   and on. A curtain set holds its palette, then the 4 colors of the
   texture, then the curtains. */
#define CURTAIN_SETS 4 /* QUARRY_CURTAIN_SETS of CMakeLists.txt */
#define TEXTURES 4

_Static_assert(CURTAIN_SETS <= 9 && TEXTURES <= 9, "An asset's name has one digit.");

static uint8_t scene;
static uint8_t curtain_set; /* the one shown, from 0 */

/* A new screen starts on a blank canvas, so nothing is left of the last
   one, such as the upgrade screen's panels on plane 1. Returns whether
   the screen changed. */
static uint8_t scene_change(uint8_t to)
{
    if (scene == to)
        return 0;
    scene = to;
    video_start();
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

/* The upgrade screen: rock tiles on plane 0, and the panels on plane 1 from
   PANEL_Y, which the upgrade screen scrolls: their palette, their tiles
   and the map of their frames, with plain plates for the upgrade screen
   to fill in. */
void scene_menu(void)
{
    mode2_config_t config;

    if (!scene_change(SCENE_MENU))
        return;
    load("ROM:tiles", 0, XRAM_TILES, sizeof(((xram_layout_t *)0)->art.menu.tiles));
    load("ROM:sleds", 0, XRAM_SLED_IMAGES, sizeof(((xram_layout_t *)0)->art.menu.sled_images));
    xreg_vga_mode2(MODE2_4BPP | MODE2_16X16, XRAM_TILE_CONFIG, 0);
    load("ROM:panels", 0, XRAM_PANEL_PALETTE, XRAM_TILE_MAP - XRAM_PANEL_PALETTE);
    memset(&config, 0, sizeof config);
    config.y_pos_px = PANEL_Y;
    config.width_tiles = PANEL_MAP_COLS;
    config.height_tiles = PANEL_ROWS;
    config.xram_data_ptr = XRAM_PANELS;
    config.xram_palette_ptr = XRAM_PANEL_PALETTE;
    config.xram_tile_ptr = XRAM_PANEL_TILES;
    xram0_write(XRAM_PANEL_CONFIG, &config, sizeof config);
    xreg_vga_mode2(MODE2_8BPP | MODE2_8X8, XRAM_PANEL_CONFIG, 1, PANEL_Y, PANEL_Y + PANEL_ROWS * 8);
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
   picked at random. The texture takes its colors from the curtain set. */
static void cave(void)
{
    char texture[] = "ROM:texture1";
    unsigned long noise = ria_attr_get(RIA_ATTR_LRAND);

    texture[11] = '1' + noise % TEXTURES;
    noise /= TEXTURES;
    curtain_set = noise % CURTAIN_SETS;
    noise /= CURTAIN_SETS;
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
        cave();
    load("ROM:logo", 0, XRAM_LOGO_IMAGES, sizeof(((xram_layout_t *)0)->art.cave.logo_images));
}

/* A stage: a cave, if it comes from another screen, and the sled of a
   level of the width upgrade. */
void scene_stage(uint8_t sled_level)
{
    if (scene_change(SCENE_STAGE))
        cave();
    load("ROM:sleds", (long)sled_level * SLED_SLOT, XRAM_STAGE_SLED, SLED_SLOT);
}

/* The curtain set after this one, or before it, in its place, while the
   screen shows. It loads as it shows, and may tear. */
void scene_curtains(int8_t step)
{
    curtain_set = (curtain_set + CURTAIN_SETS + step) % CURTAIN_SETS;
    curtains_load();
}

/* The images of the sled of a level of the width upgrade, on this screen. */
unsigned scene_sled(uint8_t level)
{
    return scene == SCENE_STAGE ? XRAM_STAGE_SLED : XRAM_SLED_IMAGES + level * SLED_SLOT;
}
