#include "title.h"
#include "bricks.h"
#include "cursor.h"
#include "frame.h"
#include "input.h"
#include "save.h"
#include "scene.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"

/* The title screen: the texture behind everything, the curtains outside
   the logo, the logo at the top, the menu under it, and the progress of
   the save under the menu. */

#define LOGO_X 64 /* the logo is three 64x64 sprites side by side */
#define LOGO_Y 12
#define LOGO_W 192
#define LOGO_SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))
#define LOGO_IMAGE(i) (XRAM_LOGO_IMAGES + (i) * sizeof(logo_image_t))

/* The progress box is as wide as the menu, one line tall, low enough that
   the question to start over, which takes the menu's place, clears it. */
#define PROGRESS_TOP 23

/* How far the save has come: the levels cleared and the upgrade ranks
   bought, out of all of them. */
static uint8_t progress(void)
{
    uint16_t done = levels_cleared, all = LEVELS;
    uint8_t u;

    for (u = 0; u < UPGRADES; u++)
    {
        done += upgrade_ranks[u];
        all += upgrades_max(u);
    }
    return all ? done * 100 / all : 0;
}

static void progress_draw(const menu_t *menu)
{
    uint8_t left = menu->center - MENU_COLS / 2, done = progress();

    video_box(left, PROGRESS_TOP, left + MENU_COLS - 1, PROGRESS_TOP + 2, menu->frame);
    video_text(left + 3, PROGRESS_TOP + 1, "PROGRESS");
    video_number(left + 12, PROGRESS_TOP + 1, done, 3);
    video_text(left + 12 + (done >= 100 ? 3 : done >= 10 ? 2 : 1), PROGRESS_TOP + 1, "%");
}

/* The title screen, with the progress box under the menu, which the
   caller opens after. */
void title_open(const menu_t *menu)
{
    uint8_t i;

    video_hide_sprites();
    cursor_hide();
    scene_title();
    menu_clear();
    frame_curtains(LOGO_X, LOGO_X + LOGO_W);
    for (i = 0; i < 3; i++)
    {
        sprite_set(LOGO_SPRITE(i), LOGO_IMAGE(i), XRAM_PALETTE_LOGO, MODE5_SIZE(64, 64));
        sprite_move(LOGO_SPRITE(i), LOGO_X + i * 64, LOGO_Y);
    }
    progress_draw(menu);
}

/* Shift and left or right switch the curtains, to look at each set. */
void title_step(void)
{
    if (shift_pressed & SHIFT_LEFT)
        scene_curtains(-1);
    if (shift_pressed & SHIFT_RIGHT)
        scene_curtains(1);
}
