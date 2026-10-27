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

/* Shift and an arrow key is not a move, but a key for testing: on the
   title it switches the curtains, and in a debug build's play it cheats. */
#define SHIFT_RIGHT 0x01
#define SHIFT_LEFT 0x02
#define SHIFT_UP 0x04
#define SHIFT_DOWN 0x08

/* The SHIFT_ bits pressed this step, then again every SHIFT_REPEAT steps
   while they are held. */
extern uint8_t shift_pressed;

void input_init(void);
void input_read(void);

#endif
