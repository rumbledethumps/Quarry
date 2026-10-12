#ifndef NUGGETS_H
#define NUGGETS_H

#include <stdint.h>
#include "xram.h"

/* The nuggets collected of each color of brick. They never reset, and
   only the upgrades will spend them. */
extern uint16_t nuggets[BRICK_COLORS];

void nuggets_start(uint8_t colors, int16_t panel_right);
void nuggets_spawn(int16_t x, int16_t y, uint8_t color);
void nuggets_add(uint8_t color);
void nuggets_step(void);
void nuggets_draw(void);

#endif
