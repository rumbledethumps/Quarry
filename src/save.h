#ifndef SAVE_H
#define SAVE_H

#include <stdint.h>

extern uint8_t save_exists;     /* a good save was read or written */
extern uint8_t stages_unlocked; /* the stages that can be played, from 1 */

uint8_t save_load(void);
void save_write(void);
void save_new_game(void);

#endif
