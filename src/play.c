#include "play.h"
#include "bricks.h"
#include "debug.h"
#include "input.h"
#include "tuning.h"
#include "video.h"
#include "xram.h"

/* Positions and speeds are in 1/256 pixel. */
#define FIX(px) ((int32_t)(px) << 8)
#define PX(fix) ((int16_t)((fix) >> 8))

/* The ball is the size of its image. */
#define BALL_SIZE 8

/* The right panel is a framed box. The ball icons in it sit under the
   energy bar to come. */
#define PANEL_TOP_ROW 1
#define PANEL_BOTTOM_ROW 28
#define ICONS_COLS 3
#define ICONS_PITCH 10
#define ICONS_Y 136

#define BALL_DOCKED 0 /* on the paddle, waiting for launch */
#define BALL_FLYING 1
#define BALL_GONE 2

#define BALL_SPRITE XRAM_ACTORS
#define PADDLE_SPRITE(i) (XRAM_ACTORS + (1 + (i)) * sizeof(mode5_csprite_t))
#define ICON_SPRITE(i) (XRAM_BALL_ICONS + (i) * sizeof(mode5_csprite_t))

#define ZONE_SPEED(unit) ((int16_t)((int32_t)TUNE_BALL_SPEED * (unit) / 256))

/* The ball's velocity off each zone of the paddle, left to right. */
static const int16_t zone_vx[6] = {
    -ZONE_SPEED(TUNE_SHALLOW_X), -ZONE_SPEED(TUNE_MIDDLE_X), -ZONE_SPEED(TUNE_STEEP_X),
    ZONE_SPEED(TUNE_STEEP_X), ZONE_SPEED(TUNE_MIDDLE_X), ZONE_SPEED(TUNE_SHALLOW_X),
};
static const int16_t zone_vy[6] = {
    -ZONE_SPEED(TUNE_SHALLOW_Y), -ZONE_SPEED(TUNE_MIDDLE_Y), -ZONE_SPEED(TUNE_STEEP_Y),
    -ZONE_SPEED(TUNE_STEEP_Y), -ZONE_SPEED(TUNE_MIDDLE_Y), -ZONE_SPEED(TUNE_SHALLOW_Y),
};

_Static_assert(TUNE_PADDLE_WIDTH % 8 == 0 && TUNE_PADDLE_WIDTH >= 16 &&
                   TUNE_PADDLE_WIDTH <= PADDLE_PIECES_MAX * 8,
               "TUNE_PADDLE_WIDTH must be a multiple of 8 from 16 to 64.");

int16_t play_left;
int16_t play_right;

static uint8_t balls; /* balls not yet launched */
static uint8_t ball_state;
static int32_t ball_x; /* the top left of the ball */
static int32_t ball_y;
static int16_t ball_vx;
static int16_t ball_vy;

static int32_t paddle_x; /* the left edge of the paddle */
static uint8_t paddle_width;
static uint8_t paddle_moved;
static uint8_t paddle_left; /* the paddle last moved left */

static uint8_t icons_shown;
static int16_t icons_x;

