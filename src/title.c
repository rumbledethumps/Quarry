#include "title.h"
#include "bricks.h"
#include "cursor.h"
#include "frame.h"
#include "input.h"
#include "menu.h"
#include "save.h"
#include "scene.h"
#include "talk.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"
#include <string.h>

/* The title screen: the texture behind everything, the curtains outside
   the logo, the logo at the top, and under it the title's panels, on
   plane 1. With a save, the menu's panel holds CONTINUE GAME and DELETE
   SAVE, and the progress of the save is on a panel that hangs from it.
   With none, a smaller panel holds START GAME, and a dwarf greets the
   player from under it, and stays while they pick. DELETE SAVE asks first,
   in a box of caution tape in the panels' place. Yes deletes the save, and
   the panels of none come at once, and the dwarf. */

#define LOGO_X 64 /* the logo is three 64x64 sprites side by side */
#define LOGO_Y 12
#define LOGO_W 192
#define LOGO_SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))
#define LOGO_IMAGE(i) (XRAM_LOGO_IMAGES + (i) * sizeof(logo_image_t))

/* The panels' map has its top left on this cell of the menus' cells, so
   the menus' cursor goes round the items on them. A menu's box is the
   panel's width, so the cursor spans its plate. */
#define PANELS_COL 10
#define PANELS_ROW 10
_Static_assert(TITLE_COLS == MENU_COLS, "The title's panels are as wide as a menu's box.");

/* The menus on the panels, whose items art/title_panels.py draws there. A
   menu with no title has its first item's text two rows under its top, so
   each menu's top is two rows over the row of the map that gives. The
   question takes the panels' place. */
static const char *const save_items[] = {"CONTINUE GAME", "DELETE SAVE"};
#define SAVE_CONTINUE 1
#define SAVE_DELETE 2
static const char *const start_items[] = {"START GAME"};
static const char *const yes_no[] = {"YES", "NO"};
#define ASK_YES 1
#define ASK_NO 2
static const menu_t save_menu = {PANELS_COL + MENU_COLS / 2, PANELS_ROW + TITLE_SAVE_ROW - 2, BOX_NONE, 0,
                                 save_items, 2};
static const menu_t start_menu = {PANELS_COL + MENU_COLS / 2, PANELS_ROW + TITLE_START_ROW - 2, BOX_NONE, 0,
                                  start_items, 1};
static const menu_t delete_menu = {20, 11, BOX_TAPE, "DELETE SAVE?", yes_no, 2};

static uint8_t asking; /* whether to delete the save */

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

/* The progress of the save on its panel, centered on the cells: PROGRESS
   42%, a space more under 10%, so it is as long, or at 100, 100% COMPLETE! */
static void progress_draw(void)
{
    static const char font[] = TITLE_FONT;
    char line[] = "PROGRESS  0%";
    const char *s = line;
    uint8_t cells[TITLE_COLS];
    uint8_t done = progress(), n = 0;

    if (done >= 100)
        s = "100% COMPLETE!";
    else
    {
        if (done >= 10)
            line[9] = '0' + done / 10;
        line[10] = '0' + done % 10;
    }
    while (s[n])
    {
        const char *at = strchr(font, s[n]);
        cells[n] = TITLE_TILE_GLYPH + (at ? at - font : 0);
        n++;
    }
    xram0_write(XRAM_TITLE_MAP + TITLE_PROGRESS_ROW * TITLE_COLS + TITLE_COLS / 2 - n / 2, cells, n);
}

/* The panels, and the menu on them with item pick picked: those of the
   save, or of none, with the dwarf's greeting. They load off the screen,
   and show once they are whole. */
static void panels_open(uint8_t pick)
{
    if (save_exists)
    {
        scene_title_panels(TITLE_MAP_SAVE);
        progress_draw();
        menu_open(&save_menu, pick, 0);
    }
    else
    {
        scene_title_panels(TITLE_MAP_START);
        menu_open(&start_menu, 0, 0);
        talk_queue(TALK_GREENHORN);
    }
    scene_title_show(PANELS_COL * 8);
    asking = 0;
}

/* The title screen, its menu up. */
void title_open(void)
{
    uint8_t i;

    video_hide_sprites();
    cursor_hide();
    scene_title(PANELS_ROW * 8);
    menu_clear();
    frame_curtains(LOGO_X, LOGO_X + LOGO_W);
    for (i = 0; i < 3; i++)
    {
        sprite_set(LOGO_SPRITE(i), LOGO_IMAGE(i), XRAM_PALETTE_LOGO, MODE5_SIZE(64, 64));
        sprite_move(LOGO_SPRITE(i), LOGO_X + i * 64, LOGO_Y);
    }
    panels_open(SAVE_CONTINUE - 1);
}

/* Returns TITLE_CONTINUE or TITLE_START once one is chosen, and the dwarf
   goes with the title. Shift and left or right switch the curtains, to
   look at each set. */
uint8_t title_step(void)
{
    if (shift_pressed & SHIFT_LEFT)
        scene_curtains(-1);
    if (shift_pressed & SHIFT_RIGHT)
        scene_curtains(1);
    if (asking)
        /* Esc is No. */
        switch (input_pressed & INPUT_PAUSE ? ASK_NO : menu_step())
        {
        case ASK_YES:
            menu_close();
            save_delete();
            panels_open(0);
            break;
        case ASK_NO:
            menu_close();
            panels_open(SAVE_DELETE - 1);
            break;
        }
    else
        switch (menu_step())
        {
        case SAVE_CONTINUE: /* or START GAME, the first item too */
            talk_stop();
            return save_exists ? TITLE_CONTINUE : TITLE_START;
        case SAVE_DELETE:
            menu_close();
            scene_title_show(SCREEN_W);
            menu_open(&delete_menu, ASK_NO - 1, 0);
            asking = 1;
            break;
        }
    return TITLE_NONE;
}
