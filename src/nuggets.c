#include "nuggets.h"
#include "debug.h"
#include "sfx.h"
#include "tuning.h"
#include "video.h"

#define ICON_SPRITE(c) (XRAM_NUGGET_ICONS + (c) * sizeof(mode5_csprite_t))
#define NUGGET_SPRITE(i) (XRAM_NUGGET_SPRITES + (i) * sizeof(mode5_csprite_t))

/* The left panel is a framed box, with a line for each color reached: the
   nugget icon, then the count. */
#define PANEL_TOP_ROW 1
#define ICON_X 12
#define COUNT_COL 3
#define COUNT_DIGITS 5

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

static flight_t flights[NUGGETS_MAX];
static uint8_t lines; /* colors shown in the panel */

static int16_t icon_y(uint8_t color)
{
    return (PANEL_TOP_ROW + 1 + color) * 8;
}

static void count_draw(uint8_t color)
{
    video_number(COUNT_COL, PANEL_TOP_ROW + 1 + color, nuggets[color], COUNT_DIGITS,
                 TEXT_COLOR, BOX_FILL);
}

void nuggets_add(uint8_t color)
{
    if (nuggets[color] < 0xFFFF)
        nuggets[color]++;
    if (color < lines)
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

/* Draws the panel with a line for each of the first colors, and lands any
   nugget still in flight. The panel ends at panel_right. */
void nuggets_start(uint8_t colors, int16_t panel_right)
{
    uint8_t i;

    lines = colors;
    nuggets_land();
    video_box(0, PANEL_TOP_ROW, panel_right / 8 - 1, PANEL_TOP_ROW + 1 + colors, BOX_COLOR);
    for (i = 0; i < BRICK_COLORS; i++)
    {
        sprite_set(ICON_SPRITE(i), XRAM_NUGGET_IMAGE, XRAM_PALETTE_BRICK(i), MODE5_SIZE(8, 8));
        if (i < colors)
        {
            sprite_move(ICON_SPRITE(i), ICON_X, icon_y(i));
            count_draw(i);
        }
    }
    for (i = 0; i < NUGGETS_MAX; i++)
        sprite_set(NUGGET_SPRITE(i), XRAM_NUGGET_IMAGE, XRAM_PALETTE_BRICK(0), MODE5_SIZE(8, 8));
}

/* A nugget at x, y, its top left, flies to its color's line in the panel.
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
    f->to_x = ICON_X;
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
   one that reaches its line in the panel adds to the count. */
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
                sfx_play(SFX_NUGGET, ICON_X);
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
