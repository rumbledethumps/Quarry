#ifndef SCENE_H
#define SCENE_H

#include <stdint.h>

void scene_menu(void);
void scene_menu_show(void);
void scene_title(int16_t y);
void scene_title_panels(uint8_t map);
void scene_title_show(int16_t x);
uint8_t scene_level(uint8_t sled_rank);
void scene_curtains(int8_t step);
void scene_panel_frame(uint8_t p, unsigned at);
void scene_picture_sled(uint8_t slot, uint8_t rank);
void scene_menus(void);
void scene_dwarf(uint8_t dwarf);
void scene_bubble(uint8_t bubble);
uint8_t scene_big_coin(void);

#endif
