#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "play.h"
#include "sfx.h"
#include "tuning.h"
#include "video.h"
#include "xram.h"
#include <fcntl.h>
#include <rp6502.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define CRACK_SPRITE(i) (XRAM_CRACK_SPRITES + (i) * sizeof(mode5_csprite_t))
#define CHUNK_SPRITE(i) (XRAM_CHUNK_SPRITES + (i) * sizeof(mode5_csprite_t))
#define CRACK_IMAGE(set, state) (XRAM_CRACK_IMAGES + ((set) * CRACK_STATES + (state)) * sizeof(crack_image_t))
#define CHUNK_IMAGE(i) (XRAM_CHUNK_IMAGES + (i) * sizeof(chunk_image_t))
#define CRACK_PALETTE(color) (XRAM_PALETTE_BRICK(color) + BRICK_CRACK_COLORS * sizeof(uint16_t))
#define NUGGET_LEFT (BRICK_W / 2 - 4) /* its nugget's left edge, from the brick's: 8 wide in the middle */

/* The cracks over a brick are as many pieces as fit across it, set at
   random in the room left over. */
#define CRACK_PIECES (BRICK_W / CRACK_W)
#define CRACK_ROOM (BRICK_W - CRACK_PIECES * CRACK_W)
#define CRACK_FLIPS (MODE5_HFLIP | MODE5_VFLIP)

/* A brick breaks into CHUNKS_PER_BREAK chunks across it, which fly up and
   out, and fall, for CHUNK_STEPS steps, turning over every CHUNK_TURN.
   Their places and speeds are in 1/CHUNK_SUB px. */
#define CHUNKS_PER_BREAK 4
#define CHUNK_STEPS 36
#define CHUNK_TURN 6
#define CHUNK_GRAVITY 2
#define CHUNK_SUB 16

_Static_assert(BRICKS_MAX * CRACK_PIECES <= CRACKS_MAX, "Every brick needs its cracks.");
_Static_assert(CHUNKS_MAX % CHUNKS_PER_BREAK == 0, "A break takes its chunks together.");

/* A level, as levels/levels.py lays it out and ROM:levels holds them, one
   after another: its walls, the inner faces of its posts, and its bricks,
   each its top left and its color, all on the screen. */
typedef struct
{
    int16_t x;
    uint8_t y;
    uint8_t color; /* BRICK_GRAY and on */
} level_brick_t;

typedef struct
{
    int16_t left, right;
    uint8_t count;
    uint8_t unused;
    level_brick_t bricks[BRICKS_MAX];
} level_t;

#define LEVEL_BYTES sizeof(level_t) /* for tests/assets.py */

/* The hits that break a brick of each color. */
static const uint8_t brick_hits[BRICK_COLORS] = TUNE_BRICK_HITS;

uint8_t bricks_left;
int16_t bricks_hit_left;
int16_t bricks_hit_right;
int16_t bricks_hit_top;
int16_t bricks_hit_bottom;

/* Bricks are sprites, so each one keeps its own position. */
static level_t layout; /* the level's */
static uint8_t brick_count;
static int16_t brick_x[BRICKS_MAX];
static int16_t brick_y[BRICKS_MAX];
static uint8_t brick_alive[BRICKS_MAX];
static uint8_t brick_color[BRICKS_MAX];
static uint8_t brick_damage[BRICKS_MAX]; /* hits taken */

/* Each piece of cracks, its set and its flips, and each brick's, where its
   cracks start across it. They stay the same while the screen does. */
static uint8_t crack_look[CRACKS_MAX];
static uint8_t crack_left[BRICKS_MAX];

/* A chunk in flight, while steps is above 0. */
typedef struct
{
    int16_t x, y;
    int8_t vx, vy;
    uint8_t steps;
    uint8_t turn; /* its flips */
} chunk_t;

static chunk_t chunks[CHUNKS_MAX];
static uint8_t chunk_next; /* the free one, or the oldest */

static unsigned brick_sprite(uint8_t i)
{
    return XRAM_BRICKS + i * sizeof(mode5_csprite_t);
}

/* Reads a level, from 1, and sets its playfield, before the frame goes up
   around it. */
void bricks_layout(uint8_t level)
{
    int fd = open("ROM:levels", O_RDONLY);

    if (fd < 0)
        DEBUG_LOG("no levels\n");
    else
    {
        lseek(fd, (long)(level - 1) * sizeof layout, SEEK_SET);
        read(fd, &layout, sizeof layout);
        close(fd);
    }
    play_left = layout.left;
    play_right = layout.right;
}

/* New cracks for every brick, picked at random as the screen opens: each
   piece's set and flips, and where across its brick they start. */
void bricks_shuffle(void)
{
    uint8_t i;

    for (i = 0; i < CRACKS_MAX; i++)
    {
        unsigned r = rand();
        crack_look[i] = (r % CRACK_SETS) | (r & CRACK_FLIPS);
        if (i < BRICKS_MAX)
            crack_left[i] = (r >> 8) % (CRACK_ROOM + 1);
    }
}

/* The chunks in flight are gone at once. */
void bricks_finish(void)
{
    uint8_t i;

    for (i = 0; i < CHUNKS_MAX; i++)
        if (chunks[i].steps)
        {
            chunks[i].steps = 0;
            sprite_hide(CHUNK_SPRITE(i));
        }
}

