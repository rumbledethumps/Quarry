#ifndef FRAME_H
#define FRAME_H

#include <stdint.h>

void frame_start(int16_t left, int16_t right);
void frame_curtains(int16_t left, int16_t right);
void frame_rock(uint8_t *pixels, int16_t x, int16_t y, uint8_t n);
void frame_lamp(uint8_t on);
void frame_meter(uint8_t frame, uint8_t color);

/* The colors of the meter's paddle. */
#define METER_GREEN 0
#define METER_YELLOW 1
#define METER_RED 2

#endif
