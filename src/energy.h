#ifndef ENERGY_H
#define ENERGY_H

#include <stdint.h>

extern uint16_t energy;         /* steps of thrust left */
extern uint8_t energy_draining; /* set at the first launch of a stage */

void energy_start(int16_t x, int16_t y);
void energy_step(void);

#endif
