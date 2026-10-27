#ifndef SFX_H
#define SFX_H

#include <stdint.h>

/* The sound effects, in the order of the table in src/sfx.c. */
#define SFX_PADDLE 0   /* the ball off the paddle */
#define SFX_WALL 1     /* the ball off a wall */
#define SFX_BRICK 2    /* the ball off a brick */
#define SFX_BREAK 3    /* a brick breaking */
#define SFX_NUGGET 4   /* a nugget landing in the panel */
#define SFX_LOST 5     /* a ball falling off the screen */
#define SFX_LOW 6      /* the energy turning low */
#define SFX_LOW_BEEP 7 /* the energy still low */
#define SFX_SPUTTER 8  /* out of energy, the flames sputtering */
#define SFX_FALL 9     /* the paddle falling */
#define SFX_BUY 10     /* an upgrade bought */
#define SFX_MOVE 11    /* a menu's pick moving */
#define SFX_RATTLE 12  /* the lock of a stage newly open shaking */
#define SFX_SNAP 13    /* the lock breaking */
#define SFX_UNLOCK 14  /* the stage's button lighting up */
#define SFX_HISS 15    /* a puff of steam in the upgrade screen's backdrop */
#define SFX_COUNT 16

#define SFX_CENTER 160 /* a sound from the middle of the screen */

void sfx_init(void);
void sfx_play(uint8_t sound, int16_t x);
void sfx_step(void);

#endif
