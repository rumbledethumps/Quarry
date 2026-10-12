#include "energy.h"
#include "debug.h"
#include "sfx.h"
#include "tuning.h"
#include "video.h"
#include "xram.h"

#define BAR_SPRITE(i) (XRAM_ENERGY_SPRITES + (i) * sizeof(mode5_csprite_t))
#define BAR_IMAGE(i) (XRAM_ENERGY_IMAGES + (i) * sizeof(energy_image_t))
#define BAR_PIECE_H 4

/* While the energy is low, a beep every LOW_BEEP_STEPS steps. */
#define LOW_BEEP_STEPS 180

/* The energy each segment of the bar stands for. */
#define SEGMENT_ENERGY ((TUNE_ENERGY + ENERGY_SEGMENTS - 1) / ENERGY_SEGMENTS)

_Static_assert(TUNE_ENERGY_LOW < TUNE_ENERGY, "TUNE_ENERGY_LOW must be less than TUNE_ENERGY.");

uint16_t energy;
uint8_t energy_draining;

static uint8_t lit_shown; /* segments lit on the bar */
static uint8_t beep_steps;
static uint8_t low_shown; /* the lit segments are orange */

/* Lights a segment for each SEGMENT_ENERGY left, or part of it, from the
   bottom up. They turn from yellow to orange when the energy is low. */
static void bar_draw(void)
{
    uint8_t lit = (energy + SEGMENT_ENERGY - 1) / SEGMENT_ENERGY;
    uint8_t low = energy <= TUNE_ENERGY_LOW;
    uint8_t i;

    if (lit == lit_shown && low == low_shown)
        return;
    for (i = 0; i < ENERGY_SEGMENTS; i++)
    {
        uint8_t image = i < ENERGY_SEGMENTS - lit ? ENERGY_EMPTY : low ? ENERGY_LOW : ENERGY_FULL;
        xram0_poke16(BAR_SPRITE(1 + i) + offsetof(mode5_csprite_t, xram_sprite_ptr), BAR_IMAGE(image));
    }
    lit_shown = lit;
    low_shown = low;
}

/* A full bar, with its top left at x, y. */
void energy_start(int16_t x, int16_t y)
{
    uint8_t i;

    energy = TUNE_ENERGY;
    energy_draining = 0;
    for (i = 0; i < ENERGY_SEGMENTS + 2; i++)
    {
        uint8_t image = i == 0 ? ENERGY_TOP : i == ENERGY_SEGMENTS + 1 ? ENERGY_BOTTOM : ENERGY_EMPTY;
        sprite_set(BAR_SPRITE(i), BAR_IMAGE(image), XRAM_PALETTE_FX, MODE5_SIZE(28, BAR_PIECE_H));
        sprite_move(BAR_SPRITE(i), x, y + i * BAR_PIECE_H);
    }
    lit_shown = 0;
    low_shown = 0;
    bar_draw();
}

void energy_step(void)
{
    uint16_t was = energy;

    if (!energy_draining || !energy)
        return;
    if (energy > TUNE_ENERGY_DRAIN)
        energy -= TUNE_ENERGY_DRAIN;
    else
        energy = 0;
    if (energy <= TUNE_ENERGY_LOW && was > TUNE_ENERGY_LOW)
    {
        sfx_play(SFX_LOW, SFX_CENTER);
        beep_steps = 0;
        DEBUG_LOG("energy low\n");
    }
    else if (energy <= TUNE_ENERGY_LOW && energy && ++beep_steps >= LOW_BEEP_STEPS)
    {
        sfx_play(SFX_LOW_BEEP, SFX_CENTER);
        beep_steps = 0;
    }
    bar_draw();
}
