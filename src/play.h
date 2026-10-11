#ifndef PLAY_H
#define PLAY_H

#include <stdint.h>

/* What play_step() returns. */
#define PLAY_ON 0
#define PLAY_CLEARED 1 /* every brick is broken */
#define PLAY_OUT 2     /* the last ball is lost */

extern int16_t play_left;  /* the inner edges of the side walls */
extern int16_t play_right;

void play_init(void);
void play_start(void);
uint8_t play_step(void);
void play_draw(void);

#endif
