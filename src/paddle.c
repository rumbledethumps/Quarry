#include "paddle.h"
#include "debug.h"
#include "input.h"
#include "play.h"
#include "sfx.h"
#include "tuning.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"

#define PIECE_SPRITE(i) (XRAM_PADDLE_SPRITES + (i) * sizeof(mode5_csprite_t))
#define FLAME_SPRITE(i) (XRAM_FLAME_SPRITES + (i) * sizeof(mode5_csprite_t))
#define SMOKE_SPRITE(i) (XRAM_SMOKE_SPRITES + (i) * sizeof(mode5_csprite_t))
#define FLAME_IMAGE(i) (XRAM_FLAME_IMAGES + (i) * sizeof(piece_image_t))
#define SMOKE_IMAGE(i) (XRAM_SMOKE_IMAGES + (i) * sizeof(piece_image_t))

/* The flames burn through their frames, short, medium and long, a frame
   every FLAME_STEPS steps, the two out of step with each other. */
#define FLAME_STEPS 3
static const uint8_t flame_cycle[8] = {0, 1, 2, 2, 1, 2, 1, 1};

/* A sputtering flame shows its short frame on the steps with a bit set
   here, and nothing on the others. */
static const uint8_t sputter_pattern[8] = {0xB2, 0x4C, 0x91, 0x0A, 0x48, 0x02, 0x20, 0x01};

/* The puff of smoke shows each frame for SMOKE_STEPS steps, and rises a
   pixel every SMOKE_RISE steps. */
#define SMOKE_STEPS 10
#define SMOKE_RISE 4

/* A falling paddle tilts, the right end lower, a pixel more per piece
   every TILT_STEPS steps, up to TILT_MAX. */
#define TILT_STEPS 6
#define TILT_MAX 2

uint8_t paddle_state;
int32_t paddle_x;
int32_t paddle_y;
uint8_t paddle_width;
uint8_t paddle_left;

static uint16_t paddle_speed;
static uint8_t paddle_moved; /* the pieces need drawing */
static uint16_t state_steps; /* steps since paddle_state changed */
static int16_t fall_speed;   /* 1/256 px per step */
static int16_t smoke_x;      /* where the paddle gave up, for the smoke */
static int16_t smoke_y;

/* The paddle is a left end, middle pieces, and a right end, 8 px each.
   The end pieces have the nozzles, and a flame burns under each. Its
   width and speed come from the upgrades bought so far. */
