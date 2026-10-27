#include "title.h"
#include "bricks.h"
#include "frame.h"
#include "save.h"
#include "scene.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"

/* The title screen: the texture behind everything, the curtains outside
   the logo, the logo at the top, the menu under it, the progress of the
   save under the menu, and the credit at the bottom. */

#define LOGO_X 64 /* the logo is three 64x64 sprites side by side */
#define LOGO_Y 12
#define LOGO_W 192
#define LOGO_SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))
#define LOGO_IMAGE(i) (XRAM_LOGO_IMAGES + (i) * sizeof(logo_image_t))

/* The progress box is as wide as the menu, one line tall, low enough that
   the question to start over, which takes the menu's place, clears it. */
#define PROGRESS_TOP 21
#define CREDIT_ROW 28
static const char credit[] = "(c)2026 Rumbledethumps";

/* How far the save has come: the stages cleared and the upgrade levels
   bought, out of all of them. */
static uint8_t progress(void)
{
    uint16_t done = stages_unlocked - 1, all = STAGES - 1;
    uint8_t u;

    for (u = 0; u < UPGRADES; u++)
    {
        done += upgrade_levels[u];
        all += upgrades_max(u);
    }
    return all ? done * 100 / all : 0;
}

static void progress_draw(const menu_t *menu)
{
    uint8_t left = menu->center - MENU_COLS / 2, done = progress();

    video_box(left, PROGRESS_TOP, left + MENU_COLS - 1, PROGRESS_TOP + 2, menu->frame);
    video_text(left + 2, PROGRESS_TOP + 1, "PROGRESS", TEXT_COLOR, BOX_FILL);
    video_number(left + 11, PROGRESS_TOP + 1, done, 3, TEXT_COLOR, BOX_FILL);
    video_text(left + 11 + (done >= 100 ? 3 : done >= 10 ? 2 : 1), PROGRESS_TOP + 1, "%", TEXT_COLOR,
               BOX_FILL);
}

/* The title screen, with the progress box under the menu, which the
   caller opens after. */
void title_open(const menu_t *menu)
{
    uint8_t i;

    video_hide_sprites();
    scene_title();
    video_text_clear();
    frame_curtains(LOGO_X, LOGO_X + LOGO_W);
    for (i = 0; i < 3; i++)
    {
        sprite_set(LOGO_SPRITE(i), LOGO_IMAGE(i), XRAM_PALETTE_LOGO, MODE5_SIZE(64, 64));
        sprite_move(LOGO_SPRITE(i), LOGO_X + i * 64, LOGO_Y);
    }
    progress_draw(menu);
    video_text((TEXT_COLS - (sizeof credit - 1)) / 2, CREDIT_ROW, credit, DIM_COLOR, CLEAR);
}
