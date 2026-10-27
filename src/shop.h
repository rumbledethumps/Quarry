#ifndef SHOP_H
#define SHOP_H

#include <stdint.h>

/* What shop_step() returns. */
#define SHOP_STAY 0
#define SHOP_BEGIN 1 /* begin stage_picked */
#define SHOP_TITLE 2 /* go back to the title */

void shop_open(void);
uint8_t shop_step(void);
void shop_draw(void);

#endif
