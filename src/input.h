#ifndef INPUT_H
#define INPUT_H

#include <stdint.h>

#define INPUT_LEFT 0x01
#define INPUT_RIGHT 0x02
#define INPUT_LAUNCH 0x04

extern uint8_t input_held;    /* the INPUT_ bits held this step */
extern uint8_t input_pressed; /* the INPUT_ bits held this step and not the last */

void input_init(void);
void input_read(void);

#endif
