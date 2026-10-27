#include "menu.h"
#include "debug.h"
#include "input.h"
#include "sfx.h"
#include "video.h"
#include <string.h>

/* Each item is 3 rows, for the gold frame around the one picked. */
#define ITEM_ROWS 3

static const menu_t *shown; /* NULL when no menu is shown */
static uint8_t picked;
static uint8_t disabled_items; /* a bit for each item that can't be picked */
static uint8_t waiting;        /* steps before it takes a choice */

static uint8_t first_item_row(void)
{
    return shown->top + (shown->title ? 3 : 1);
}

/* The row of a menu's bottom edge. */
uint8_t menu_bottom(const menu_t *menu)
{
    return menu->top + (menu->title ? 3 : 1) + menu->count * ITEM_ROWS;
}

static void item_draw(uint8_t i)
{
    uint8_t row = first_item_row() + i * ITEM_ROWS;
    const char *item = shown->items[i];

    video_box(shown->center - MENU_COLS / 2 + 2, row, shown->center + MENU_COLS / 2 - 3, row + 2,
              i == picked ? PICK_COLOR : BOX_FILL);
    video_text(shown->center - strlen(item) / 2, row + 1, item,
               disabled_items & (1 << i) ? DIM_COLOR : TEXT_COLOR, BOX_FILL);
}

static void items_draw(void)
{
    uint8_t i;

    for (i = 0; i < shown->count; i++)
        item_draw(i);
}

/* Steps the pick by step, 1 or -1, past items that can't be picked. It
   stops at the first and the last: a menu doesn't wrap around. */
static void pick_step(int8_t step)
{
    uint8_t i = picked;

    while ((uint8_t)(i + step) < shown->count)
    {
        i += step;
        if (!(disabled_items & (1 << i)))
        {
            picked = i;
            return;
        }
    }
}

/* Opens the menu with item pick picked, counting from 0, or the next one
   that can be picked. disabled has a bit for each item that can't be. It
   waits wait steps before it takes a choice, so a press meant for what came
   before doesn't choose. */
void menu_open(const menu_t *menu, uint8_t pick, uint8_t disabled, uint8_t wait)
{
    shown = menu;
    disabled_items = disabled;
    picked = pick;
    if (disabled & (1 << pick))
        pick_step(1);
    video_box(menu->center - MENU_COLS / 2, menu->top, menu->center + MENU_COLS / 2 - 1, menu_bottom(menu),
              menu->frame);
    if (menu->title)
        video_text(menu->center - strlen(menu->title) / 2, menu->top + 1, menu->title, TEXT_COLOR,
                   BOX_FILL);
    items_draw();
    waiting = wait;
    DEBUG_LOG("menu %s\n", menu->items[0]);
}

/* Erases the box, if it is shown, so what is under it shows again. */
void menu_close(void)
{
    if (shown)
        video_clear(shown->center - MENU_COLS / 2, shown->top, shown->center + MENU_COLS / 2 - 1,
                    menu_bottom(shown));
    shown = 0;
}

/* The item picked, counting from 0. */
uint8_t menu_picked(void)
{
    return picked;
}

/* Up picks the item before, down the item after, but for the first and
   the last, and choose returns the one picked, from 1. */
uint8_t menu_step(void)
{
    uint8_t was = picked;

    if (!shown)
        return MENU_NONE;
    if (waiting)
    {
        waiting--;
        return MENU_NONE;
    }
    if (input_pressed & INPUT_UP)
        pick_step(-1);
    else if (input_pressed & INPUT_DOWN)
        pick_step(1);
    else if (input_pressed & INPUT_CHOOSE)
        return picked + 1;
    if (picked != was)
    {
        sfx_play(SFX_MOVE, SFX_CENTER);
        items_draw();
    }
    return MENU_NONE;
}
