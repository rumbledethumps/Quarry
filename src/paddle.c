#include "paddle.h"
#include "debug.h"
#include "input.h"
#include "play.h"
#include "scene.h"
#include "sfx.h"
#include "tuning.h"
#include "upgrades.h"
#include "video.h"
#include "xram.h"

#define JET_SPRITE(i) (XRAM_JET_SPRITES + (i) * sizeof(mode5_csprite_t))
#define SMOKE_SPRITE(i) (XRAM_SMOKE_SPRITES + (i) * sizeof(mode5_csprite_t))
#define JET_IMAGE(i) (XRAM_JET_IMAGES + (i) * sizeof(jet_image_t))
#define SMOKE_IMAGE(i) (XRAM_SMOKE_IMAGES + (i) * sizeof(piece_image_t))

/* The jets hang from the mount, under the plate and the mount. */
#define JET_TOP 5

/* The flames burn through their frames, short, medium and long, a frame
   every FLAME_STEPS steps, each jet out of step with the others. */
#define FLAME_STEPS 3
static const uint8_t flame_cycle[8] = {0, 1, 2, 2, 1, 2, 1, 1};

/* A sputtering jet shows its short flame on the steps with a bit set
   here, and its nozzle alone on the others. */
static const uint8_t sputter_pattern[8] = {0xB2, 0x4C, 0x91, 0x0A, 0x48, 0x02, 0x20, 0x01};

/* The puff of smoke shows each frame for SMOKE_STEPS steps, and rises a
   pixel every SMOKE_RISE steps. */
#define SMOKE_STEPS 10
#define SMOKE_RISE 4

/* A falling paddle tilts, the right end lower, a pixel more in 8 every
   TILT_STEPS steps, up to TILT_MAX, the tilts of art/sleds/. */
#define TILT_STEPS 6
#define TILT_MAX 2

uint8_t paddle_state;
int32_t paddle_x;
int32_t paddle_y;
uint8_t paddle_width;
uint8_t paddle_left;

static uint16_t paddle_speed;
static uint8_t paddle_moved; /* the sled needs drawing */
static uint8_t sled_level;   /* its sled, the level of the width upgrade */
static uint8_t sled_tilt;    /* the tilt its sprite shows */
static uint8_t sled_jets;
static int8_t steer;         /* 1 moving right, -1 left, 0 still */
static uint16_t state_steps; /* steps since paddle_state changed */
static int16_t fall_speed;   /* 1/256 px per step */
static int16_t smoke_x;      /* where the paddle gave up, for the smoke */
static int16_t smoke_y;

/* The center of jet i of jets under a sled width px wide, as jet_x() in
   art/sled.py. */
static uint8_t jet_x(uint8_t width, uint8_t jets, uint8_t i)
{
    return jets == 1 ? width / 2 : 7 + i * (width - 14) / (jets - 1);
}

/* The width of a sled's image and sprite, a multiple of 4. */
#define SLED_IMAGE_W(width) (((width) + 3) & ~3)

/* The image of the sled of a level of the width upgrade, width px wide,
   level or tilted, as art/sled.py lays it out. */
static unsigned sled_image(uint8_t level, uint8_t width, uint8_t tilt)
{
    unsigned image = scene_sled(level);

    if (tilt)
        image += SLED_IMAGE_W(width) * (8 + (tilt - 1) * SLED_TILT_ROWS) / 2;
    return image;
}

static void jet_set(unsigned sprite, uint8_t frame, uint8_t flip)
{
    xram0_poke16(sprite + offsetof(mode5_csprite_t, xram_sprite_ptr), JET_IMAGE(frame));
    xram0_poke8(sprite + offsetof(mode5_csprite_t, attributes),
                flip ? MODE5_4BPP | MODE5_HFLIP : MODE5_4BPP);
}

/* The sled of a level of the width upgrade with its top left at x, y, from
   count sprites at sprites: the sled, then its jets, with a medium flame,
   or the nozzles alone without flames. The sprites it doesn't need are
   hidden, and all of them with level SLED_NONE. */
