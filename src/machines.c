#include "machines.h"
#include "video.h"
#include "xram.h"
#include <rp6502.h>

/* What moves in the upgrade screen's backdrop: the two cogs at the left of
   the floor turn all the time, and now and then the vent by the piston
   lets out a puff of steam, quietly. They are plane 0 sprites over the
   backdrop, in the slots of a stage's curtains, which this screen doesn't
   have, and in the bottom band's palette. art/backdrop.py draws their
   frames. */

#define GEAR_SPRITE(i) (XRAM_CURTAIN_SPRITES + (i) * sizeof(mode5_csprite_t))
#define STEAM_SPRITE GEAR_SPRITE(2)
#define GEAR_FRAME_BYTES (BACKDROP_GEARS_W * (BACKDROP_GEARS_H1 + BACKDROP_GEARS_H2) / 2)
#define GEAR_IMAGE(f, half) (XRAM_BACKDROP_SPRITES + (f) * GEAR_FRAME_BYTES + (half) * BACKDROP_GEARS_W * BACKDROP_GEARS_H1 / 2)
#define STEAM_IMAGE(f) (XRAM_BACKDROP_SPRITES + BACKDROP_STEAM_AT + (f) * BACKDROP_STEAM_W * BACKDROP_STEAM_H / 2)

#define GEAR_STEPS 8  /* a frame of the cogs */
#define STEAM_STEPS 5 /* a frame of the steam */
#define STEAM_WAIT 180 /* steps at least between puffs, and as many more at most */

_Static_assert(XRAM_CURTAIN_SPRITES + 3 * sizeof(mode5_csprite_t) <= XRAM_POST_SPRITES,
               "The curtains' sprites are too few for the backdrop's.");

static uint8_t gear_steps, gear_frame;
static uint16_t steam_wait;
static uint8_t steam_steps; /* into a puff, or 0 between them */
static uint8_t dirty;

static void steam_later(void)
{
    steam_wait = STEAM_WAIT + ria_attr_get(RIA_ATTR_LRAND) % STEAM_WAIT;
}

void machines_start(void)
{
    sprite_set(GEAR_SPRITE(0), GEAR_IMAGE(0, 0), XRAM_BAND_PALETTE(bottom),
               MODE5_SIZE(BACKDROP_GEARS_W, BACKDROP_GEARS_H1));
    sprite_set(GEAR_SPRITE(1), GEAR_IMAGE(0, 1), XRAM_BAND_PALETTE(bottom),
               MODE5_SIZE(BACKDROP_GEARS_W, BACKDROP_GEARS_H2));
    sprite_set(STEAM_SPRITE, STEAM_IMAGE(0), XRAM_BAND_PALETTE(bottom),
               MODE5_SIZE(BACKDROP_STEAM_W, BACKDROP_STEAM_H));
    sprite_move(GEAR_SPRITE(0), BACKDROP_GEARS_X, BACKDROP_GEARS_Y);
    sprite_move(GEAR_SPRITE(1), BACKDROP_GEARS_X, BACKDROP_GEARS_Y + BACKDROP_GEARS_H1);
    gear_steps = gear_frame = steam_steps = 0;
    steam_later();
}

/* The cogs turn a frame every GEAR_STEPS, and the steam waits, or puffs. */
void machines_step(void)
{
    if (++gear_steps == GEAR_STEPS)
    {
        gear_steps = 0;
        gear_frame = (gear_frame + 1) % BACKDROP_GEAR_FRAMES;
        dirty = 1;
    }
    if (steam_steps)
    {
        if (++steam_steps == BACKDROP_STEAM_FRAMES * STEAM_STEPS + 1)
        {
            steam_steps = 0;
            steam_later();
        }
        dirty = 1;
    }
    else if (!--steam_wait)
    {
        steam_steps = 1;
        dirty = 1;
    }
}

/* At the start of a frame: the cogs' frame, and the steam's. */
void machines_draw(void)
{
    if (!dirty)
        return;
    dirty = 0;
    xram0_poke16(GEAR_SPRITE(0) + offsetof(mode5_csprite_t, xram_sprite_ptr), GEAR_IMAGE(gear_frame, 0));
    xram0_poke16(GEAR_SPRITE(1) + offsetof(mode5_csprite_t, xram_sprite_ptr), GEAR_IMAGE(gear_frame, 1));
    if (steam_steps)
    {
        xram0_poke16(STEAM_SPRITE + offsetof(mode5_csprite_t, xram_sprite_ptr),
                     STEAM_IMAGE((steam_steps - 1) / STEAM_STEPS));
        sprite_move(STEAM_SPRITE, BACKDROP_STEAM_X, BACKDROP_STEAM_Y);
    }
    else
        sprite_hide(STEAM_SPRITE);
}
