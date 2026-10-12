#ifndef PLAY_H
#define PLAY_H

#include <stdint.h>

/* Positions and speeds are in 1/256 pixel. */
#define FIX(px) ((int32_t)(px) << 8)
#define PX(fix) ((int16_t)((fix) >> 8))

/* What play_step() returns. */
#define PLAY_ON 0
#define PLAY_CLEARED 1   /* every brick is broken */
#define PLAY_OUT 2       /* the last ball is lost */
#define PLAY_NO_ENERGY 3 /* the paddle ran out of energy and fell */

extern int16_t play_left;  /* the inner edges of the side walls */
extern int16_t play_right;

void play_init(void);
void play_start(void);
uint8_t play_step(void);
void play_idle(void);
void play_finish(void);
void play_draw(void);

#endif
