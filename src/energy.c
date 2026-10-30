#include "energy.h"
#include "debug.h"
#include "frame.h"
#include "sfx.h"
#include "tuning.h"
#include "upgrades.h"
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
#define LAMP_STEPS 24

/* The machine's meter shows how the fuel stands: its paddle is green, then
   yellow from TUNE_ENERGY_MID, and red from TUNE_ENERGY_LOW. When that
   changes, the paddle slides down out of sight a px every METER_STEPS
   steps, and back up in its new color. As a level builds up, it slides
   down and stays down, and once the first ball lands, it comes up green,
   as a meter's does when its knob is turned. */
#define METER_STEPS 2

/* A bubble rises BUBBLE_SPEED sixteenths of a px a step, from the foot of
   the fuel to its surface, and sways a px either way as it goes, a step of
   the sway every 8 px. At the surface it pops and throws up a drop, which
   hops up to DROP_PEAK px over the surface and falls back in, and then
   the bubble is free again. */
#define BUBBLE_SPEED 16
#define BUBBLE_SPRITE(i) GAUGE_SPRITE(bubbles, i)
#define DROP_PEAK 3

/* A refill sends a bubble up from the foot after FILL_BUBBLE_MIN to
   FILL_BUBBLE_MAX steps of the fuel rising, at random, and so on while it
   rises: about 12 over a refill from empty in TUNE_BUILD_STEPS. */
#define FILL_BUBBLE_MIN 5
#define FILL_BUBBLE_MAX 15

/* The energy a cheat adds or takes away, a twelfth of a full gauge. */
#define CHEAT_ENERGY ((TUNE_ENERGY + 11) / 12)

_Static_assert(TUNE_ENERGY_LOW < TUNE_ENERGY, "TUNE_ENERGY_LOW must be less than TUNE_ENERGY.");
_Static_assert(GLASS_PIECES == (GLASS_H + PIECE_H - 1) / PIECE_H, "GLASS_PIECES is wrong.");
_Static_assert(LIQUID_SEGMENTS * LIQUID_H <= GLASS_H, "The runs of fuel fit in the glass.");

uint16_t energy;
uint8_t energy_draining;

static int16_t gauge_x, glass_y; /* the gauge's left, and its glass's top */
static uint8_t rows;             /* of fuel in the glass */
static uint8_t rows_drawn;       /* as its sprites show them */
static uint16_t bubble_y[BUBBLES]; /* the top of each bubble, in 1/16 px, or 0 for none */
static uint8_t bubble_x[BUBBLES];  /* its left, from the glass's, before it sways; its drop's, once popped */
static uint8_t bubble_pop[BUBBLES]; /* steps of its drop's hop, from 1, once it pops */
static const int8_t sway[] = {0, 1, 0, -1};
static const uint8_t hop[] = {1, 1, 2, 2, DROP_PEAK, DROP_PEAK, DROP_PEAK, DROP_PEAK, DROP_PEAK, DROP_PEAK, 2, 2, 1, 1};
static uint8_t beep_steps;
static uint8_t lamp_steps;
static uint8_t meter_on;    /* whether the paddle may show, once the first ball lands */
static uint8_t meter_color; /* the paddle's, from METER_GREEN */
static uint8_t meter_risen; /* px, from 0, down, to METER_RISE, up */
static uint8_t meter_steps;
static uint8_t meter_drawn; /* the px risen and the color its sprite shows */
static uint8_t fill_wait;   /* steps of a refill until its next bubble */

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

/* The rows of fuel for the energy: a row for each GLASS_H-th of
   TUNE_ENERGY, or part of one. */
static void rows_count(void)
{
    rows = ((uint32_t)energy * GLASS_H + TUNE_ENERGY - 1) / TUNE_ENERGY;
}

/* A bubble from the foot of the fuel, if there is fuel and a bubble free.
   None is ever taken from another, so each rises all the way. It starts
   somewhere across the glass, where it and its sway stay inside the
   outline. */