void play_init(void)
{
    uint8_t i;

    for (i = 0; i < BALL_ICONS_MAX; i++)
        sprite_set(ICON_SPRITE(i), XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
    sprite_set(BALL_SPRITE, XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
}

/* Shows one icon for each ball not yet launched. */
static void icons_draw(void)
{
    while (icons_shown < balls && icons_shown < BALL_ICONS_MAX)
    {
        sprite_move(ICON_SPRITE(icons_shown),
                    icons_x + icons_shown % ICONS_COLS * ICONS_PITCH,
                    ICONS_Y + icons_shown / ICONS_COLS * ICONS_PITCH);
        icons_shown++;
    }
    while (icons_shown > balls)
        sprite_hide(ICON_SPRITE(--icons_shown));
}

/* The paddle is a left end, middle pieces, and a right end, 8 px each. */
static void paddle_build(void)
{
    uint8_t i, pieces = paddle_width / 8;

    for (i = 0; i < PADDLE_PIECES_MAX; i++)
    {
        uint8_t piece = i == 0 ? PADDLE_LEFT : i == pieces - 1 ? PADDLE_RIGHT : PADDLE_MIDDLE;
        sprite_set(PADDLE_SPRITE(i), XRAM_PADDLE_IMAGES + piece * sizeof(piece_image_t),
                   XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
    }
    paddle_moved = 1;
}

static void ball_dock(void)
{
    ball_state = BALL_DOCKED;
    ball_x = paddle_x + FIX(paddle_width / 2 - BALL_SIZE / 2);
    ball_y = FIX(TUNE_PADDLE_Y - BALL_SIZE);
}

void play_start(void)
{
    int16_t panel_left = play_right + WALL_SIZE;

    video_box(panel_left / 8 + 1, PANEL_TOP_ROW, SCREEN_W / 8 - 2, PANEL_BOTTOM_ROW);
    balls = TUNE_BALLS;
    icons_x = (panel_left + SCREEN_W) / 2 - (ICONS_COLS * ICONS_PITCH - (ICONS_PITCH - 8)) / 2;
    icons_shown = 0;
    icons_draw();

    paddle_width = TUNE_PADDLE_WIDTH;
    paddle_x = FIX((play_left + play_right - paddle_width) / 2);
    paddle_left = 0;
    paddle_build();
    ball_dock();
}

static void paddle_step(void)
{
    int32_t x = paddle_x;

    switch (input_held & (INPUT_LEFT | INPUT_RIGHT))
    {
    case INPUT_LEFT:
        x -= TUNE_PADDLE_SPEED;
        paddle_left = 1;
        break;
    case INPUT_RIGHT:
        x += TUNE_PADDLE_SPEED;
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

/* Launches the ball steeply, the way the paddle last moved. */
static void ball_launch(void)
{
    balls--;
    icons_draw();
    ball_state = BALL_FLYING;
    ball_vx = zone_vx[paddle_left ? 2 : 3];
    ball_vy = zone_vy[3];
    DEBUG_LOG("launch, %u balls left\n", balls);
}

/* x is the ball's left edge, which overlaps the paddle. */
static void paddle_bounce(int16_t x)
{
    int16_t across = x + BALL_SIZE - PX(paddle_x);
    uint8_t zone = across * 6 / (paddle_width + BALL_SIZE);

    if (zone > 5)
        zone = 5;
    ball_vx = zone_vx[zone];
    ball_vy = zone_vy[zone];
    DEBUG_LOG("paddle zone %u\n", zone);
}

/* The ball's box in whole pixels, one wider or taller when it sits between
   pixels, so a test against it is exact. */
static uint8_t ball_extent(int32_t fix)
{
    return BALL_SIZE + ((uint8_t)fix != 0);
}

/* Moves the ball across, then down. On each axis, a ball that goes into
   something is reflected back out of it, as far as it went in. If that
   puts it in another brick, it stays where it started on that axis
   instead, so it never ends a step inside a brick. */
static void ball_step(void)
{
    int32_t old;

    old = ball_x;
    ball_x += ball_vx;
    if (ball_x < FIX(play_left))
    {
        ball_x = FIX(play_left) * 2 - ball_x;
        ball_vx = -ball_vx;
    }
    else if (ball_x > FIX(play_right - BALL_SIZE))
    {
        ball_x = FIX(play_right - BALL_SIZE) * 2 - ball_x;
        ball_vx = -ball_vx;
    }
    else if (bricks_hit(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
    {
        if (ball_vx > 0)
            ball_x = FIX(bricks_hit_left - BALL_SIZE) * 2 - ball_x;
        else
            ball_x = FIX(bricks_hit_right) * 2 - ball_x;
        ball_vx = -ball_vx;
    }
    else
        old = ball_x;
    if (old != ball_x &&
        bricks_touch(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
        ball_x = old;

    old = ball_y;
    ball_y += ball_vy;
    if (ball_y < FIX(WALL_SIZE))
    {
        ball_y = FIX(WALL_SIZE) * 2 - ball_y;
        ball_vy = -ball_vy;
    }
    else if (bricks_hit(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
    {
        if (ball_vy > 0)
            ball_y = FIX(bricks_hit_top - BALL_SIZE) * 2 - ball_y;
        else
            ball_y = FIX(bricks_hit_bottom) * 2 - ball_y;
        ball_vy = -ball_vy;
    }
    else if (ball_vy > 0 &&
             old <= FIX(TUNE_PADDLE_Y - BALL_SIZE) && ball_y > FIX(TUNE_PADDLE_Y - BALL_SIZE) &&
             ball_x + FIX(BALL_SIZE) > paddle_x && ball_x < paddle_x + FIX(paddle_width))
    {
        ball_y = FIX(TUNE_PADDLE_Y - BALL_SIZE) * 2 - ball_y;
        paddle_bounce(PX(ball_x));
    }
    else
        old = ball_y;
    if (old != ball_y &&
        bricks_touch(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
        ball_y = old;
}

uint8_t play_step(void)
{
    paddle_step();
    switch (ball_state)
    {
    case BALL_DOCKED:
        ball_dock();
        if (input_pressed & INPUT_LAUNCH)
            ball_launch();
        break;
    case BALL_FLYING:
        ball_step();
        if (!bricks_left)
        {
            ball_state = BALL_GONE;
            DEBUG_LOG("stage cleared\n");
            return PLAY_CLEARED;
        }
        if (PX(ball_y) >= SCREEN_H)
        {
            DEBUG_LOG("ball lost\n");
            if (!balls)
            {
                ball_state = BALL_GONE;
                DEBUG_LOG("out of balls\n");
                return PLAY_OUT;
            }
            ball_dock();
        }
        break;
    }
    return PLAY_ON;
}

void play_draw(void)
{
    if (paddle_moved)
    {
        uint8_t i, pieces = paddle_width / 8;
        int16_t x = PX(paddle_x);
        for (i = 0; i < PADDLE_PIECES_MAX; i++)
            if (i < pieces)
                sprite_move(PADDLE_SPRITE(i), x + i * 8, TUNE_PADDLE_Y);
            else
                sprite_hide(PADDLE_SPRITE(i));
        paddle_moved = 0;
    }
    if (ball_state == BALL_GONE)
        sprite_hide(BALL_SPRITE);
    else
        sprite_move(BALL_SPRITE, PX(ball_x), PX(ball_y));
}
