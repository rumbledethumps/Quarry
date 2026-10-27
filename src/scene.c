#include "scene.h"
#include "debug.h"
#include "video.h"
#include "xram.h"
#include <fcntl.h>
#include <rp6502.h>
#include <stdio.h>
#include <unistd.h>

/* Each screen has art of its own in XRAM_ART, read from the ROM's assets
   when the screen starts. The upgrade screen has the rock tiles and every
   sled. The title has a texture, a curtain set and the logo, and a stage a
   texture, a curtain set and its own sled. */

#define SCENE_MENU 1
#define SCENE_STAGE 2
#define SCENE_TITLE 3

/* The curtain sets, ROM:curtain1 and on, and the textures, ROM:texture1
   and on. A curtain set holds its palette, then the 4 colors of the
   texture, then the curtains. */
#define CURTAIN_SETS 1
#define TEXTURES 4

static uint8_t scene;

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

/* The upgrade screen: rock tiles on plane 0. */
void scene_menu(void)
{
    if (scene == SCENE_MENU)
        return;
    scene = SCENE_MENU;
    load("ROM:tiles", 0, XRAM_TILES, sizeof(((xram_layout_t *)0)->art.menu.tiles));
    load("ROM:sleds", 0, XRAM_SLED_IMAGES, sizeof(((xram_layout_t *)0)->art.menu.sled_images));
    xreg_vga_mode2(MODE2_4BPP | MODE2_16X16, XRAM_TILE_CONFIG, 0);
}

/* A texture on plane 0, shown from a new place, and a curtain set, both
   picked at random. The texture takes its colors from the curtain set. */
static void cave(void)
{
    char curtain[] = "ROM:curtain1";
    char texture[] = "ROM:texture1";
    unsigned long noise = ria_attr_get(RIA_ATTR_LRAND);
    unsigned palette = sizeof(((palettes_t *)0)->curtain);

    texture[11] = '1' + noise % TEXTURES;
    noise /= TEXTURES;
    curtain[11] = '1' + noise % CURTAIN_SETS;
    noise /= CURTAIN_SETS;
    load(texture, 0, XRAM_TEXTURE, sizeof(((xram_layout_t *)0)->art.cave.texture));
    load(curtain, 0, XRAM_PALETTE_CURTAIN, palette);
    load(curtain, palette, XRAM_PALETTE_TEXTURE, 4 * sizeof(uint16_t));
    load(curtain, palette + 4 * sizeof(uint16_t), XRAM_CURTAINS, 2 * CURTAIN_BYTES);
    xram0_poke16(XRAM_TEXTURE_CONFIG + offsetof(mode3_config_t, x_pos_px), -(int16_t)(noise % TEXTURE_W));
    noise /= TEXTURE_W;
    xram0_poke16(XRAM_TEXTURE_CONFIG + offsetof(mode3_config_t, y_pos_px), -(int16_t)(noise % TEXTURE_H));
    xreg_vga_mode3(MODE3_2BPP, XRAM_TEXTURE_CONFIG, 0);
}

/* The title: a cave and the logo. */
void scene_title(void)
{
    scene = SCENE_TITLE;
    cave();
    load("ROM:logo", 0, XRAM_LOGO_IMAGES, sizeof(((xram_layout_t *)0)->art.cave.logo_images));
}

/* A stage: a cave and the sled of a level of the width upgrade. */
void scene_stage(uint8_t sled_level)
{
    scene = SCENE_STAGE;
    cave();
    load("ROM:sleds", (long)sled_level * SLED_SLOT, XRAM_STAGE_SLED, SLED_SLOT);
}

/* The images of the sled of a level of the width upgrade, on this screen. */
unsigned scene_sled(uint8_t level)
{
    return scene == SCENE_STAGE ? XRAM_STAGE_SLED : XRAM_SLED_IMAGES + level * SLED_SLOT;
}
