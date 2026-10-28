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
   sled's colors darker, so they stay in the background. Each piece is
   drawn for the left side, and MODE5_HFLIP turns it for the right. */

#define SCENERY(field, i) (XRAM_SCENERY + offsetof(scenery_t, field) + (i) * sizeof(mode5_csprite_t))

/* A curtain is CURTAIN_COLS images across and CURTAIN_ROWS down, as
   art/curtain.py cuts it, and its rock runs CURTAIN_UNDER px under its
   post. */
static const uint8_t curtain_cols[] = {64, 36};
static const uint8_t curtain_rows[] = {64, 64, 64, 48};
#define CURTAIN_UNDER 6

/* The machine hangs this far down the right wall. Its lamp is the red of
   the shade palette, which the game lights. */
#define MACHINE_Y 140
#define LAMP_COLOR 7
#define LAMP_OFF COLOR_FROM_RGBA(92, 32, 13, 255) /* the red of the shade row */
#define LAMP_ON COLOR_FROM_RGBA(255, 64, 32, 255)

_Static_assert(sizeof curtain_cols * sizeof curtain_rows == CURTAIN_TILES, "CURTAIN_TILES is wrong.");

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
    first = SCREEN_W / 2 - (SCREEN_W / 2 - left + repeat - 1) / repeat * repeat;
    last = SCREEN_W / 2 + (right - SCREEN_W / 2 + repeat - 1) / repeat * repeat;
    piece(SCENERY(braces, 0), XRAM_BRACE_IMAGE, XRAM_FRAME_SHADE, MODE5_SIZE(BRACE_SIZE, BRACE_SIZE),
          left, BEAM_H, 0);
    piece(SCENERY(braces, 1), XRAM_BRACE_IMAGE, XRAM_FRAME_SHADE, MODE5_SIZE(BRACE_SIZE, BRACE_SIZE),
          right - BRACE_SIZE, BEAM_H, 1);
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