void energy_bubble(void)
{
    uint8_t i;

    if (!rows)
        return;
    for (i = 0; i < BUBBLES; i++)
        if (!bubble_y[i])
        {
            bubble_y[i] = (glass_y + GLASS_H - BUBBLE_SIZE) << 4;
            bubble_x[i] = 2 + rand() % (GLASS_W - 6);
            return;
        }
}

/* Each bubble a step up, until its top reaches the surface, where it pops,
   and its drop a step through its hop, and when the drop is back in the
   fuel, the bubble is gone. */
static void bubbles_step(void)
{
    int16_t surface = glass_y + GLASS_H - rows;
    uint8_t i;

    for (i = 0; i < BUBBLES; i++)
    {
        if (!bubble_y[i])
            continue;
        if (bubble_pop[i])
        {
            if (++bubble_pop[i] > sizeof hop)
                bubble_y[i] = bubble_pop[i] = 0;
        }
        else
        {
            int16_t y = (bubble_y[i] -= BUBBLE_SPEED) >> 4;

            if (y <= surface + 1)
            {
                bubble_x[i] += sway[y >> 3 & 3] + 1; /* the drop, from the middle of the ring */
                bubble_pop[i] = 1;
            }
        }
    }
}

/* Every METER_STEPS steps, the paddle moves a px: down while its color is
   not the fuel's, or it may not show, taking the fuel's once it is down,
   and then up. */
static void meter_step(void)
{
    uint8_t color = energy <= TUNE_ENERGY_LOW ? METER_RED : energy <= TUNE_ENERGY_MID ? METER_YELLOW : METER_GREEN;

    if (++meter_steps < METER_STEPS)
        return;
    meter_steps = 0;
    if (color != meter_color || !meter_on)
    {
        if (meter_risen)
            meter_risen--;
        else
            meter_color = color;
    }
    else if (meter_risen < METER_RISE)
        meter_risen++;
}

/* A bubble's sprite at x, y with its image, in one write. */
static void bubble_show(unsigned sprite, unsigned image, int16_t x, int16_t y)
{
    int16_t s[3];

    s[0] = x;
    s[1] = y;
    s[2] = image;
    xram0_write(sprite, s, sizeof s);
}

/* The gauge's sprites as the fuel and the bubbles are, and the meter's, at
   the start of a step, as a level draws all of its sprites, back to
   front. The fuel is its surface, over the runs of it from the foot of the
   glass up, each shown whole or not at all. The surface reaches down to
   the first run, or to the foot of the glass, so it never shows past the
   nut. */
void energy_draw(void)
{
    int16_t foot = glass_y + GLASS_H, top = foot - rows;
    uint8_t i;

    if ((meter_risen << 2 | meter_color) != meter_drawn)
    {
        frame_meter(meter_risen, meter_color);
        meter_drawn = meter_risen << 2 | meter_color;
    }
    if (rows != rows_drawn)
    {
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
        rows_drawn = rows;
    }
    for (i = 0; i < BUBBLES; i++)
    {
        if (!bubble_y[i])
            sprite_hide(BUBBLE_SPRITE(i));
        else if (bubble_pop[i])
            bubble_show(BUBBLE_SPRITE(i), XRAM_DROP_IMAGE, gauge_x + GLASS_X + bubble_x[i], top - hop[bubble_pop[i] - 1]);
        else
        {
            int16_t y = bubble_y[i] >> 4;

            bubble_show(BUBBLE_SPRITE(i), XRAM_BUBBLE_IMAGE, gauge_x + GLASS_X + bubble_x[i] + sway[y >> 3 & 3], y);
        }
    }
}

