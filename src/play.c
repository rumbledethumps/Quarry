#include "play.h"
#include "bricks.h"
#include "debug.h"
#include "energy.h"
#include "input.h"
#include "nuggets.h"
#include "paddle.h"
#include "tuning.h"
#include "video.h"
#include "xram.h"

/* The ball is the size of its image. */
#define BALL_SIZE 8

/* The right panel is a framed box from the wall to the edge of the
   screen, with the energy bar at the top and the ball icons under it, in
   rows as wide as the bar. */
#define PANEL_TOP_ROW 1
#define PANEL_BOTTOM_ROW 28
#define PANEL_LABEL_ROW 2
#define ENERGY_Y 26
#define ICONS_COLS 3
#define ICONS_PITCH 10
#define ICONS_Y 92

#define BALL_DOCKED 0 /* on the paddle, waiting for launch */
#define BALL_FLYING 1
#define BALL_GONE 2

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

int16_t play_left;
int16_t play_right;

static uint8_t balls; /* balls not yet launched */
static uint8_t ball_state;
static int32_t ball_x; /* the top left of the ball */
static int32_t ball_y;
static int16_t ball_vx;
static int16_t ball_vy;

static uint8_t icons_shown;
static int16_t icons_x;

void play_init(void)
{
    uint8_t i;

    for (i = 0; i < BALL_ICONS_MAX; i++)
        sprite_set(ICON_SPRITE(i), XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
    sprite_set(XRAM_BALL_SPRITE, XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
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

/* The ball sits on the middle of the paddle, and goes where it goes, even
   when it falls and tilts. */
static void ball_dock(void)
{
    ball_state = BALL_DOCKED;
    ball_x = paddle_x + FIX(paddle_width / 2 - BALL_SIZE / 2);
    ball_y = paddle_y + FIX(paddle_width / 16 * paddle_tilt() - BALL_SIZE);
}

void play_start(void)
{
    int16_t panel_left = play_right + WALL_SIZE;
    int16_t center = (panel_left + SCREEN_W) / 2;
    int16_t bar_left = center - (ICONS_COLS * ICONS_PITCH - (ICONS_PITCH - 8)) / 2;

    video_box(panel_left / 8, PANEL_TOP_ROW, SCREEN_W / 8 - 1, PANEL_BOTTOM_ROW, BOX_COLOR);
    video_text(panel_left / 8 + 1, PANEL_LABEL_ROW, "ENERGY", TEXT_COLOR, BOX_FILL);
    energy_start(bar_left, ENERGY_Y);
    balls = TUNE_BALLS;
    icons_x = bar_left;
    icons_shown = 0;
    icons_draw();
    paddle_start();
    ball_dock();
}

/* Launches the ball steeply, the way the paddle last moved. The first
   launch of a stage starts the energy draining. */
static void ball_launch(void)
{
    balls--;
    icons_draw();
    ball_state = BALL_FLYING;
    ball_vx = zone_vx[paddle_left ? 2 : 3];
    ball_vy = zone_vy[3];
    energy_draining = 1;
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
    else if (ball_vy > 0 && paddle_state <= PADDLE_SPUTTER &&
             old <= paddle_y - FIX(BALL_SIZE) && ball_y > paddle_y - FIX(BALL_SIZE) &&
             ball_x + FIX(BALL_SIZE) > paddle_x && ball_x < paddle_x + FIX(paddle_width))
    {
        ball_y = (paddle_y - FIX(BALL_SIZE)) * 2 - ball_y;
        paddle_bounce(PX(ball_x));
    }
    else
        old = ball_y;
    if (old != ball_y &&
        bricks_touch(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
        ball_y = old;
}

/* When the energy runs out, the paddle sputters and falls, and the stage
   ends when it is gone. A ball in flight plays on until then, but a lost
   one is not replaced. */
uint8_t play_step(void)
{
    energy_step();
    if (!energy && paddle_state == PADDLE_HOVER)
        paddle_give_up();
    paddle_step(1);
    nuggets_step();
    bricks_step();
    switch (ball_state)
    {
    case BALL_DOCKED:
        ball_dock();
        if (paddle_state == PADDLE_HOVER && (input_pressed & INPUT_LAUNCH))
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
            if (paddle_state != PADDLE_HOVER)
                ball_state = BALL_GONE;
            else if (balls)
                ball_dock();
            else
            {
                ball_state = BALL_GONE;
                DEBUG_LOG("out of balls\n");
                return PLAY_OUT;
            }
        }
        break;
    }
    if (paddle_state == PADDLE_GONE)
    {
        ball_state = BALL_GONE;
        return PLAY_NO_ENERGY;
    }
    return PLAY_ON;
}

/* After the stage ends, the flames still burn, a falling paddle still
   falls off the screen, and the last nuggets still fly to the panel. The
   nuggets step before the bricks, so a new one stays where its brick was
   until the next step. */
void play_idle(void)
{
    paddle_step(0);
    nuggets_step();
    bricks_step();
}

/* Finishes every break and lands every nugget at once, so the counts are
   whole. */
void play_finish(void)
{
    bricks_finish();
    nuggets_land();
}

/* The nuggets of a color still to land: breaking, or in flight. */
uint8_t play_pending(uint8_t color)
{
    return bricks_pending(color) + nuggets_flying(color);
}

/* The ball is drawn first, as early in the vertical blank as it can be. */
void play_draw(void)
{
    if (ball_state == BALL_GONE || PX(ball_y) >= SCREEN_H)
        sprite_hide(XRAM_BALL_SPRITE);
    else
        sprite_move(XRAM_BALL_SPRITE, PX(ball_x), PX(ball_y));
    paddle_draw();
    nuggets_draw();
}