void paddle_start(void)
{
    uint8_t i, pieces;

    paddle_state = PADDLE_HOVER;
    state_steps = 0;
    paddle_width = upgrades_width();
    paddle_speed = upgrades_speed();
    paddle_x = FIX((play_left + play_right - paddle_width) / 2);
    paddle_y = FIX(TUNE_PADDLE_Y);
    paddle_left = 0;
    pieces = paddle_width / 8;
    for (i = 0; i < PADDLE_PIECES_MAX; i++)
    {
        uint8_t piece = i == 0 ? PADDLE_LEFT : i == pieces - 1 ? PADDLE_RIGHT : PADDLE_MIDDLE;
        sprite_set(PIECE_SPRITE(i), XRAM_PADDLE_IMAGES + piece * sizeof(piece_image_t),
                   XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
    }
    for (i = 0; i < 2; i++)
    {
        sprite_set(FLAME_SPRITE(i), FLAME_IMAGE(0), XRAM_PALETTE_FX, MODE5_SIZE(8, 8));
        sprite_set(SMOKE_SPRITE(i), SMOKE_IMAGE(0), XRAM_PALETTE_FX, MODE5_SIZE(8, 8));
    }
    paddle_moved = 1;
}

/* Out of energy. The player loses control, and the flames sputter. */
void paddle_give_up(void)
{
    paddle_state = PADDLE_SPUTTER;
    state_steps = 0;
    sfx_play(SFX_SPUTTER, PX(paddle_x) + paddle_width / 2);
    DEBUG_LOG("out of energy\n");
}

static void hover_step(void)
{
    int32_t x = paddle_x;

    switch (input_held & (INPUT_LEFT | INPUT_RIGHT))
    {
    case INPUT_LEFT:
        x -= paddle_speed;
        paddle_left = 1;
        break;
    case INPUT_RIGHT:
        x += paddle_speed;
        paddle_left = 0;
        break;
    }
    if (x < FIX(play_left))
        x = FIX(play_left);
    if (x > FIX(play_right - paddle_width))
        x = FIX(play_right - paddle_width);
    if (x != paddle_x)
    {
        paddle_x = x;
        paddle_moved = 1;
    }
}

/* With controls 0, as after the stage ends, the paddle still burns its
   flames, and finishes falling if it was. */
void paddle_step(uint8_t controls)
{
    state_steps++;
    switch (paddle_state)
    {
    case PADDLE_HOVER:
        if (controls)
            hover_step();
        break;
    case PADDLE_SPUTTER:
        if (state_steps >= TUNE_SPUTTER_STEPS)
        {
            paddle_state = PADDLE_FALLING;
            state_steps = 0;
            fall_speed = 0;
            smoke_x = PX(paddle_x);
            smoke_y = PX(paddle_y) + 6;
            sfx_play(SFX_FALL, smoke_x + paddle_width / 2);
            DEBUG_LOG("paddle falls\n");
        }
        break;
    case PADDLE_FALLING:
        fall_speed += TUNE_FALL_GRAVITY;
        paddle_y += fall_speed;
        paddle_moved = 1;
        if (PX(paddle_y) >= SCREEN_H)
        {
            paddle_state = PADDLE_GONE;
            DEBUG_LOG("paddle gone\n");
        }
        break;
    }
}

static void flame_draw(uint8_t i, int16_t x, int16_t y)
{
    uint8_t frame;

    if (paddle_state == PADDLE_HOVER)
        frame = flame_cycle[(state_steps / FLAME_STEPS + i * 3) & 7];
    else if (paddle_state == PADDLE_SPUTTER &&
             (sputter_pattern[(state_steps / 8 + i * 3) & 7] & (1 << (state_steps & 7))))
        frame = 0;
    else
    {
        sprite_hide(FLAME_SPRITE(i));
        return;
    }
    sprite_move(FLAME_SPRITE(i), x, y);
    xram0_poke16(FLAME_SPRITE(i) + offsetof(mode5_csprite_t, xram_sprite_ptr), FLAME_IMAGE(frame));
}

static void smoke_draw(void)
{
    uint8_t i, frame = state_steps / SMOKE_STEPS;

    for (i = 0; i < 2; i++)
    {
        if (paddle_state != PADDLE_FALLING || frame >= SMOKE_FRAMES)
        {
            sprite_hide(SMOKE_SPRITE(i));
            continue;
        }
        sprite_move(SMOKE_SPRITE(i), smoke_x + i * (paddle_width - 8),
                    smoke_y - state_steps / SMOKE_RISE);
        xram0_poke16(SMOKE_SPRITE(i) + offsetof(mode5_csprite_t, xram_sprite_ptr), SMOKE_IMAGE(frame));
    }
}

/* How much lower each piece of a falling paddle is than the one before. */
uint8_t paddle_tilt(void)
{
    uint8_t tilt;

    if (paddle_state != PADDLE_FALLING)
        return 0;
    tilt = state_steps / TILT_STEPS;
    return tilt > TILT_MAX ? TILT_MAX : tilt;
}

void paddle_draw(void)
{
    uint8_t i, pieces = paddle_width / 8;
    int16_t x = PX(paddle_x);
    int16_t y = PX(paddle_y);

    if (paddle_moved)
    {
        uint8_t tilt = paddle_tilt();
        for (i = 0; i < PADDLE_PIECES_MAX; i++)
            if (i < pieces && paddle_state != PADDLE_GONE)
                sprite_move(PIECE_SPRITE(i), x + i * 8, y + i * tilt);
            else
                sprite_hide(PIECE_SPRITE(i));
        paddle_moved = 0;
    }
    flame_draw(0, x, y + 8);
    flame_draw(1, x + paddle_width - 8, y + 8);
    smoke_draw();
}
