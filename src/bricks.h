#ifndef BRICKS_H
#define BRICKS_H

#include <stdint.h>

#define BRICK_W 24
#define BRICK_H 8

/* Colors of brick, each with its own palette and nugget, in the order of
   COLORS in art/bricks.py. */
#define BRICK_GRAY 0
#define BRICK_RED 1
#define BRICK_GREEN 2
#define BRICK_BLUE 3
#define BRICK_GOLD 4

/* Levels 3 on are stand-ins until the levels are designed. */
#define LEVELS 10

extern uint8_t bricks_cols;   /* the width of the level, in bricks */
extern int16_t bricks_width;  /* of the playfield */
extern uint8_t bricks_margin; /* the room between each wall and the bricks */
extern uint8_t bricks_gap;    /* between two bricks, across and down */
extern uint8_t bricks_left; /* bricks not yet broken */

/* The box around the bricks the last bricks_hit() broke. */
extern int16_t bricks_hit_left;
extern int16_t bricks_hit_right;
extern int16_t bricks_hit_top;
extern int16_t bricks_hit_bottom;

void bricks_layout(uint8_t level);
void bricks_shuffle(void);
void bricks_start(int16_t left, int16_t top);
uint8_t bricks_hit(int16_t x, int16_t y, uint8_t w, uint8_t h);
uint8_t bricks_touch(int16_t x, int16_t y, uint8_t w, uint8_t h);
void bricks_step(void);
void bricks_draw(void);
void bricks_finish(void);

#endif
