#ifndef TALK_H
#define TALK_H

#include <stdint.h>
#include <talks.h>

/* talk_state */
#define TALK_OFF 0
#define TALK_IN 1    /* he and his bubble coming in */
#define TALK_WAIT 2  /* in, before the OK shows */
#define TALK_READY 3 /* the OK showing, with the cursor round it */
#define TALK_OUT 4   /* going */

extern uint8_t talk_state;

void talk_queue(uint8_t talk);
void talk_once(uint8_t talk);
uint8_t talk_busy(void);
uint8_t talk_step(void);
void talk_draw(void);
void talk_stop(void);

#endif
