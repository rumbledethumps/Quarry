#ifndef VIDEO_H
#define VIDEO_H

#include <stdint.h>

#define SCREEN_W 320
#define SCREEN_H 240

/* A box of the menus, framed in caution tape and steel, or plain. */
#define BOX_TAPE 1
#define BOX_PLAIN 0

/* The outlined digits of a count are this far apart. */
#define DIGIT_ADVANCE 7

/* A hidden sprite sits above the canvas. Sprites are at most 64 tall. */
#define SPRITE_HIDDEN_Y -64

void video_init(void);
void video_blank(void);
void video_start(void);
void video_menus(void);
void video_talk(void);
void video_hide_sprites(void);
void video_text_clear(void);
void video_clear(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom);
void video_text(uint8_t col, uint8_t row, const char *s);
void video_number(uint8_t col, uint8_t row, uint16_t n, uint8_t width);
void video_box(uint8_t left, uint8_t top, uint8_t right, uint8_t bottom, uint8_t frame);
void video_rule(uint8_t left, uint8_t right, uint8_t row);

void sprite_set(unsigned sprite, unsigned image, unsigned palette, uint8_t width_height);
void sprite_move(unsigned sprite, int16_t x, int16_t y);
void sprite_hide(unsigned sprite);
void sprite_flip(unsigned sprite);
void sprite_attributes(unsigned sprite, uint8_t attributes);
void video_count(unsigned first, uint8_t sprites, int16_t x, int16_t y, uint16_t n);

#endif
