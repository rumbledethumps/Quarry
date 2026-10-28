#include "cursor.h"
#include "video.h"
#include "xram.h"

/* The holographic cursor: four bright corners around what is picked, on
   the upgrade screen or in a menu on any screen. Placed while it shows, it
   slides to its new place, fast and then settling; placed while hidden, it
   appears there at once. All the while, it breathes, its corners drifting
   out and back, and its two brightest colors pulse. Its sprites are the
   last of plane 2's, over everything. cursor_step() moves
   it, and cursor_draw() puts it there at the start of the next frame, so
   it doesn't move while the frame is drawn. */

#define CORNER(i) (XRAM_CURSOR_SPRITES + (i) * sizeof(mode5_csprite_t))

/* How far out the corners are, in px, for each BEAT steps of a breath.
   The shimmer takes 4 beats, so a breath holds 3 of them. */
#define BEAT 6
static const uint8_t breath[] = {0, 0, 1, 1, 2, 2, 2, 2, 1, 1, 0, 0};

static int16_t at[4], to[4]; /* left, top, right, bottom */
static uint8_t shown, dirty, steps;
static uint8_t out; /* how far out the corners were put */

static void corners_move(void)
{
    uint8_t i;

    out = breath[steps / BEAT];
    for (i = 0; i < 4; i++)
        sprite_move(CORNER(i), i & 1 ? at[2] + out - 8 : at[0] - out, i & 2 ? at[3] + out - 8 : at[1] - out);
}

/* Steps a value a quarter of the way to where it is going, at least a
   pixel, so it slides fast and settles slowly. */
static int16_t ease(int16_t now, int16_t then)
{
    int16_t step = (then - now) / 4;

    if (!step)
        step = then > now ? 1 : then < now ? -1 : 0;
    return now + step;
}

/* The cursor goes around the box from left, top to right, bottom, its
   corners inside it. */
void cursor_place(int16_t left, int16_t top, int16_t right, int16_t bottom)
{
    static const uint8_t flips[] = {0, MODE5_HFLIP, MODE5_VFLIP, MODE5_HFLIP | MODE5_VFLIP};
    uint8_t i;

    to[0] = left;
    to[1] = top;
    to[2] = right;
    to[3] = bottom;
    if (!shown)
    {
        for (i = 0; i < 4; i++)
        {
            at[i] = to[i];
            sprite_set(CORNER(i), XRAM_CURSOR_IMAGE, XRAM_PALETTE_HOLO, MODE5_SIZE(8, 8));
            sprite_attributes(CORNER(i), flips[i]);
        }
        corners_move();
        shown = 1;
        return;
    }
    dirty = 1;
}

/* Hidden, so the next place it goes it appears at once. A new screen
   hides it, as it hides every sprite. */
void cursor_hide(void)
{
    uint8_t i;

    for (i = 0; i < 4; i++)
        sprite_hide(CORNER(i));
    shown = dirty = 0;
}

void cursor_step(void)
{
    uint8_t i;

    if (++steps == sizeof breath * BEAT)
        steps = 0;
    if (!shown)
        return;
    for (i = 0; i < 4; i++)
        if (at[i] != to[i])
        {
            at[i] = ease(at[i], to[i]);
            dirty = 1;
        }
}

/* At the start of a frame: the cursor shimmers, and moves to where it got
   and as far out as its breath has it. */
void cursor_draw(void)
{
    static const uint16_t bright[] = {
        COLOR_FROM_RGBA(200, 251, 255, 255), COLOR_FROM_RGBA(150, 240, 255, 255),
        COLOR_FROM_RGBA(110, 220, 245, 255), COLOR_FROM_RGBA(150, 240, 255, 255)};
    static const uint16_t middle[] = {
        COLOR_FROM_RGBA(79, 216, 240, 255), COLOR_FROM_RGBA(60, 190, 220, 255),
        COLOR_FROM_RGBA(40, 160, 200, 255), COLOR_FROM_RGBA(60, 190, 220, 255)};
    uint8_t phase = steps / BEAT % 4;

    if (!shown)
        return;
    xram0_poke16(XRAM_PALETTE_HOLO + 4 * sizeof(uint16_t), bright[phase]);
    xram0_poke16(XRAM_PALETTE_HOLO + 3 * sizeof(uint16_t), middle[phase]);
    if (!dirty && out == breath[steps / BEAT])
        return;
    dirty = 0;
    corners_move();
}
