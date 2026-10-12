/* Every gameplay number, so a playtest change is a one-line edit.
   The game steps once per VSYNC, 60 times a second. Speeds are in
   1/256 pixel per step, so 256 is one pixel per step. */

#ifndef TUNING_H
#define TUNING_H

/* Balls */
#define TUNE_BALLS 5          /* balls at the start of a stage */
#define TUNE_BALL_SPEED 640   /* 2.5 px per step */

/* Energy. A full bar holds this many steps of thrust, and it drains from
   the first launch of a stage until the stage ends. */
#define TUNE_ENERGY 14400     /* 4 minutes */
#define TUNE_ENERGY_DRAIN 1   /* per step */
#define TUNE_ENERGY_LOW 2880  /* the bar turns orange: the last 48 seconds */

/* Out of energy: the flames sputter, then the paddle falls. */
#define TUNE_SPUTTER_STEPS 45 /* how long the flames sputter */
#define TUNE_FALL_GRAVITY 20  /* the falling paddle speeds up this much each step */

/* Bricks */
#define TUNE_BRICKS_Y 32      /* the top of the first row of bricks */

/* Nuggets fly from a broken brick to the left panel this many pixels a
   step, along the longer of across and down. */
#define TUNE_NUGGET_SPEED 4

/* Paddle */
#define TUNE_PADDLE_Y 208     /* hover height, the top of the paddle */

/* Upgrades, paid in white nuggets. Each level of an upgrade has its
   value, starting with the value before any upgrade, and each level after
   the first has its cost. */
#define TUNE_WIDTHS {24, 32, 40, 48, 56, 64} /* px, multiples of 8 from 16 to 64 */
#define TUNE_WIDTH_COSTS {6, 10, 16, 24, 34}
#define TUNE_SPEEDS {512, 576, 640, 704, 768} /* 2 to 3 px per step */
#define TUNE_SPEED_COSTS {6, 10, 16, 24}

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
