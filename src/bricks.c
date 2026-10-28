#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "sfx.h"
#include "video.h"
#include "xram.h"

#define BREAK_IMAGE(i) (XRAM_BREAK_IMAGES + (i) * sizeof(break_image_t))

/* A broken brick shows each frame of its break for BREAK_STEPS steps,
   then a nugget flies from where it was. The break frames are taller than
   the brick, by BREAK_OVER above and below. */
#define BREAK_STEPS 4
#define BREAK_OVER 4

/* Stage 1 is 4 by 4 white bricks, with half a brick of space at each
   wall. Until the stages are designed, each one after it is a column
   wider, up to STAGE_COLS_MAX. */
#define STAGE1_COLS 4
#define STAGE1_ROWS 4
#define STAGE1_MARGIN (BRICK_W / 2)
#define STAGE_COLS_MAX 10

_Static_assert(STAGE_COLS_MAX * STAGE1_ROWS <= BRICKS_MAX, "A stage has too many bricks.");
_Static_assert(BRICK_W % (BEAM_W / 2) == 0 && 2 * STAGE1_MARGIN % (BEAM_W / 2) == 0,
               "The frame's beam needs a playfield a multiple of BEAM_W / 2 wide.");

uint8_t bricks_cols;
uint8_t bricks_margin;
uint8_t bricks_left;
int16_t bricks_hit_left;
int16_t bricks_hit_right;
int16_t bricks_hit_top;
int16_t bricks_hit_bottom;

/* Bricks are sprites, so each one keeps its own position. */
static uint8_t brick_count;
static int16_t brick_x[BRICKS_MAX];
static int16_t brick_y[BRICKS_MAX];
static uint8_t brick_alive[BRICKS_MAX];
static uint8_t brick_color[BRICKS_MAX];
static uint8_t brick_breaking[BRICKS_MAX]; /* steps into the break, 0 if not */

static unsigned brick_sprite(uint8_t i)
{
    return XRAM_BRICKS + i * sizeof(mode5_csprite_t);
}

/* Sets the size of a stage, from 1, before the frame goes up around it. */
void bricks_layout(uint8_t stage)
{
    bricks_cols = STAGE1_COLS + stage - 1 < STAGE_COLS_MAX ? STAGE1_COLS + stage - 1 : STAGE_COLS_MAX;
    bricks_margin = STAGE1_MARGIN;
}

/* A brick still breaking counts its nugget now, and its sprite is hidden. */
void bricks_finish(void)
{
    uint8_t i;

    for (i = 0; i < brick_count; i++)
        if (brick_breaking[i])
        {
            brick_breaking[i] = 0;
            sprite_hide(brick_sprite(i));
            nuggets_add(brick_color[i]);
        }
}

void bricks_start(int16_t left, int16_t top)
{
    uint8_t i;

    bricks_finish();
    bricks_left = 0;
    brick_count = bricks_cols * STAGE1_ROWS;
    for (i = 0; i < brick_count; i++)
    {
        brick_x[i] = left + (i % bricks_cols) * BRICK_W;
        brick_y[i] = top + (i / bricks_cols) * BRICK_H;
        brick_alive[i] = 1;
        brick_color[i] = BRICK_WHITE;
        brick_breaking[i] = 0;
        sprite_set(brick_sprite(i), XRAM_BRICK_IMAGE, XRAM_PALETTE_BRICK(brick_color[i]),
                   MODE5_SIZE(BRICK_W, BRICK_H));
        if (brick_alive[i])
        {
            bricks_left++;
            sprite_move(brick_sprite(i), brick_x[i], brick_y[i]);
        }
    }
}

static uint8_t brick_overlaps(uint8_t i, int16_t x, int16_t y, uint8_t w, uint8_t h)
{
    return brick_alive[i] &&
           x < brick_x[i] + BRICK_W && x + w > brick_x[i] &&
           y < brick_y[i] + BRICK_H && y + h > brick_y[i];
}

/* Breaks every brick that overlaps the box, and returns how many broke.
   A broken brick is gone at once, and its sprite shows the break. */
uint8_t bricks_hit(int16_t x, int16_t y, uint8_t w, uint8_t h)
{
    uint8_t i, hits = 0;

    for (i = 0; i < brick_count; i++)
    {
        if (!brick_overlaps(i, x, y, w, h))
            continue;
        if (!hits || brick_x[i] < bricks_hit_left)
            bricks_hit_left = brick_x[i];
        if (!hits || brick_x[i] + BRICK_W > bricks_hit_right)
            bricks_hit_right = brick_x[i] + BRICK_W;
        if (!hits || brick_y[i] < bricks_hit_top)
            bricks_hit_top = brick_y[i];
        if (!hits || brick_y[i] + BRICK_H > bricks_hit_bottom)
            bricks_hit_bottom = brick_y[i] + BRICK_H;
        brick_alive[i] = 0;
        brick_breaking[i] = 1;
        bricks_left--;
        hits++;
        sprite_set(brick_sprite(i), BREAK_IMAGE(0), XRAM_PALETTE_BRICK(brick_color[i]),
                   MODE5_SIZE(BRICK_W, BRICK_H + 2 * BREAK_OVER));
        sprite_move(brick_sprite(i), brick_x[i], brick_y[i] - BREAK_OVER);
        DEBUG_LOG("brick %u, %u left\n", i, bricks_left);
    }
    if (hits)
        sfx_play(SFX_BREAK, bricks_hit_left + BRICK_W / 2);
    return hits;
}

/* Whether any brick overlaps the box, without breaking it. */
uint8_t bricks_touch(int16_t x, int16_t y, uint8_t w, uint8_t h)
{
    uint8_t i;

    for (i = 0; i < brick_count; i++)
        if (brick_overlaps(i, x, y, w, h))
            return 1;
    return 0;
}

/* Steps the breaks: each frame in turn, then the nugget, from the middle
   of the brick. */
void bricks_step(void)
{
    uint8_t i;

    for (i = 0; i < brick_count; i++)
    {
        if (!brick_breaking[i])
            continue;
        if (++brick_breaking[i] == BREAK_STEPS + 1)
            xram0_poke16(brick_sprite(i) + offsetof(mode5_csprite_t, xram_sprite_ptr), BREAK_IMAGE(1));
        else if (brick_breaking[i] == BREAK_FRAMES * BREAK_STEPS + 1)
        {
            brick_breaking[i] = 0;
            sprite_hide(brick_sprite(i));
            nuggets_spawn(brick_x[i] + BRICK_W / 2 - 4, brick_y[i], brick_color[i]);
        }
    }
}

/* How many bricks of a color are still breaking, their nuggets to come. */
uint8_t bricks_pending(uint8_t color)
{
    uint8_t i, n = 0;

    for (i = 0; i < brick_count; i++)
        if (brick_breaking[i] && brick_color[i] == color)
            n++;
    return n;
}
