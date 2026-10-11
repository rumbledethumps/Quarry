#ifndef VIDEO_H
#define VIDEO_H

#include <stdint.h>

#define SCREEN_W 320
#define SCREEN_H 240

/* Colors in the main palette. */
#define TEXT_COLOR 9 /* cream */
#define BOX_COLOR 7  /* pale steel, the frame of a box */
#define BOX_FILL 1   /* the dark inside of a box */

/* The walls are one background tile thick. */
#define WALL_SIZE 16

/* A hidden sprite sits above the canvas. Sprites are at most 64 tall. */
#define SPRITE_HIDDEN_Y -64

void video_init(void);
void video_start(void);
void video_walls(int16_t left, int16_t right);
void video_text_clear(void);
void video_text(uint8_t col, uint8_t row, const char *s);
void video_box(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom);

void sprite_set(unsigned sprite, unsigned image, unsigned palette, uint8_t width_height);
void sprite_move(unsigned sprite, int16_t x, int16_t y);
void sprite_hide(unsigned sprite);

#endif
