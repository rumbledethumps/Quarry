#ifndef NUGGETS_H
#define NUGGETS_H

#include <stdint.h>
#include "xram.h"

/* The nuggets collected of each color of brick. They never reset, and
   only the upgrades will spend them. */
extern uint16_t nuggets[BRICK_COLORS];

/* The coins, one for the first clear of each level. */
extern uint16_t coins;

/* The lines of the counts the player has reached: a bit for each color,
   from 1 << BRICK_GRAY, and COUNT_COINS. */
#define COUNT_COINS (1 << BRICK_COLORS)
extern uint8_t counts_shown;

void nuggets_start(void);
void nuggets_spawn(int16_t x, int16_t y, uint8_t color);
void coins_add(void);
void nuggets_land(void);
uint8_t nuggets_flying(uint8_t color);
void nuggets_step(void);
void nuggets_draw(void);

#endif
