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

/* A picture of the sled of a level, and its jets, for the upgrade screen:
   with flames, doubled, or in the shade palette, as look says, from the
   sled's flat image at image. */
#define SLED_NONE 0xFF
#define SLED_FLAMES 0x01
#define SLED_DOUBLE 0x02
#define SLED_DIM 0x04
void sled_show(unsigned sprites, uint8_t count, int16_t x, int16_t y, uint8_t level, uint8_t look,
               unsigned image);

#endif
