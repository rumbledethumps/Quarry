#ifndef MENU_H
#define MENU_H

#include <stdint.h>

/* A menu: a box of the menus' cells with a title, if any, and items under
   it, one picked. The box is MENU_COLS wide, centered on center. A menu
   of BOX_NONE has no box, and the screen under it has its items, where
   they would be in a box, as the title has on its panels. */
typedef struct
{
    uint8_t center; /* the column in the middle of the box */
    uint8_t top;    /* the row of the box's top edge */
    uint8_t frame;  /* BOX_TAPE or BOX_NONE */
    const char *title;
    const char *const *items;
    uint8_t count;
} menu_t;

#define MENU_COLS 20

/* menu_t frame */
#define BOX_TAPE 1 /* framed in caution tape and steel */
#define BOX_NONE 0

/* What menu_step() returns: no choice yet, or 1 for the first item. */
#define MENU_NONE 0

void menu_clear(void);
void menu_open(const menu_t *menu, uint8_t pick, uint8_t disabled, uint8_t wait);
void menu_close(void);
uint8_t menu_picked(void);
uint8_t menu_step(void);
void menu_draw(void);

#endif
