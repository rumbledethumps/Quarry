#ifndef INPUT_H
#define INPUT_H

#include <stdint.h>

#define INPUT_LEFT 0x01
#define INPUT_RIGHT 0x02
#define INPUT_LAUNCH 0x04
#define INPUT_UP 0x08
#define INPUT_DOWN 0x10
#define INPUT_CHOOSE 0x20 /* in a menu */
#define INPUT_PAUSE 0x40

extern uint8_t input_held;    /* the INPUT_ bits held this step */
extern uint8_t input_pressed; /* the INPUT_ bits held this step and not the last */

/* Debug builds only: Shift and an arrow key is a cheat, not a move. */
#define CHEAT_BALL_MORE 0x01   /* Shift and right */
#define CHEAT_BALL_LESS 0x02   /* Shift and left */
#define CHEAT_ENERGY_MORE 0x04 /* Shift and up */
#define CHEAT_ENERGY_LESS 0x08 /* Shift and down */

/* The CHEAT_ bits pressed this step, then again every CHEAT_REPEAT steps
   while they are held. */
extern uint8_t cheat_pressed;

void input_init(void);
void input_read(void);

#endif
