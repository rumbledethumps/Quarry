#ifndef SAVE_H
#define SAVE_H

#include <stdint.h>

extern uint8_t save_exists;    /* a good save was read or written */
extern uint8_t levels_cleared; /* the levels cleared, level 1 on */
extern uint8_t level_picked;   /* the level to play, on the upgrade screen, from 1 */
extern uint8_t levels_shown;   /* the highest level the upgrade screen has shown open */
extern uint8_t talks_seen;     /* a bit for each talk of the dwarves the player has seen, TALK_ from 1 */

uint8_t save_levels_open(void);
uint8_t save_load(void);
void save_write(void);
void save_new_game(void);
void save_delete(void);

#endif
