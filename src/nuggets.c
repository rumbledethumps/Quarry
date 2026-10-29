#include "nuggets.h"
#include "debug.h"
#include "tuning.h"
#include "video.h"

#define ICON_SPRITE(c) (XRAM_NUGGET_ICONS + (c) * sizeof(mode5_csprite_t))
#define NUGGET_SPRITE(i) (XRAM_NUGGET_SPRITES + (i) * sizeof(mode5_csprite_t))

/* The counts are at the top left: the coins, then a line for each color,
   each its icon, as tall as the digits, and its count in outlined digits.
   A line shows once the first of its color lands, and the coins' once the
   first level is cleared. A nugget flies to the middle of its icon. */
#define ICON_X 4
#define ICON_TOP 5
#define LINE_H 12
#define DIGITS_X (ICON_X + 12)
#define NUGGET_TO_X (ICON_X + 1)
#define DIGITS(c) (XRAM_NUGGET_DIGITS + (c) * COUNT_DIGITS * sizeof(mode5_csprite_t))

/* A nugget in flight, stepped along its line like Bresenham's. */
typedef struct
{
    uint8_t flying;
    uint8_t color;
    int16_t x, y;
    int16_t to_x, to_y;
    int16_t dx, dy; /* dy is negative */
    int8_t sx, sy;
    int16_t err;
} flight_t;

uint16_t nuggets[BRICK_COLORS];
uint16_t coins;
uint8_t counts_shown;

static flight_t flights[NUGGETS_MAX];

static int16_t icon_y(uint8_t color)
{
    return ICON_TOP + (color + 1) * LINE_H;
}

/* A line of the counts, its icon and its count, or neither while it is
   not shown. */
static void line_draw(unsigned icon, unsigned digits, uint8_t shown, int16_t y, uint16_t n)
{
    uint8_t i;

    if (shown)
    {
        sprite_move(icon, ICON_X, y - 1);
        video_count(digits, COUNT_DIGITS, DIGITS_X, y - 1, n);
        return;
    }
    sprite_hide(icon);
    for (i = 0; i < COUNT_DIGITS; i++)
        sprite_hide(digits + i * sizeof(mode5_csprite_t));
}

static void count_draw(uint8_t color)
{
    line_draw(ICON_SPRITE(color), DIGITS(color), counts_shown & 1 << color, icon_y(color), nuggets[color]);
}

static void coins_draw(void)
{
    line_draw(XRAM_COIN_ICON, XRAM_COIN_DIGITS, counts_shown & COUNT_COINS, ICON_TOP, coins);
}

/* A coin, for the first clear of a level. */
void coins_add(void)
{
    if (coins < 0xFFFF)
        coins++;
    counts_shown |= COUNT_COINS;
    coins_draw();
}

void nuggets_add(uint8_t color)
{
    if (nuggets[color] < 0xFFFF)
        nuggets[color]++;
    counts_shown |= 1 << color;
    count_draw(color);
}

/* Lands every nugget still in flight at once. */
void nuggets_land(void)
{
    uint8_t i;

    for (i = 0; i < NUGGETS_MAX; i++)
        if (flights[i].flying)
        {
            flights[i].flying = 0;
            sprite_hide(NUGGET_SPRITE(i));
            nuggets_add(flights[i].color);
        }
}

/* How many nuggets of a color are in flight. */
uint8_t nuggets_flying(uint8_t color)
{
    uint8_t i, n = 0;

    for (i = 0; i < NUGGETS_MAX; i++)
        if (flights[i].flying && flights[i].color == color)
            n++;
    return n;
}

/* Shows the lines of the counts that have been reached, and lands any
   nugget still in flight. */
void nuggets_start(void)
{
    uint8_t i;

    nuggets_land();
    sprite_set(XRAM_COIN_ICON, XRAM_COIN_IMAGE, XRAM_PALETTE_SLED, MODE5_SIZE(ICON_SIZE, ICON_SIZE));
    coins_draw();
    for (i = 0; i < BRICK_COLORS; i++)
    {
        sprite_set(ICON_SPRITE(i), XRAM_NUGGET_ICON_IMAGE, XRAM_PALETTE_BRICK(i), MODE5_SIZE(ICON_SIZE, ICON_SIZE));
        count_draw(i);
    }
    for (i = 0; i < NUGGETS_MAX; i++)
        sprite_set(NUGGET_SPRITE(i), XRAM_NUGGET_IMAGE, XRAM_PALETTE_BRICK(0), MODE5_SIZE(8, 8));
}

/* A nugget at x, y, its top left, flies to its color's line of the counts.
   It shows at once, so it takes the place of the brick that just broke
   with no frame between. With every flight taken, it counts at once. */
void nuggets_spawn(int16_t x, int16_t y, uint8_t color)
{
    uint8_t i;
    flight_t *f;

    for (i = 0; i < NUGGETS_MAX && flights[i].flying; i++)
        ;
    if (i == NUGGETS_MAX)
    {
        nuggets_add(color);
        return;
    }
    f = &flights[i];
    f->flying = 1;
    f->color = color;
    f->x = x;
    f->y = y;
    f->to_x = NUGGET_TO_X;
    f->to_y = icon_y(color);
    f->dx = f->to_x > x ? f->to_x - x : x - f->to_x;
    f->dy = f->to_y > y ? y - f->to_y : f->to_y - y;
    f->sx = x < f->to_x ? 1 : -1;
    f->sy = y < f->to_y ? 1 : -1;
    f->err = f->dx + f->dy;
    xram0_poke16(NUGGET_SPRITE(i) + offsetof(mode5_csprite_t, palette_ptr), XRAM_PALETTE_BRICK(color));
    sprite_move(NUGGET_SPRITE(i), x, y);
}

/* Each nugget takes TUNE_NUGGET_SPEED pixel steps along its line, and the
   one that reaches its line of the counts adds to it. */
void nuggets_step(void)
{
    uint8_t i, n;

    for (i = 0; i < NUGGETS_MAX; i++)
    {
        flight_t *f = &flights[i];
        if (!f->flying)
            continue;
        for (n = 0; n < TUNE_NUGGET_SPEED; n++)
        {
            int16_t e2;
            if (f->x == f->to_x && f->y == f->to_y)
            {
                nuggets_add(f->color);
                DEBUG_LOG("nugget landed, %u\n", nuggets[f->color]);
                f->flying = 0;
                sprite_hide(NUGGET_SPRITE(i));
                break;
            }
            e2 = f->err * 2;
            if (e2 >= f->dy)
            {
                f->err += f->dy;
                f->x += f->sx;
            }
            if (e2 <= f->dx)
            {
                f->err += f->dx;
                f->y += f->sy;
            }
        }
    }
}

void nuggets_draw(void)
{
    uint8_t i;

    for (i = 0; i < NUGGETS_MAX; i++)
        if (flights[i].flying)
            sprite_move(NUGGET_SPRITE(i), flights[i].x, flights[i].y);
}
