#ifndef ENERGY_H
#define ENERGY_H

#include <stdint.h>

extern uint16_t energy;         /* steps of thrust left */
extern uint8_t energy_draining; /* set at the first launch of a level */

void energy_start(int16_t x, int16_t y);
void energy_step(void);
void energy_bubble(void);
void energy_draw(void);
void energy_idle(void);
void energy_cheat(int8_t steps);

#endif
