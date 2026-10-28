#ifndef SCENE_H
#define SCENE_H

#include <stdint.h>

void scene_menu(void);
void scene_menu_show(void);
void scene_title(void);
void scene_stage(uint8_t sled_level);
void scene_curtains(int8_t step);
void scene_picture_sled(uint8_t slot, uint8_t level);
void scene_menus(void);
void scene_talk(uint8_t talk);

#endif
