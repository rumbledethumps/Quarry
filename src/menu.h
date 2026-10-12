#ifndef MENU_H
#define MENU_H

#include <stdint.h>

/* What menu_step() returns. */
#define MENU_NONE 0
#define MENU_UPGRADES 1
#define MENU_PLAY 2

void menu_open(const char *title, uint8_t pick, uint8_t wait);
void menu_close(void);
uint8_t menu_step(void);

#endif
