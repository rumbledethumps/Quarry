/* Every gameplay number, so a playtest change is a one-line edit.
   The game steps once per VSYNC, 60 times a second. Speeds are in
   1/256 pixel per step, so 256 is one pixel per step. */

#ifndef TUNING_H
#define TUNING_H

/* Balls */
#define TUNE_BALLS 5          /* balls at the start of a stage */
#define TUNE_BALL_SPEED 640   /* 2.5 px per step */

/* Bricks */
#define TUNE_BRICKS_Y 32      /* the top of the first row of bricks */

/* Paddle */
#define TUNE_PADDLE_WIDTH 24  /* px, a multiple of 8 from 16 to 64 */
#define TUNE_PADDLE_SPEED 512 /* 2 px per step */
#define TUNE_PADDLE_Y 208     /* hover height, the top of the paddle */

/* The paddle is cut into six zones of equal width. The two in the center
   send the ball up steeply, the zones beside them at 45 degrees, and the
   outer edges at a shallow angle. Each angle is a unit vector times 256:
   across, then up. */
#define TUNE_STEEP_X 88       /* 70 degrees */
#define TUNE_STEEP_Y 241
#define TUNE_MIDDLE_X 181     /* 45 degrees */
#define TUNE_MIDDLE_Y 181
#define TUNE_SHALLOW_X 222    /* 30 degrees */
#define TUNE_SHALLOW_Y 128

#endif
