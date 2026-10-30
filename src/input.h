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

/* Shift and a key is not a move, but a key for testing: with an arrow, on
   the title it switches the curtains, and in a debug build's play it
   cheats. */
#define SHIFT_RIGHT 0x01
#define SHIFT_LEFT 0x02
#define SHIFT_UP 0x04
#define SHIFT_DOWN 0x08

/* The SHIFT_ bits pressed this step, then again every so often while they
   are held. */
extern uint8_t shift_pressed;

/* A letter of the top row, Q, W, E and on, pressed with Shift this step,
   from 1 for Q, or 0. In a debug build it brings in a talk of the
   dwarves, to test. */
extern uint8_t shift_letter;

/* The number the number keys typed with Shift held, the last two digits,
   the step Shift is let go, or 0. In a debug build it brings in the coin's
   talk for that level. */
extern uint8_t shift_number;

void input_init(void);
void input_read(void);
uint8_t input_repeat(void);
void input_repeat_stop(void);

#endif
