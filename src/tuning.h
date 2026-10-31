/* Every gameplay number, so a playtest change is a one-line edit.
   The game steps once per VSYNC, 60 times a second. Speeds are in
   1/256 pixel per step, so 256 is one pixel per step, but for the sled's,
   in pixels a second, as its panel shows them. */

#ifndef TUNING_H
#define TUNING_H

/* A level builds up as it starts: the sled rises into place, the bricks
   are laid, the gauge fills, and a ball flies from the count to the sled,
   to land as it ends. */
#define TUNE_BUILD_STEPS 120  /* 2 seconds */
#define TUNE_RISE_STEPS 45    /* of them, the sled's rise from below the screen */

/* Balls. The balls at the start of a level are the upgrade's, below. */
#define TUNE_BALL_SPEED 640   /* 2.5 px per step */
#define TUNE_BALL_COME 1024   /* a new ball flies from the count to the sled, 4 px per step */

/* Fuel, which the code calls energy. A full gauge holds TUNE_FUEL liters,
   and it burns from the first launch of a level until the level ends, at
   the rate of the fuel efficiency bought. Energy is counted in 1/600 L,
   ENERGY_LITER of them a liter, so a burn of so many tenths of a liter a
   second takes that many a step. */
#define ENERGY_LITER 600u
#define TUNE_FUEL 100                        /* liters */
#define TUNE_ENERGY (TUNE_FUEL * ENERGY_LITER)
#define TUNE_ENERGY_MID (50 * ENERGY_LITER)  /* the meter's paddle turns yellow: the last 50 L */
#define TUNE_ENERGY_LOW (20 * ENERGY_LITER)  /* it turns red, and the beeps start: the last 20 L */

/* Out of energy: the flames sputter, then the paddle falls. */
#define TUNE_SPUTTER_STEPS 45 /* how long the flames sputter */
#define TUNE_FALL_GRAVITY 20  /* the falling paddle speeds up this much each step */

/* The level cleared or out of balls, the paddle flies home, down off the
   screen under its own power, speeding up gently to its speed. */
#define TUNE_LEAVE_ACCEL 4
#define TUNE_LEAVE_SPEED 192  /* 0.75 px per step */

/* Bricks. Where they are, and the hits that break each, are each level's,
   in levels/levels.py. */

/* Nuggets fly from a broken brick to the left panel this many pixels a
   step, along the longer of across and down. */
#define TUNE_NUGGET_SPEED 4

/* Paddle */
#define TUNE_PADDLE_Y 208     /* hover height, the top of the paddle */

/* Upgrades, paid in nuggets, in the order of their panels. Each rank of
   an upgrade has its value, starting with the value before any upgrade,
   and each rank after the first has its cost, of up to three counts of
   nuggets, each gray unless it says another color, as RED(4) is 4 red:
   {25, RED(5)} is 25 gray and 5 red. The build draws a sled for each
   width, with its jets. */
#define RED(n) ((n) | (unsigned)BRICK_RED << COST_COLOR_SHIFT)
#define GREEN(n) ((n) | (unsigned)BRICK_GREEN << COST_COLOR_SHIFT)
#define BLUE(n) ((n) | (unsigned)BRICK_BLUE << COST_COLOR_SHIFT)
#define GOLD(n) ((n) | (unsigned)BRICK_GOLD << COST_COLOR_SHIFT)
#define TUNE_BALLS {1, 2, 3, 4, 5, 6} /* at the start of a level */
#define TUNE_BALL_COSTS {{1}, {20}, {25, RED(25)}, {30, GREEN(30)}, {50, RED(50), GREEN(50)}}
#define TUNE_DAMAGES {1, 2, 3, 4, 5, 6, 7}  /* a brick's hit */
#define TUNE_DAMAGE_COSTS {{RED(1)}, {RED(10)}, {RED(25)}, {GREEN(1)}, {GREEN(10)}, {GREEN(25)}}
#define TUNE_BURNS {50, 40, 35, 31, 28, 25, 23, 21, 19, 17, 15} /* 1/10 L a second */
#define TUNE_BURN_COSTS {{5}, {10}, {25}, {25, RED(5)}, {25, RED(10)}, {25, RED(25)}, \
                         {25, RED(25), GREEN(5)}, {25, RED(25), GREEN(10)}, {25, RED(25), GREEN(25)}, \
                         {25, RED(25), GREEN(25)}}
#define TUNE_SPEEDS {100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150} /* px a second */
#define TUNE_SPEED_COSTS {{6}, {10}, {16}, {24}, {34}, {46}, {60}, {76}, {94}, {114}}
#define TUNE_WIDTHS {17, 20, 23, 26, 29, 32, 35, 38, 41, 44, 47} /* px, 64 at most */
#define TUNE_WIDTH_COSTS {{3}, {4}, {5}, {6}, {7}, {9}, {11}, {13}, {15}, {17}}
#define TUNE_JETS {1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3} /* visible jets, 3 at most */

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