#ifndef NDEBUG
/* A cheat: adds a twelfth of the energy, up to full, or takes it away. */
void energy_cheat(int8_t steps)
{
    int32_t more = energy + (int32_t)steps * CHEAT_ENERGY;

    energy = more < 0 ? 0 : more > TUNE_ENERGY ? TUNE_ENERGY : more;
    rows_count();
    DEBUG_LOG("cheat: energy %u\n", energy);
}
#endif

static void fill_wait_pick(void)
{
    fill_wait = FILL_BUBBLE_MIN + rand() % (FILL_BUBBLE_MAX - FILL_BUBBLE_MIN + 1);
}

/* A step of a refill, raising the fuel to energy, unless it holds as much
   already. The bubbles rising through it rise with it, a px for each px
   it rises, and while it rises, it sends up more now and then. */
void energy_fill(uint16_t to)
{
    uint8_t was = rows, i;

    if (to <= energy)
        return;
    energy = to < TUNE_ENERGY ? to : TUNE_ENERGY;
    rows_count();
    for (i = 0; i < BUBBLES; i++)
        if (bubble_y[i] && !bubble_pop[i])
            bubble_y[i] -= (rows - was) << 4;
    if (!--fill_wait)
    {
        energy_bubble();
        fill_wait_pick();
    }
}

/* The meter's paddle down out of sight at once, while the menu at the end
   of a level covers it, so the level played again starts with it down. */
void energy_meter_down(void)
{
    meter_on = 0;
    meter_risen = 0;
}

/* The first ball has landed: the meter's paddle may come up. */
void energy_ready(void)
{
    meter_on = 1;
}

/* The gauge, with its top left at x, y, its glass made from the rock
   behind it, which must be in place, and the meter's paddle going down.
   On a new screen it starts empty, the paddle down. On the level played
   again, it keeps the fuel it had, and its bubbles, and the paddle slides
   down from where it was. */
void energy_start(int16_t x, int16_t y, uint8_t again)
{
    uint8_t i;

    if (!again)
    {
        energy = 0;
        meter_color = METER_GREEN;
        meter_risen = 0;
        for (i = 0; i < BUBBLES; i++)
            bubble_y[i] = bubble_pop[i] = 0;
    }
    energy_draining = 0;
    meter_on = meter_steps = 0;
    fill_wait_pick();
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
        sprite_set(BUBBLE_SPRITE(i), XRAM_BUBBLE_IMAGE, XRAM_PALETTE_LIQUID, MODE5_SIZE(BUBBLE_SIZE, BUBBLE_SIZE));
    for (i = 0; i < 2; i++)
    {
        sprite_set(GAUGE_SPRITE(fittings, i), XRAM_FITTING_IMAGE, XRAM_PALETTE_FITTING, MODE5_SIZE(GAUGE_W, FITTING_H));
        if (i)
            sprite_attributes(GAUGE_SPRITE(fittings, i), MODE5_VFLIP);
        sprite_move(GAUGE_SPRITE(fittings, i), x, i ? glass_y + GLASS_H : y);
    }
    rows_count();
    rows_drawn = 0xFF;
    lamp_steps = 0;
    meter_drawn = 0xFF;
    energy_draw();
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
    uint8_t burn = upgrades_burn();

    bubbles_step();
    meter_step();
    if (lamp_steps && !--lamp_steps)
        frame_lamp(0);
    if (!energy_draining || !energy)
        return;
    if (energy > burn)
        energy -= burn;
    else
        energy = 0;
    if (energy <= TUNE_ENERGY_LOW && was > TUNE_ENERGY_LOW)
    {
        beep(SFX_LOW);
        DEBUG_LOG("energy low\n");
    }
    else if (energy <= TUNE_ENERGY_LOW && energy && ++beep_steps >= LOW_BEEP_STEPS)
        beep(SFX_LOW_BEEP);
    rows_count();
}

/* After the level ends, and while a dwarf talks, the bubbles still rise
   and pop, and the meter's paddle still slides. */
void energy_idle(void)
{
    bubbles_step();
    meter_step();
}
