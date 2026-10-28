#ifndef SHOP_H
#define SHOP_H

#include <stdint.h>

/* What shop_step() returns. */
#define SHOP_STAY 0
#define SHOP_BEGIN 1 /* begin stage_picked */
#define SHOP_TITLE 2 /* go back to the title */

/* What the upgrade screen opens on. */
#define SHOP_ON_UPGRADES 0 /* the rail of panels, as a stage ends */
#define SHOP_ON_STAGES 1   /* the stage select, coming from the title */

void shop_open(uint8_t on);
uint8_t shop_step(void);
void shop_idle(void);
void shop_resume(void);
void shop_draw(void);

#endif
