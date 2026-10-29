#ifndef FRAME_H
#define FRAME_H

#include <stdint.h>

void frame_start(int16_t left, int16_t right);
void frame_curtains(int16_t left, int16_t right);
void frame_rock(uint8_t *pixels, int16_t x, int16_t y, uint8_t n);
void frame_lamp(uint8_t on);

#endif
