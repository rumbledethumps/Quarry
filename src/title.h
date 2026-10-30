#ifndef TITLE_H
#define TITLE_H

#include <stdint.h>

/* What title_step() returns. */
#define TITLE_NONE 0
#define TITLE_CONTINUE 1 /* the save, on the upgrade screen */
#define TITLE_START 2    /* a new game, as there is no save */

void title_open(void);
uint8_t title_step(void);

#endif
