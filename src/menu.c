#include "menu.h"
#include "debug.h"
#include "input.h"
#include "play.h"
#include "video.h"
#include <string.h>

/* The end-of-stage menu is a box over the middle of the playfield: how the
   stage ended, then UPGRADES and PLAY. The pick has a gold frame. */
#define MENU_COLS 16
#define MENU_TOP 11

static const char *const items[2] = {"UPGRADES", "PLAY"};

static uint8_t shown;
static uint8_t picked;
static uint8_t waiting; /* steps before it takes a choice */
static uint8_t center;  /* the column in the middle of the box */

static void item_draw(uint8_t i)
{
    uint8_t row = MENU_TOP + 3 + i * 3;

    video_box(center - MENU_COLS / 2 + 2, row, center + MENU_COLS / 2 - 3, row + 2,
              i == picked ? PICK_COLOR : BOX_FILL);
    video_text(center - strlen(items[i]) / 2, row + 1, items[i], TEXT_COLOR, BOX_FILL);
}

/* Opens the menu with pick picked, MENU_UPGRADES or MENU_PLAY. It waits
   wait steps before it takes a choice, so a press meant for the last ball
   doesn't choose. */
void menu_open(const char *title, uint8_t pick, uint8_t wait)
{
    center = (play_left + play_right) / 16;
    video_box(center - MENU_COLS / 2, MENU_TOP, center + MENU_COLS / 2 - 1, MENU_TOP + 9, BOX_COLOR);
    video_text(center - strlen(title) / 2, MENU_TOP + 1, title, TEXT_COLOR, BOX_FILL);
    picked = pick - MENU_UPGRADES;
    item_draw(0);
    item_draw(1);
    waiting = wait;
    shown = 1;
    DEBUG_LOG("menu\n");
}

/* Erases the box, if it is shown, so play can go on under it. */
void menu_close(void)
{
    if (shown)
        video_clear(center - MENU_COLS / 2, MENU_TOP, center + MENU_COLS / 2 - 1, MENU_TOP + 9);
    shown = 0;
}

/* Up, down, left or right moves the pick, and choose returns it. */
uint8_t menu_step(void)
{
    if (waiting)
    {
        waiting--;
        return MENU_NONE;
    }
    if (input_pressed & (INPUT_UP | INPUT_DOWN | INPUT_LEFT | INPUT_RIGHT))
    {
        picked ^= 1;
        item_draw(0);
        item_draw(1);
    }
    if (input_pressed & INPUT_CHOOSE)
        return MENU_UPGRADES + picked;
    return MENU_NONE;
}
