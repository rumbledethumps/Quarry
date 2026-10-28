#include "menu.h"
#include "cursor.h"
#include "debug.h"
#include "input.h"
#include "sfx.h"
#include "video.h"
#include "xram.h"
#include <string.h>

/* A menu box: its frame, then, with a title, a gap, the title and a thin
   rule under it, then each item ITEM_ROWS tall, its text in the middle row, then a gap and
   the frame. An item that can't be chosen is left off. The holographic
   cursor goes round the item picked, and slides from item to item. While a
   menu shows, its tape marches. */
#define ITEM_ROWS 3
#define HEAD_ROWS 4
#define TAPE_STEPS 8 /* frames the tape takes to move 2 px */

static const menu_t *shown; /* NULL when no menu is shown */
static uint8_t picked;
static uint8_t disabled_items; /* a bit for each item left off */
static uint8_t waiting;        /* steps before it takes a choice */
static uint8_t tape_steps;

static uint8_t first_item_row(void)
{
    return shown->top + (shown->title ? HEAD_ROWS : 1);
}

/* Where item i is among the items shown. */
static uint8_t place(uint8_t i)
{
    uint8_t n = 0, j;

    for (j = 0; j < i; j++)
        if (!(disabled_items & (1 << j)))
            n++;
    return n;
}

/* The row of the menu's bottom edge, with the items shown. */
static uint8_t bottom(void)
{
    return first_item_row() + place(shown->count) * ITEM_ROWS + 1;
}

/* The cursor goes round the item picked, as wide as the box inside its
   frame and a cell in from it. */
static void cursor_aim(void)
{
    int16_t row = first_item_row() + place(picked) * ITEM_ROWS;

    cursor_place((shown->center - MENU_COLS / 2 + 2) * 8, row * 8, (shown->center + MENU_COLS / 2 - 2) * 8,
                 (row + ITEM_ROWS) * 8);
}

/* Steps the pick by step, 1 or -1, past items left off. It stops at the
   first and the last: a menu doesn't wrap around. */
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
   that can be picked. disabled has a bit for each item that can't be,
   which the menu leaves off. It waits wait steps before it takes a choice,
   so a press meant for what came before doesn't choose. The cursor comes
   to it: it slides there if it shows already, or appears there. */
void menu_open(const menu_t *menu, uint8_t pick, uint8_t disabled, uint8_t wait)
{
    uint8_t i;

    shown = menu;
    disabled_items = disabled;
    picked = pick;
    if (disabled & (1 << pick))
        pick_step(1);
    video_box(menu->center - MENU_COLS / 2, menu->top, menu->center + MENU_COLS / 2 - 1, bottom(), menu->frame);
    if (menu->title)
    {
        video_text(menu->center - strlen(menu->title) / 2, menu->top + 2, menu->title);
        video_rule(menu->center - MENU_COLS / 2 + 2, menu->center + MENU_COLS / 2 - 3, menu->top + 3);
    }
    for (i = 0; i < menu->count; i++)
        if (!(disabled & (1 << i)))
            video_text(menu->center - strlen(menu->items[i]) / 2, first_item_row() + place(i) * ITEM_ROWS + 1,
                       menu->items[i]);
    cursor_aim();
    waiting = wait;
    DEBUG_LOG("menu %s\n", menu->items[0]);
}

/* Erases the box, if it is shown, so what is under it shows again. The
   cursor stays, for whatever is picked next. */
void menu_close(void)
{
    if (shown)
        video_clear(shown->center - MENU_COLS / 2, shown->top, shown->center + MENU_COLS / 2 - 1, bottom());
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
        cursor_aim();
    }
    return MENU_NONE;
}

/* At the start of a frame, while a menu shows: every TAPE_STEPS, its
   tape's colors turn round a place, and the stripes move along. */
void menu_draw(void)
{
    uint16_t tape[MENU_TAPE_PHASES], last;
    uint8_t i;

    if (!shown || ++tape_steps < TAPE_STEPS)
        return;
    tape_steps = 0;
    xram0_read(tape, XRAM_MENU_PALETTE + MENU_TAPE * sizeof(uint16_t), sizeof tape);
    last = tape[MENU_TAPE_PHASES - 1];
    for (i = MENU_TAPE_PHASES - 1; i; i--)
        tape[i] = tape[i - 1];
    tape[0] = last;
    xram0_write(XRAM_MENU_PALETTE + MENU_TAPE * sizeof(uint16_t), tape, sizeof tape);
}
