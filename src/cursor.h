#ifndef CURSOR_H
#define CURSOR_H

#include <stdint.h>

void cursor_place(int16_t left, int16_t top, int16_t right, int16_t bottom);
void cursor_hide(void);
void cursor_step(void);
void cursor_draw(void);

#endif
