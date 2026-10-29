#include "energy.h"
#include "debug.h"
#include "frame.h"
#include "sfx.h"
#include "tuning.h"
#include "video.h"
#include "xram.h"
#include <stdlib.h>

#define GAUGE_SPRITE(field, i) (XRAM_GAUGE_SPRITES + offsetof(gauge_sprites_t, field) + (i) * sizeof(mode5_csprite_t))
#define GLASS_ROW_BYTES (GLASS_W / 2)
#define PIECE_H 64 /* of the glass, the tallest a sprite can be */

/* While the energy is low, a beep every LOW_BEEP_STEPS steps, and the
   machine's lamp lights with each for LAMP_STEPS, so the machine reads as
   what powers the paddle. */
#define LOW_BEEP_STEPS 180
#define LAMP_STEPS 12

/* A bubble rises BUBBLE_SPEED sixteenths of a px a step, from the foot of
   the fuel to its surface, and sways a px either way as it goes, a step of
   the sway every 8 px. */
#define BUBBLE_SPEED 16
#define BUBBLE_SPRITE(i) GAUGE_SPRITE(bubbles, i)

/* The energy a cheat adds or takes away, a twelfth of a full gauge. */
#define CHEAT_ENERGY ((TUNE_ENERGY + 11) / 12)

_Static_assert(TUNE_ENERGY_LOW < TUNE_ENERGY, "TUNE_ENERGY_LOW must be less than TUNE_ENERGY.");
_Static_assert(GLASS_PIECES == (GLASS_H + PIECE_H - 1) / PIECE_H, "GLASS_PIECES is wrong.");
_Static_assert(LIQUID_SEGMENTS * LIQUID_H <= GLASS_H, "The runs of fuel fit in the glass.");

uint16_t energy;
uint8_t energy_draining;

static int16_t gauge_x, glass_y; /* the gauge's left, and its glass's top */
static uint8_t rows_shown;       /* of fuel in the glass */
static uint16_t bubble_y[BUBBLES]; /* the top of each bubble, in 1/16 px, or 0 for none */
static uint8_t bubble_x[BUBBLES];  /* its left, from the glass's, before it sways */
static const int8_t sway[] = {0, 1, 0, -1};
static uint8_t beep_steps;
static uint8_t lamp_steps;

/* The glass, from the rock behind it: each row the right curtain's pixels
   there, in the glass palette, an outline down each side, and the glint. */
static void glass_make(void)
{
    uint8_t row[GLASS_W], bytes[GLASS_ROW_BYTES], y, i;
    unsigned image = XRAM_GLASS_IMAGE;

    row[0] = row[GLASS_W - 1] = GLASS_OUTLINE;
    for (y = 0; y < GLASS_H; y++)
    {
        frame_rock(row + 1, gauge_x + GLASS_X + 1, glass_y + y, GLASS_W - 2);
        row[GLINT_COL] = GLASS_GLINT;
        for (i = 0; i < GLASS_ROW_BYTES; i++)
            bytes[i] = row[2 * i] << 4 | row[2 * i + 1];
        xram0_write(image, bytes, sizeof bytes);
        image += sizeof bytes;
    }
}

/* The fuel, a row of it for each GLASS_H-th of TUNE_ENERGY, or part of
   one: its surface, over the runs of it from the foot of the glass up,
   each shown whole or not at all. The surface reaches down to the first
   run, or to the foot of the glass, so it never shows past the nut. */
static void gauge_draw(void)
{
    uint8_t rows = ((uint32_t)energy * GLASS_H + TUNE_ENERGY - 1) / TUNE_ENERGY, i;
    int16_t foot = glass_y + GLASS_H, top = foot - rows;

    if (rows == rows_shown)
        return;
    rows_shown = rows;
    for (i = 0; i < LIQUID_SEGMENTS; i++)
    {
        int16_t run = foot - (i + 1) * LIQUID_H;

        if (run >= top)
            sprite_move(GAUGE_SPRITE(liquid, i), gauge_x + GLASS_X, run);
        else
            sprite_hide(GAUGE_SPRITE(liquid, i));
    }
    if (rows)
    {
        uint8_t h = rows + 1 < LIQUID_H ? (rows + 4) & ~3 : LIQUID_H;

        xram0_poke8(XRAM_SURFACE_SPRITE + offsetof(mode5_csprite_t, width_height), MODE5_SIZE(GLASS_W, h));
        sprite_move(XRAM_SURFACE_SPRITE, gauge_x + GLASS_X, top - 1);
    }
    else
        sprite_hide(XRAM_SURFACE_SPRITE);
}

/* A bubble from the foot of the fuel, if there is fuel and a bubble free.
   None is ever taken from another, so each rises all the way. It starts
   somewhere across the glass, where it and its sway stay inside the
   outline. */
