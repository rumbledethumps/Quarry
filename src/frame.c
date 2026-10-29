#include "frame.h"
#include "video.h"
#include "xram.h"

/* The frame of a playfield and what stands around it, all plane 0 sprites
   in front of the texture. The posts and the cap beam, of the level's
   frame set, are where the ball bounces: the bright inner face of a post
   is the edge of the playfield, and the underside of the beam its top.
   Outside the posts are the curtains, the rock of a curtain set. Behind
   the ball are a knee brace in each top corner, in the frame set's colors
   darkened, and a machine on the right wall, in the shade palette, the
   sled's colors darker, so they stay in the background, but for the
   meter through its window, which src/energy.c sets. Each piece is drawn
   for the left side, and MODE5_HFLIP turns it for the right. */

#define SCENERY(field, i) (XRAM_SCENERY + offsetof(scenery_t, field) + (i) * sizeof(mode5_csprite_t))

/* A curtain is CURTAIN_COLS images across and CURTAIN_ROWS down, as
   art/curtain.py cuts it, and its rock runs CURTAIN_UNDER px under its
   post. */
static const uint8_t curtain_cols[] = {64, 36};
static const uint8_t curtain_rows[] = {64, 64, 64, 48};
#define CURTAIN_UNDER 6

/* The machine hangs this far down the right wall. Its lamp is the red of
   the shade palette, which the game lights. Its meter is behind its
   window, which is in the middle, so the same either way round. */
#define MACHINE_Y 140
#define LAMP_COLOR 7
#define LAMP_OFF COLOR_FROM_RGBA(92, 32, 13, 255) /* the red of the shade row */
#define LAMP_ON COLOR_FROM_RGBA(255, 64, 32, 255)
#define METER_X 6  /* the meter's paddle, across the window */
#define METER_Y 11 /* its top, when it is up */

/* The meter's paddle and its shade in each of its colors, from
   METER_GREEN. */
#define PADDLE_GREEN COLOR_FROM_RGBA(64, 176, 72, 255)
#define PADDLE_YELLOW COLOR_FROM_RGBA(248, 200, 48, 255)
#define PADDLE_RED COLOR_FROM_RGBA(224, 56, 40, 255)
static const uint16_t paddle_colors[][2] = {
    {PADDLE_GREEN, COLOR_FROM_RGBA(32, 112, 48, 255)},
    {PADDLE_YELLOW, COLOR_FROM_RGBA(184, 128, 24, 255)},
    {PADDLE_RED, COLOR_FROM_RGBA(144, 28, 24, 255)},
};

_Static_assert(sizeof curtain_cols * sizeof curtain_rows == CURTAIN_TILES, "CURTAIN_TILES is wrong.");

static int16_t right_curtain; /* the left edge of the right curtain on the screen */

/* The beam's art repeats from the middle of the screen, every 8 or 12 px,
   and so from here too, a whole number of both to the left of it, and
   left of every wall. */
#define BEAM_ANCHOR (SCREEN_W / 2 - 8 * 24)

static void piece(unsigned sprite, unsigned image, unsigned palette, uint8_t size, int16_t x, int16_t y,
                  uint8_t flip)
{
    sprite_set(sprite, image, palette, size);
    if (flip)
        sprite_flip(sprite);
    sprite_move(sprite, x, y);
}

static void curtain(uint8_t side, int16_t x)
{
    unsigned image = XRAM_CURTAINS + side * CURTAIN_BYTES;
    uint8_t r, c, i = 0;
    int16_t y = 0;

    for (r = 0; r < sizeof curtain_rows; r++)
    {
        int16_t left = x;
        for (c = 0; c < sizeof curtain_cols; c++)
        {
            uint8_t w = curtain_cols[c], h = curtain_rows[r];
            piece(SCENERY(curtains, side * CURTAIN_TILES + i++), image, XRAM_PALETTE_CURTAIN,
                  MODE5_SIZE(w, h), left, y, 0);
            image += w * h / 2;
            left += w;
        }
        y += curtain_rows[r];
    }
}

/* The two curtains of the curtain set, the left one's inner edge at left
   and the right one's at right. */
void frame_curtains(int16_t left, int16_t right)
{
    curtain(0, left - CURTAIN_W);
    curtain(1, right);
    right_curtain = right;
}

/* The colors of n pixels of the right curtain from x, y on the screen, a
   byte each, into pixels: the rock behind the energy gauge. Where the
   shaft is clear, or there is no curtain, the darkest rock. */