void bricks_start(void)
{
    uint8_t i;

    bricks_finish();
    bricks_left = 0;
    brick_count = layout.count;
    for (i = 0; i < brick_count; i++)
    {
        brick_x[i] = layout.bricks[i].x;
        brick_y[i] = layout.bricks[i].y;
        brick_alive[i] = 1;
        brick_color[i] = layout.bricks[i].color;
        brick_damage[i] = 0;
        sprite_set(brick_sprite(i), XRAM_BRICK_IMAGE, XRAM_PALETTE_BRICK(brick_color[i]),
                   MODE5_SIZE(BRICK_W, BRICK_H));
        sprite_mode(brick_sprite(i), MODE5_2BPP);
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

/* A brick's cracks, for the hits it has taken: the quarters of it broken,
   to the nearest, 1 to CRACK_STATES. */
static void cracks_show(uint8_t i)
{
    uint8_t hits = brick_hits[brick_color[i]];
    uint8_t state = (brick_damage[i] * 8 / hits + 1) / 2;
    uint8_t k;

    if (!state)
        state = 1;
    else if (state > CRACK_STATES)
        state = CRACK_STATES;
    for (k = 0; k < CRACK_PIECES; k++)
    {
        uint8_t piece = i * CRACK_PIECES + k;
        unsigned sprite = CRACK_SPRITE(piece);

        sprite_set(sprite, CRACK_IMAGE(crack_look[piece] % CRACK_SETS, state - 1), CRACK_PALETTE(brick_color[i]),
                   MODE5_SIZE(CRACK_W, CRACK_H));
        sprite_mode(sprite, MODE5_2BPP | (crack_look[piece] & CRACK_FLIPS));
        sprite_move(sprite, brick_x[i] + crack_left[i] + k * CRACK_W, brick_y[i]);
    }
}

/* The chunks of a broken brick, taking the free sprites, or the oldest
   chunks' when every one flies. */
static void chunks_spawn(uint8_t i)
{
    uint8_t k;

    for (k = 0; k < CHUNKS_PER_BREAK; k++)
    {
        chunk_t *c = &chunks[chunk_next];
        unsigned sprite = CHUNK_SPRITE(chunk_next);
        uint8_t r = rand();

        c->x = (brick_x[i] + k * (BRICK_W - 8) / (CHUNKS_PER_BREAK - 1)) * CHUNK_SUB;
        c->y = brick_y[i] * CHUNK_SUB;
        c->vx = (int8_t)((2 * k - (CHUNKS_PER_BREAK - 1)) * 4 + (r & 7) - 3);
        c->vy = (int8_t)(-12 - (r >> 4));
        c->steps = CHUNK_STEPS;
        c->turn = r & CRACK_FLIPS;
        sprite_set(sprite, CHUNK_IMAGE(rand() % CHUNK_IMAGES), XRAM_PALETTE_BRICK(brick_color[i]),
                   MODE5_SIZE(8, 8));
        sprite_mode(sprite, MODE5_2BPP | c->turn);
        chunk_next = (chunk_next + 1) % CHUNKS_MAX;
    }
}

/* Hits every brick that overlaps the box, and returns how many it hit. A
   brick cracks more with each hit, and breaks with the last its color
   takes: it is gone at once, in chunks, with a crunch, and its nugget
   takes its place, with a chime. */
uint8_t bricks_hit(int16_t x, int16_t y, uint8_t w, uint8_t h)
{
    uint8_t i, k, hits = 0, broke = 0;

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
        hits++;
        if (++brick_damage[i] < brick_hits[brick_color[i]])
        {
            cracks_show(i);
            DEBUG_LOG("cracked %u, %u hits\n", i, brick_damage[i]);
            continue;
        }
        brick_alive[i] = 0;
        bricks_left--;
        broke = 1;
        sprite_hide(brick_sprite(i));
        for (k = 0; k < CRACK_PIECES; k++)
            sprite_hide(CRACK_SPRITE(i * CRACK_PIECES + k));
        chunks_spawn(i);
        nuggets_spawn(brick_x[i] + NUGGET_LEFT, brick_y[i], brick_color[i]);
        DEBUG_LOG("brick %u, %u left\n", i, bricks_left);
    }
    if (broke)
    {
        sfx_play(SFX_BREAK, bricks_hit_left + BRICK_W / 2);
        sfx_play(SFX_NUGGET, bricks_hit_left + BRICK_W / 2);
    }
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

/* The chunks fly, fall, bounce off the walls, and turn over, until their
   time is up. */
void bricks_step(void)
{
    uint8_t i;

    for (i = 0; i < CHUNKS_MAX; i++)
    {
        chunk_t *c = &chunks[i];
        if (!c->steps)
            continue;
        if (!--c->steps)
        {
            sprite_hide(CHUNK_SPRITE(i));
            continue;
        }
        c->x += c->vx;
        c->y += c->vy;
        c->vy += CHUNK_GRAVITY;
        if (c->x < play_left * CHUNK_SUB || c->x > (play_right - 8) * CHUNK_SUB)
        {
            c->x = c->x < play_left * CHUNK_SUB ? play_left * CHUNK_SUB : (play_right - 8) * CHUNK_SUB;
            c->vx = -c->vx / 2;
        }
        if (c->steps % CHUNK_TURN == 0)
        {
            /* Unflipped, then flipped across, then both ways, then up and
               down, by its flips. */
            static const uint8_t over[4] = {MODE5_HFLIP, MODE5_HFLIP | MODE5_VFLIP, 0, MODE5_VFLIP};
            c->turn = over[c->turn >> 4];
            sprite_mode(CHUNK_SPRITE(i), MODE5_2BPP | c->turn);
        }
    }
}

/* At the start of a frame: the chunks where they got to. */
void bricks_draw(void)
{
    uint8_t i;

    for (i = 0; i < CHUNKS_MAX; i++)
        if (chunks[i].steps)
            sprite_move(CHUNK_SPRITE(i), chunks[i].x / CHUNK_SUB, chunks[i].y / CHUNK_SUB);
}
