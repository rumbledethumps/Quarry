#include "play.h"
#include "bricks.h"
#include "debug.h"
#include "energy.h"
#include "input.h"
#include "nuggets.h"
#include "paddle.h"
#include "sfx.h"
#include "talk.h"
#include "tuning.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"

/* The ball is the size of its image. */
#define BALL_SIZE 8

/* The count of balls is at the bottom left, the ball, as big as the
   digits, and then its digits, and the energy gauge down the right edge,
   over the right curtain, from the top of the screen to its foot.
   levels/levels.py keeps every level's right post clear of it. */
#define BALLS_X 4
#define BALLS_Y 227
#define BALLS_MAX 99
#define GAUGE_X 300
#define GAUGE_Y 0

#define BALL_DOCKED 0 /* on the paddle, waiting for launch */
#define BALL_FLYING 1
#define BALL_GONE 2   /* none in play */
#define BALL_COMING 3 /* from the count to the paddle */

/* As a level starts, it builds up over TUNE_BUILD_STEPS: the sled rises
   into place, the bricks are laid one by one, and the gauge fills, from
   empty at the rate that fills it in that time, so a gauge that holds
   some already rises, with its bubbles, only once the fill reaches it. A
   ball leaves the count so as to land on the sled as it ends. Once the
   ball is on the sled and the time is up, it can be launched, and the
   meter comes up. It starts when the level does, or as the dwarf with
   something to say goes. */
_Static_assert(TUNE_BUILD_STEPS <= 255, "TUNE_BUILD_STEPS is a byte.");
_Static_assert(TUNE_RISE_STEPS <= TUNE_BUILD_STEPS, "The sled is in place before the level is built.");

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

static uint8_t balls; /* balls in the count, not yet in play */
static uint8_t ball_state;
static uint8_t building;    /* the level is building up */
static uint8_t build_steps; /* of it so far */
static int32_t ball_x; /* the top left of the ball */
static int32_t ball_y;
static int16_t ball_vx;
static int16_t ball_vy;

void play_init(void)
{
    sprite_set(XRAM_BALL_SPRITE, XRAM_BALL_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(8, 8));
    sprite_set(XRAM_BALL_ICON, XRAM_BALL_ICON_IMAGE, XRAM_PALETTE_MAIN, MODE5_SIZE(ICON_SIZE, ICON_SIZE));
}

/* The count of balls not yet launched. */
static void balls_draw(void)
{
    video_count(XRAM_BALL_DIGITS, BALL_DIGITS, BALLS_X + 12, BALLS_Y - 1, balls);
}

/* The ball's place on the paddle: on its middle, and where it goes, even
   when it falls and tilts. */
static int32_t dock_x(void)
{
    return paddle_x + FIX(paddle_width / 2 - BALL_SIZE / 2);
}

static int32_t dock_y(void)
{
    return paddle_y + FIX(paddle_width / 2 * paddle_tilt() / 8 - BALL_SIZE);
}

static void ball_dock(void)
{
    ball_state = BALL_DOCKED;
    ball_x = dock_x();
    ball_y = dock_y();
}

/* The steps a ball from the count takes to the paddle, as it is now. */
static uint8_t come_steps(void)
{
    int32_t dx = dock_x() - FIX(BALLS_X + ICON_ROUND / 2 - BALL_SIZE / 2);
    int32_t dy = dock_y() - FIX(BALLS_Y - 1 + ICON_ROUND / 2 - BALL_SIZE / 2);

    return ((dx > -dy ? dx : -dy) + TUNE_BALL_COME - 1) / TUNE_BALL_COME;
}

/* The next ball leaves the count, from the middle of its icon. */
static void ball_come(void)
{
    balls--;
    balls_draw();
    ball_state = BALL_COMING;
    ball_x = FIX(BALLS_X + ICON_ROUND / 2 - BALL_SIZE / 2);
    ball_y = FIX(BALLS_Y - 1 + ICON_ROUND / 2 - BALL_SIZE / 2);
    DEBUG_LOG("ball comes, %u left\n", balls);
}

