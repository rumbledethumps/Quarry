#ifndef FRAME_H
#define FRAME_H

#include <stdint.h>

void frame_start(int16_t left, int16_t right);
void frame_curtains(int16_t left, int16_t right);
void frame_lamp(uint8_t on);

#endif