void energy_bubble(void)
{
    uint8_t i;

    if (!rows_shown)
        return;
    for (i = 0; i < BUBBLES; i++)
        if (!bubble_y[i])
        {
            bubble_y[i] = (glass_y + GLASS_H - BUBBLE_SIZE) << 4;
            bubble_x[i] = 2 + rand() % (GLASS_W - 6);
            return;
        }
}

/* Each bubble a step up, until its top reaches the surface, and it is
   gone. */
static void bubbles_step(void)
{
    int16_t surface = glass_y + GLASS_H - rows_shown;
    uint8_t i;

    for (i = 0; i < BUBBLES; i++)
    {
        int16_t y;

        if (!bubble_y[i])
            continue;
        bubble_y[i] -= BUBBLE_SPEED;
        y = bubble_y[i] >> 4;
        if (y <= surface + 1)
        {
            bubble_y[i] = 0;
            sprite_hide(BUBBLE_SPRITE(i));
        }
        else
            sprite_move(BUBBLE_SPRITE(i), gauge_x + GLASS_X + bubble_x[i] + sway[y >> 3 & 3], y);
    }
}

#ifndef NDEBUG
/* A cheat: adds a twelfth of the energy, up to full, or takes it away. */
void energy_cheat(int8_t steps)
{
    int16_t more = energy + steps * (int16_t)CHEAT_ENERGY;

    energy = more < 0 ? 0 : more > TUNE_ENERGY ? TUNE_ENERGY : more;
    gauge_draw();
    DEBUG_LOG("cheat: energy %u\n", energy);
}
#endif

/* A full gauge, with its top left at x, y: its glass made from the rock
   behind it, which must be in place. */
void energy_start(int16_t x, int16_t y)
{
    uint8_t i;

    energy = TUNE_ENERGY;
    energy_draining = 0;
    gauge_x = x;
    glass_y = y + FITTING_H;
    glass_make();
    for (i = 0; i < GLASS_PIECES; i++)
    {
        uint8_t top = i * PIECE_H, h = i < GLASS_PIECES - 1 ? PIECE_H : GLASS_H - top;

        sprite_set(GAUGE_SPRITE(glass, i), XRAM_GLASS_IMAGE + top * GLASS_ROW_BYTES, XRAM_PALETTE_GLASS,
                   MODE5_SIZE(GLASS_W, h));
        sprite_move(GAUGE_SPRITE(glass, i), x + GLASS_X, glass_y + top);
    }
    for (i = 0; i < LIQUID_SEGMENTS; i++)
        sprite_set(GAUGE_SPRITE(liquid, i), XRAM_LIQUID_IMAGE, XRAM_PALETTE_LIQUID, MODE5_SIZE(GLASS_W, LIQUID_H));
    sprite_set(XRAM_SURFACE_SPRITE, XRAM_SURFACE_IMAGE, XRAM_PALETTE_LIQUID, MODE5_SIZE(GLASS_W, LIQUID_H));
    for (i = 0; i < BUBBLES; i++)
    {
        bubble_y[i] = 0;
        sprite_set(BUBBLE_SPRITE(i), XRAM_BUBBLE_IMAGE, XRAM_PALETTE_LIQUID, MODE5_SIZE(BUBBLE_SIZE, BUBBLE_SIZE));
    }
    for (i = 0; i < 2; i++)
    {
        sprite_set(GAUGE_SPRITE(fittings, i), XRAM_FITTING_IMAGES + i * sizeof(fitting_image_t), XRAM_PALETTE_BRASS,
                   MODE5_SIZE(GAUGE_W, FITTING_H));
        sprite_move(GAUGE_SPRITE(fittings, i), x, i ? glass_y + GLASS_H : y);
    }
    rows_shown = 0xFF;
    lamp_steps = 0;
    gauge_draw();
}

static void beep(uint8_t sound)
{
    sfx_play(sound, SFX_CENTER);
    beep_steps = 0;
    lamp_steps = LAMP_STEPS;
    frame_lamp(1);
}

void energy_step(void)
{
    uint16_t was = energy;

    bubbles_step();
    if (lamp_steps && !--lamp_steps)
        frame_lamp(0);
    if (!energy_draining || !energy)
        return;
    if (energy > TUNE_ENERGY_DRAIN)
        energy -= TUNE_ENERGY_DRAIN;
    else
        energy = 0;
    if (energy <= TUNE_ENERGY_LOW && was > TUNE_ENERGY_LOW)
    {
        beep(SFX_LOW);
        DEBUG_LOG("energy low\n");
    }
    else if (energy <= TUNE_ENERGY_LOW && energy && ++beep_steps >= LOW_BEEP_STEPS)
        beep(SFX_LOW_BEEP);
    gauge_draw();
}
