#ifndef PADDLE_H
#define PADDLE_H

#include <stdint.h>

/* paddle_state */
#define PADDLE_HOVER 0   /* on its thrusters, under the player's control */
#define PADDLE_SPUTTER 1 /* out of energy, the flames sputter */
#define PADDLE_FALLING 2 /* gave up in a puff of smoke */
#define PADDLE_GONE 3    /* fell off the bottom of the screen */

extern uint8_t paddle_state;
extern int32_t paddle_x; /* the left edge, in 1/256 px */
extern int32_t paddle_y; /* the top, in 1/256 px */
extern uint8_t paddle_width;
extern uint8_t paddle_left; /* the paddle last moved left */

void paddle_start(void);
void paddle_give_up(void);
void paddle_step(uint8_t controls);
uint8_t paddle_tilt(void);
void paddle_draw(void);

#endif
