#ifndef BRICKS_H
#define BRICKS_H

#include <stdint.h>

#define BRICK_W 24
#define BRICK_H 8

/* Colors of brick, each with its own palette and nugget. */
#define BRICK_WHITE 0

extern uint8_t bricks_cols; /* the width of the stage, in bricks */
extern uint8_t bricks_left; /* bricks not yet broken */

/* The box around the bricks the last bricks_hit() broke. */
extern int16_t bricks_hit_left;
extern int16_t bricks_hit_right;
extern int16_t bricks_hit_top;
extern int16_t bricks_hit_bottom;

void bricks_layout(void);
void bricks_start(int16_t left, int16_t top);
uint8_t bricks_hit(int16_t x, int16_t y, uint8_t w, uint8_t h);
uint8_t bricks_touch(int16_t x, int16_t y, uint8_t w, uint8_t h);
void bricks_step(void);

#endif