/* A coming ball flies TUNE_BALL_COME a step to its place on the paddle,
   wherever the paddle goes, even as it falls, and lands there. */
static void ball_come_step(void)
{
    int32_t dx = dock_x() - ball_x, dy = dock_y() - ball_y;
    int32_t d = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;

    if (ady > d)
        d = ady;
    if (d <= TUNE_BALL_COME)
    {
        ball_dock();
        DEBUG_LOG("ball landed\n");
        return;
    }
    ball_x += dx * TUNE_BALL_COME / d;
    ball_y += dy * TUNE_BALL_COME / d;
}

/* The level, ready to build up: no ball in play, the gauge, the count of
   balls, and the paddle. On a new screen, the gauge is empty and the
   paddle below the screen. On the level played again, the ball in play
   is gone, and the gauge and a hovering paddle stay as they were. */
void play_start(uint8_t again)
{
    energy_start(GAUGE_X, GAUGE_Y, again);
    balls = upgrades_balls();
    sprite_move(XRAM_BALL_ICON, BALLS_X, BALLS_Y - 1);
    balls_draw();
    paddle_start(again);
    ball_state = BALL_GONE;
    building = 1;
    build_steps = 0;
}

/* A step of the build-up: the paddle's rise, the bricks due, and the
   fill. */
static void build_step(void)
{
    if (build_steps == TUNE_BUILD_STEPS)
        return;
    build_steps++;
    paddle_rise(build_steps);
    bricks_lay(build_steps);
    energy_fill((uint32_t)build_steps * TUNE_ENERGY / TUNE_BUILD_STEPS);
}

/* Launches the ball steeply, the way the paddle last moved. The first
   launch of a level starts the energy draining. */
static void ball_launch(void)
{
    ball_state = BALL_FLYING;
    ball_vx = zone_vx[paddle_left ? 2 : 3];
    ball_vy = zone_vy[3];
    energy_draining = 1;
    DEBUG_LOG("launch, %u balls left\n", balls);
}

/* x is the ball's left edge, which overlaps the paddle. Each bounce sends a
   bubble up the fuel gauge. */
