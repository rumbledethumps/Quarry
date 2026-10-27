#ifndef SAVE_H
#define SAVE_H

#include <stdint.h>

extern uint8_t save_exists;    /* a good save was read or written */
extern uint8_t stages_cleared; /* the stages cleared, stage 1 on */
extern uint8_t stage_picked;   /* the stage to play, on the upgrade screen, from 1 */
extern uint8_t stages_shown;   /* the highest stage the upgrade screen has shown open */

uint8_t save_stages_open(void);
uint8_t save_load(void);
void save_write(void);
void save_new_game(void);

#endif
