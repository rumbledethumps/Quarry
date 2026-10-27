#ifndef VIDEO_H
#define VIDEO_H

#include <stdint.h>

#define SCREEN_W 320
#define SCREEN_H 240

/* Colors in the main palette. */
#define TEXT_COLOR 9 /* cream */
#define DIM_COLOR 4  /* stone, for what can't be chosen */
#define BOX_COLOR 7  /* pale steel, the frame of a box */
#define PICK_COLOR 14 /* gold, the frame of what is picked in a menu */
#define BOX_FILL 1   /* the dark inside of a box */
#define CLEAR 0      /* transparent */

/* The outlined digits of a count are this far apart. */
#define DIGIT_ADVANCE 7

/* A hidden sprite sits above the canvas. Sprites are at most 64 tall. */
#define SPRITE_HIDDEN_Y -64

void video_init(void);
void video_start(void);
void video_rock(void);
void video_hide_sprites(void);
void video_text_clear(void);
void video_clear(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom);
void video_text(uint8_t col, uint8_t row, const char *s, uint8_t fg, uint8_t bg);
void video_number(uint8_t col, uint8_t row, uint16_t n, uint8_t width, uint8_t fg, uint8_t bg);
void video_box(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom, uint8_t color);

void sprite_set(unsigned sprite, unsigned image, unsigned palette, uint8_t width_height);
void sprite_move(unsigned sprite, int16_t x, int16_t y);
void sprite_hide(unsigned sprite);
void sprite_flip(unsigned sprite);
void video_count(unsigned first, uint8_t sprites, int16_t x, int16_t y, uint16_t n);

#endif
