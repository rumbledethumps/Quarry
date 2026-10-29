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
   in a box of caution tape in the panels' place. Yes deletes the save,
   and the title turns into the one with none: the panels come back, the
   progress panel goes, then the menu's panel shrinks to START GAME, and
   the dwarf comes in. */

#define LOGO_X 64 /* the logo is three 64x64 sprites side by side */
#define LOGO_Y 12
#define LOGO_W 192
#define LOGO_SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))
#define LOGO_IMAGE(i) (XRAM_LOGO_IMAGES + (i) * sizeof(logo_image_t))

/* The panels' maps have their top left on this cell of the menus' cells,
   so the menus' cursor goes round the items on them. A menu's box is the
   panel's width, so the cursor spans its plate. Each map has its text
   from the start, and the layer shows one at a time, all at once. */
#define PANELS_COL 10
#define PANELS_ROW 10
_Static_assert(TITLE_COLS == MENU_COLS, "The title's panels are as wide as a menu's box.");

/* The menus on the panels, which draw their items themselves, on the
   plate inside the frame, two cells in: the two of a save right under the
   frame, and START GAME in the middle of its panel. The question takes
   the panels' place. */
static const char *const save_items[] = {"CONTINUE GAME", "DELETE SAVE"};
#define SAVE_CONTINUE 1
#define SAVE_DELETE 2
static const char *const start_items[] = {"START GAME"};
static const char *const yes_no[] = {"YES", "NO"};
#define ASK_YES 1
#define ASK_NO 2
static const menu_t save_menu = {PANELS_COL + MENU_COLS / 2, PANELS_ROW + 1, BOX_NONE, 0, save_items, 2};
static const menu_t start_menu = {PANELS_COL + MENU_COLS / 2, PANELS_ROW + 2, BOX_NONE, 0, start_items, 1};
static const menu_t delete_menu = {20, 11, BOX_TAPE, "DELETE SAVE?", yes_no, 2};

/* title_state */
#define ON_MENU 0
#define ASKING 1     /* whether to delete the save */
#define FORGETTING 2 /* the save deleted, and the panels turning into those of none */

/* While FORGETTING, the steps until the progress panel goes, and until
   the menu's panel shrinks. */
#define GONE_STEPS 30
#define SHRUNK_STEPS 60

static uint8_t title_state;
static uint8_t steps;

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

/* Text on the panels of map, centered as a menu centers it, on a row. */
static void text(uint8_t map, uint8_t row, const char *s)
{
    static const char font[] = TITLE_FONT;
    uint8_t cells[TITLE_COLS];
    uint8_t n = 0;

    while (s[n] && n < TITLE_COLS)
    {
        const char *at = strchr(font, s[n]);
        cells[n] = TITLE_TILE_GLYPH + (at ? at - font : 0);
        n++;
    }
    xram0_write(XRAM_TITLE_MAP(map) + row * TITLE_COLS + TITLE_COLS / 2 - n / 2, cells, n);
}

/* The items of the menu on the panels of map. */
static void items_draw(uint8_t map, const menu_t *menu)
{
    uint8_t i;

    for (i = 0; i < menu->count; i++)
        text(map, menu_item_row(menu, i) - PANELS_ROW, menu->items[i]);
}

/* The text of every map: the menus, and the progress of the save. */
static void maps_draw(void)
{
    char line[] = "PROGRESS 100%";
    uint8_t done = progress(), n = sizeof "PROGRESS";

    items_draw(TITLE_MAP_SAVE, &save_menu);
    items_draw(TITLE_MAP_MENU, &save_menu);
    items_draw(TITLE_MAP_START, &start_menu);
    if (done >= 100)
        line[n++] = '0' + done / 100;
    if (done >= 10)
        line[n++] = '0' + done / 10 % 10;
    line[n++] = '0' + done % 10;
    line[n++] = '%';
    line[n] = 0;
    text(TITLE_MAP_SAVE, TITLE_PROGRESS_ROW, line);
}

/* The panels of map, in their place, or off the screen with
   PANELS_HIDDEN. */
#define PANELS_HIDDEN 0xFF
static void panels_show(uint8_t map)
{
    if (map != PANELS_HIDDEN)
        xram0_poke16(XRAM_PANEL_CONFIG + offsetof(mode2_config_t, xram_data_ptr), XRAM_TITLE_MAP(map));
    xram0_poke16(XRAM_PANEL_CONFIG + offsetof(mode2_config_t, x_pos_px),
                 map == PANELS_HIDDEN ? SCREEN_W : PANELS_COL * 8);
}

/* The panels, and the menu on them with item pick picked: those of the
   save, or of none, with the dwarf's greeting. */
static void panels_open(uint8_t pick)
{
    if (save_exists)
    {
        panels_show(TITLE_MAP_SAVE);
        menu_open(&save_menu, pick, 0, 0);
    }
    else
    {
        panels_show(TITLE_MAP_START);
        menu_open(&start_menu, 0, 0, 0);
        talk_queue(TALK_GREENHORN);
    }
    title_state = ON_MENU;
}

/* The title screen, its menu up. */
void title_open(void)
{
    uint8_t i;

    video_hide_sprites();
    cursor_hide();
    scene_title(PANELS_ROW * 8);
    maps_draw();
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
    switch (title_state)
    {
    case ON_MENU:
        switch (menu_step())
        {
        case SAVE_CONTINUE: /* or START GAME, the first item too */
            talk_stop();
            return save_exists ? TITLE_CONTINUE : TITLE_START;
        case SAVE_DELETE:
            menu_close();
            panels_show(PANELS_HIDDEN);
            menu_open(&delete_menu, ASK_NO - 1, 0, 0);
            title_state = ASKING;
            break;
        }
        break;
    case ASKING:
        /* Esc is No. */
        switch (input_pressed & INPUT_PAUSE ? ASK_NO : menu_step())
        {
        case ASK_YES:
            menu_close();
            cursor_hide();
            panels_show(TITLE_MAP_SAVE);
            save_delete();
            title_state = FORGETTING;
            steps = 0;
            break;
        case ASK_NO:
            menu_close();
            panels_open(SAVE_DELETE - 1);
            break;
        }
        break;
    case FORGETTING:
        if (++steps == GONE_STEPS)
            panels_show(TITLE_MAP_MENU);
        else if (steps == SHRUNK_STEPS)
            panels_open(0);
        break;
    }
    return TITLE_NONE;
}