void frame_rock(uint8_t *pixels, int16_t x, int16_t y, uint8_t n)
{
    unsigned band = XRAM_CURTAINS + CURTAIN_BYTES;
    uint8_t r = 0, i;

    while (r < sizeof curtain_rows - 1 && y >= curtain_rows[r])
    {
        band += CURTAIN_W * curtain_rows[r] / 2;
        y -= curtain_rows[r++];
    }
    for (i = 0; i < n; i++)
    {
        int16_t u = x + i - right_curtain;
        uint8_t color = 0;

        if (u >= 0 && u < CURTAIN_W)
        {
            unsigned image = band;
            uint8_t w = curtain_cols[0];

            if (u >= w)
            {
                image += w * curtain_rows[r] / 2;
                u -= w;
                w = curtain_cols[1];
            }
            color = xram0_peek8(image + y * (w / 2) + u / 2);
            color = u & 1 ? color & 15 : color >> 4;
        }
        pixels[i] = color ? color : GLASS_ROCK;
    }
}

/* The frame around a playfield from left to right, and the rest around it.
   The posts' outer faces are as far out as the frame set's posts show. A
   cap tops each post. The beam's art repeats along it from the middle of
   the screen, so it is the same at both posts, and each of its pieces
   starts on a repeat, so where two overlap they join. It runs from the
   last repeat before the left post to the first after the right one,
   behind the caps, which hide the less than a repeat under each. */
void frame_start(int16_t left, int16_t right)
{
    uint8_t look[2], shows, repeat, i;
    int16_t first, last;

    xram0_read(look, XRAM_FRAME_SHOWS, 2);
    shows = look[0];
    repeat = look[1];
    first = left - (left - BEAM_ANCHOR) % repeat;
    last = right + (repeat - (right - BEAM_ANCHOR) % repeat) % repeat;
    piece(SCENERY(braces, 0), XRAM_BRACE_IMAGE, XRAM_FRAME_SHADE, MODE5_SIZE(BRACE_SIZE, BRACE_SIZE),
          left, BEAM_H, 0);
    piece(SCENERY(braces, 1), XRAM_BRACE_IMAGE, XRAM_FRAME_SHADE, MODE5_SIZE(BRACE_SIZE, BRACE_SIZE),
          right - BRACE_SIZE, BEAM_H, 1);
    piece(SCENERY(meter, 0), XRAM_METER_IMAGE, XRAM_PALETTE_FITTING, MODE5_SIZE(METER_W, METER_H),
          right - MACHINE_W + METER_X, MACHINE_Y + METER_Y + METER_RISE, 0);
    piece(SCENERY(machine, 0), XRAM_MACHINE_IMAGE, XRAM_PALETTE_SHADE, MODE5_SIZE(MACHINE_W, MACHINE_H),
          right - MACHINE_W, MACHINE_Y, 1);
    frame_curtains(left - shows + CURTAIN_UNDER, right + shows - CURTAIN_UNDER);
    for (i = 0; i < POST_SPRITES; i++)
    {
        piece(SCENERY(posts, i), XRAM_POST_IMAGE, XRAM_FRAME_PALETTE, MODE5_SIZE(POST_W, POST_H),
              left - POST_W, i * POST_H, 0);
        piece(SCENERY(posts, POST_SPRITES + i), XRAM_POST_IMAGE, XRAM_FRAME_PALETTE,
              MODE5_SIZE(POST_W, POST_H), right, i * POST_H, 1);
    }
    for (i = 0; i < BEAM_SPRITES; i++)
    {
        int16_t x = first + i * BEAM_W;

        if (x >= last)
            sprite_hide(SCENERY(beam, i));
        else
            piece(SCENERY(beam, i), XRAM_BEAM_IMAGE, XRAM_FRAME_PALETTE, MODE5_SIZE(BEAM_W, BEAM_H),
                  x + BEAM_W > last ? last - BEAM_W : x, 0, 0);
    }
    piece(SCENERY(caps, 0), XRAM_CAP_IMAGE, XRAM_FRAME_PALETTE, MODE5_SIZE(POST_W, BEAM_H), left - POST_W, 0, 0);
    piece(SCENERY(caps, 1), XRAM_CAP_IMAGE, XRAM_FRAME_PALETTE, MODE5_SIZE(POST_W, BEAM_H), right, 0, 1);
    frame_lamp(0);
}

/* Lights the machine's lamp, or puts it out. */
void frame_lamp(uint8_t on)
{
    xram0_poke16(XRAM_PALETTE_SHADE + LAMP_COLOR * sizeof(uint16_t), on ? LAMP_ON : LAMP_OFF);
}

/* The machine's meter with its paddle risen px, from 0, down, to
   METER_RISE, up, in color, from METER_GREEN. */
void frame_meter(uint8_t risen, uint8_t color)
{
    xram0_poke16(XRAM_METER_SPRITE + offsetof(mode5_csprite_t, y_pos_px),
                 MACHINE_Y + METER_Y + METER_RISE - risen);
    xram0_poke16(XRAM_PALETTE_FITTING + METER_PADDLE * sizeof(uint16_t), paddle_colors[color][0]);
    xram0_poke16(XRAM_PALETTE_FITTING + METER_SHADE * sizeof(uint16_t), paddle_colors[color][1]);
}