static void paddle_bounce(int16_t x)
{
    int16_t across = x + BALL_SIZE - PX(paddle_x);
    uint8_t zone = across * 6 / (paddle_width + BALL_SIZE);

    if (zone > 5)
        zone = 5;
    ball_vx = zone_vx[zone];
    ball_vy = zone_vy[zone];
    sfx_play(SFX_PADDLE, x + BALL_SIZE / 2);
    energy_bubble();
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
        sfx_play(SFX_WALL, play_left);
    }
    else if (ball_x > FIX(play_right - BALL_SIZE))
    {
        ball_x = FIX(play_right - BALL_SIZE) * 2 - ball_x;
        ball_vx = -ball_vx;
        sfx_play(SFX_WALL, play_right);
    }
    else if (bricks_hit(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
    {
        if (ball_vx > 0)
            ball_x = FIX(bricks_hit_left - BALL_SIZE) * 2 - ball_x;
        else
            ball_x = FIX(bricks_hit_right) * 2 - ball_x;
        ball_vx = -ball_vx;
        sfx_play(SFX_BRICK, PX(ball_x));
    }
    else
        old = ball_x;
    if (old != ball_x &&
        bricks_touch(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
        ball_x = old;

    old = ball_y;
    ball_y += ball_vy;
    if (ball_y < FIX(BEAM_H))
    {
        ball_y = FIX(BEAM_H) * 2 - ball_y;
        ball_vy = -ball_vy;
        sfx_play(SFX_WALL, PX(ball_x));
    }
    else if (bricks_hit(PX(ball_x), PX(ball_y), ball_extent(ball_x), ball_extent(ball_y)))
    {
        if (ball_vy > 0)
            ball_y = FIX(bricks_hit_top - BALL_SIZE) * 2 - ball_y;
        else
            ball_y = FIX(bricks_hit_bottom) * 2 - ball_y;
        ball_vy = -ball_vy;
        sfx_play(SFX_BRICK, PX(ball_x));
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

#ifndef NDEBUG
/* The cheats of a debug build: Shift and right or left adds a ball to the
   count or takes one away, and Shift and up or down adds a twelfth of the
   energy or takes one away. */
static void cheats_step(void)
{
    if ((shift_pressed & SHIFT_RIGHT) && balls < BALLS_MAX)
        balls++;
    if ((shift_pressed & SHIFT_LEFT) && balls)
        balls--;
    if (shift_pressed & (SHIFT_RIGHT | SHIFT_LEFT))
    {
        balls_draw();
        DEBUG_LOG("cheat: %u balls\n", balls);
    }
    if (shift_pressed & SHIFT_UP)
        energy_cheat(1);
    if (shift_pressed & SHIFT_DOWN)
        energy_cheat(-1);
}
#endif

/* When the energy runs out, the paddle sputters and falls, and the level
   ends once it is gone and no ball is in play. A ball in flight plays on,
   breaking bricks, until it falls off the bottom of the screen, and a lost
   one is not replaced, nor makes a sound, as the sled's fall was the
   sound of it. A ball on the paddle rides it down, and falls on off the
   screen once it is gone, and a ball coming to it chases it down. A lost
   ball is replaced by the next from the count. */
uint8_t play_step(void)
{
#ifndef NDEBUG
    cheats_step();
#endif
    if (building)
    {
        build_step();
        if (ball_state == BALL_DOCKED && build_steps == TUNE_BUILD_STEPS)
        {
            building = 0;
            energy_ready();
            DEBUG_LOG("ready\n");
        }
    }
    energy_step();
    if (!energy && paddle_state == PADDLE_HOVER)
        paddle_give_up();
    paddle_step(1);
    nuggets_step();
    bricks_step();
    switch (ball_state)
    {
    case BALL_GONE:
        if (building && balls && build_steps + come_steps() >= TUNE_BUILD_STEPS)
            ball_come();
        break;
    case BALL_COMING:
        ball_come_step();
        break;
    case BALL_DOCKED:
        ball_dock();
        if (!building && paddle_state == PADDLE_HOVER && (input_pressed & INPUT_LAUNCH))
            ball_launch();
        break;
    case BALL_FLYING:
        ball_step();
        if (!bricks_left)
        {
            ball_state = BALL_GONE;
            paddle_leave();
            DEBUG_LOG("level cleared\n");
            return PLAY_CLEARED;
        }
        if (PX(ball_y) >= SCREEN_H)
        {
            DEBUG_LOG("ball lost\n");
            if (paddle_state != PADDLE_HOVER)
                ball_state = BALL_GONE; /* out of energy, and the sled's fall was its sound */
            else
            {
                sfx_play(SFX_LOST, PX(ball_x));
                if (balls)
                    ball_come();
                else
                {
                    ball_state = BALL_GONE;
                    paddle_leave();
                    DEBUG_LOG("out of balls\n");
                    return PLAY_OUT;
                }
            }
        }
        break;
    }
    if (paddle_state == PADDLE_GONE)
    {
        if (ball_state == BALL_DOCKED)
        {
            ball_state = BALL_FLYING;
            ball_vx = 0;
            ball_vy = TUNE_BALL_SPEED;
        }
        else if (ball_state == BALL_GONE)
            return PLAY_NO_ENERGY;
    }
    return PLAY_ON;
}

/* After the level ends, the flames still burn, a falling paddle still
   falls off the screen, the last nuggets still fly to the panel, the last
   chunks still fall, and the gauge's bubbles still rise. While a dwarf
   talks as the level starts, it builds up once he goes. */
void play_idle(void)
{
    if (building && talk_leaving())
        build_step();
    paddle_step(0);
    energy_idle();
    nuggets_step();
    bricks_step();
}

/* Ends every break and lands every nugget at once, so the counts are
   whole. */
void play_finish(void)
{
    bricks_finish();
    nuggets_land();
}

/* The nuggets of a color still to land, in flight. */
uint8_t play_pending(uint8_t color)
{
    return nuggets_flying(color);
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
    bricks_draw();
    energy_draw();
}