void sled_show(unsigned sprites, uint8_t count, int16_t x, int16_t y, uint8_t level, uint8_t look)
{
    uint8_t i, width = 0, n = 0, scale = look & SLED_DOUBLE ? 2 : 1;
    uint8_t doubling = look & SLED_DOUBLE ? MODE5_HDOUBLE | MODE5_VDOUBLE : 0;
    unsigned palette = look & SLED_DIM ? XRAM_PALETTE_SHADE : XRAM_PALETTE_SLED;

    if (level != SLED_NONE)
    {
        width = upgrades_width_at(level);
        n = upgrades_jets_at(level);
        sprite_set(sprites, sled_image(level, width, 0), palette, MODE5_SIZE(SLED_IMAGE_W(width), 8));
        sprite_attributes(sprites, doubling);
        sprite_move(sprites, x, y);
    }
    else
        sprite_hide(sprites);
    for (i = 0; i + 1 < count; i++)
    {
        unsigned jet = sprites + (i + 1) * sizeof(mode5_csprite_t);
        if (i < n)
        {
            sprite_set(jet, JET_IMAGE(look & SLED_FLAMES ? JET_FLAME + 1 : JET_NOZZLE), palette,
                       MODE5_SIZE(8, 12));
            sprite_attributes(jet, doubling);
            sprite_move(jet, x + (jet_x(width, n, i) - 4) * scale, y + JET_TOP * scale);
        }
        else
            sprite_hide(jet);
    }
}

/* The paddle is a sled, a picture of the sled for its width from
   art/sleds/, and a sprite for each of its jets, so they can swivel. Its
   width, jets and speed come from the upgrades bought so far. */
void paddle_start(void)
{
    uint8_t i;

    paddle_state = PADDLE_HOVER;
    state_steps = 0;
    paddle_width = upgrades_width();
    paddle_speed = upgrades_speed();
    paddle_x = FIX((play_left + play_right - paddle_width) / 2);
    paddle_y = FIX(TUNE_PADDLE_Y);
    paddle_left = 0;
    steer = 0;
    sled_level = upgrade_levels[UPGRADE_WIDTH];
    sled_tilt = 0;
    sled_jets = upgrades_jets_at(sled_level);
    sprite_set(XRAM_SLED_SPRITE, sled_image(sled_level, paddle_width, 0), XRAM_PALETTE_SLED,
               MODE5_SIZE(SLED_IMAGE_W(paddle_width), 8));
    for (i = 0; i < JETS_MAX; i++)
        sprite_set(JET_SPRITE(i), JET_IMAGE(JET_NOZZLE), XRAM_PALETTE_SLED, MODE5_SIZE(8, 12));
    for (i = 0; i < 2; i++)
        sprite_set(SMOKE_SPRITE(i), SMOKE_IMAGE(0), XRAM_PALETTE_FX, MODE5_SIZE(8, 8));
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
        steer = x > paddle_x ? 1 : -1;
        paddle_x = x;
        paddle_moved = 1;
    }
}

/* With controls 0, as after the stage ends, the paddle still burns its
   flames, and finishes falling if it was. */
void paddle_step(uint8_t controls)
{
    state_steps++;
    steer = 0;
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

/* A jet swivels to push the sled the way it moves. Sputtering, it shows
   its short flame now and then, and falling, its nozzle alone. */
static void jet_draw(uint8_t i, int16_t x, int16_t y, uint8_t tilt)
{
    uint8_t frame = JET_NOZZLE, cx = jet_x(paddle_width, sled_jets, i);

    if (i >= sled_jets || paddle_state == PADDLE_GONE)
    {
        sprite_hide(JET_SPRITE(i));
        return;
    }
    if (paddle_state == PADDLE_HOVER)
    {
        frame = JET_FLAME + flame_cycle[(state_steps / FLAME_STEPS + i * 3) & 7];
        if (steer)
            frame += JET_SWIVEL;
    }
    else if (paddle_state == PADDLE_SPUTTER &&
             (sputter_pattern[(state_steps / 8 + i * 3) & 7] & (1 << (state_steps & 7))))
        frame = JET_FLAME;
    sprite_move(JET_SPRITE(i), x + cx - 4, y + JET_TOP + cx * tilt / 8);
    jet_set(JET_SPRITE(i), frame, steer < 0);
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
    uint8_t i, tilt = paddle_tilt();
    int16_t x = PX(paddle_x);
    int16_t y = PX(paddle_y);

    if (paddle_moved)
    {
        if (tilt != sled_tilt)
        {
            sled_tilt = tilt;
            xram0_poke16(XRAM_SLED_SPRITE + offsetof(mode5_csprite_t, xram_sprite_ptr),
                         sled_image(sled_level, paddle_width, tilt));
            xram0_poke8(XRAM_SLED_SPRITE + offsetof(mode5_csprite_t, width_height),
                        MODE5_SIZE(SLED_IMAGE_W(paddle_width), tilt ? SLED_TILT_ROWS : 8));
        }
        if (paddle_state != PADDLE_GONE)
            sprite_move(XRAM_SLED_SPRITE, x, y);
        else
            sprite_hide(XRAM_SLED_SPRITE);
        paddle_moved = 0;
    }
    for (i = 0; i < JETS_MAX; i++)
        jet_draw(i, x, y, tilt);
    smoke_draw();
}
