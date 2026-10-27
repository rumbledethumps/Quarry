#include "shop.h"
#include "bricks.h"
#include "debug.h"
#include "input.h"
#include "nuggets.h"
#include "paddle.h"
#include "sfx.h"
#include "upgrades.h"
#include "video.h"
#include "scene.h"
#include "xram.h"

/* The upgrade screen, after the concept. Rock all around, the nugget count
   at the top, then UPGRADES, a box for each upgrade, and a panel under
   them that tells of the upgrade picked last, with BUY and BACK. It is
   all text cells, but for the nugget icons and the sleds. */

#define SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))
#define COUNT_ICON 0 /* the sprites, in the order of the menu list */
#define COST_ICON 1  /* one for each upgrade */
#define NODE_SLED 3  /* a sled and its jet for each upgrade */
#define NOW_SLED 7   /* a sled and its jets */
#define NEXT_SLED (NOW_SLED + 1 + JETS_MAX)

_Static_assert(NEXT_SLED + 1 + JETS_MAX <= MENU_SPRITES, "MENU_SPRITES is too few.");

/* Where things are, in text cells. */
#define BAR_LEFT 13
#define BAR_RIGHT 26
#define TITLE_ROW 4
#define NODE_TOP 6
#define NODE_BOTTOM 13
#define NODE_COLS 12
#define PANEL_LEFT 3
#define PANEL_RIGHT 36
#define PANEL_TOP 16
#define PANEL_BOTTOM 28
#define NOW_COL 5
#define ARROW_COL 14
#define NEXT_COL 16
#define PREVIEW_ROW 22
#define HINT_ROW 25
#define BUTTON_LEFT 27
#define BUTTON_RIGHT 34
#define BUY_TOP 18
#define BACK_TOP 22

_Static_assert(UPGRADE_LEVELS_MAX <= NODE_COLS - 2, "The boxes have no room for the pips.");

/* Glyphs of code page 437. */
#define LEFT_ARROWHEAD "\x11"
#define RIGHT_ARROWHEAD "\x10"
#define ARROW "\x1A"
#define PIP_ON '\xFE'
#define PIP_OFF '\xFA'

/* What can be picked, in the order that up and down step through. */
#define PICK_BUY UPGRADES
#define PICK_BACK (UPGRADES + 1)
#define PICKS (UPGRADES + 2)

static const char chevrons[] = "\xAF\xAF\xAF\xAF\xAF\xAF";
static const char line[] = "\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4\xC4";

static const uint8_t node_left[UPGRADES] = {8, 21};
static const char *const names[UPGRADES] = {"WIDTH", "SPEED"};
static const char *const titles[UPGRADES] = {"WIDER PADDLE", "FASTER PADDLE"};

static uint8_t picked;
static uint8_t upgrade; /* the upgrade picked last, which BUY buys */

static uint8_t can_buy(uint8_t u)
{
    uint16_t cost = upgrades_cost(u);

    return cost && nuggets[BRICK_WHITE] >= cost;
}

static void nugget_at(uint8_t sprite, uint8_t col, uint8_t row)
{
    sprite_set(SPRITE(sprite), XRAM_NUGGET_IMAGE, XRAM_PALETTE_BRICK(BRICK_WHITE), MODE5_SIZE(8, 8));
    sprite_move(SPRITE(sprite), col * 8, row * 8);
}

static void count_draw(void)
{
    video_box(BAR_LEFT, 0, BAR_RIGHT, 2, BOX_COLOR);
    nugget_at(COUNT_ICON, BAR_LEFT + 4, 1);
    video_number(BAR_LEFT + 6, 1, nuggets[BRICK_WHITE], 5, TEXT_COLOR, BOX_FILL);
}

/* The box of an upgrade: its name, a picture, a pip for each level, filled
   for each bought, and the cost of the next. The one BUY buys has a gold
   frame. */
static void node_draw(uint8_t u)
{
    uint8_t left = node_left[u], max = upgrades_max(u), i;
    uint16_t cost = upgrades_cost(u);
    char pips[UPGRADE_LEVELS_MAX + 1];

    video_box(left, NODE_TOP, left + NODE_COLS - 1, NODE_BOTTOM, u == upgrade ? PICK_COLOR : BOX_COLOR);
    video_text(left + 3, NODE_TOP + 1, names[u], TEXT_COLOR, BOX_FILL);
    sled_show(SPRITE(NODE_SLED + u * 2), 2, (left + 4) * 8, (NODE_TOP + 3) * 8, 0, 0);
    if (u == UPGRADE_WIDTH)
    {
        video_text(left + 2, NODE_TOP + 3, LEFT_ARROWHEAD, TEXT_COLOR, BOX_FILL);
        video_text(left + 8, NODE_TOP + 3, RIGHT_ARROWHEAD, TEXT_COLOR, BOX_FILL);
    }
    else
        video_text(left + 7, NODE_TOP + 3, chevrons + 4, TEXT_COLOR, BOX_FILL);
    for (i = 0; i < max; i++)
        pips[i] = i < upgrade_levels[u] ? PIP_ON : PIP_OFF;
    pips[max] = 0;
    video_text(left + (NODE_COLS - max) / 2, NODE_TOP + 5, pips, PICK_COLOR, BOX_FILL);
    if (cost)
    {
        nugget_at(COST_ICON + u, left + 3, NODE_TOP + 6);
        video_number(left + 5, NODE_TOP + 6, cost, 3, can_buy(u) ? TEXT_COLOR : DIM_COLOR, BOX_FILL);
    }
    else
    {
        sprite_hide(SPRITE(COST_ICON + u));
        video_text(left + 4, NODE_TOP + 6, "MAX", TEXT_COLOR, BOX_FILL);
    }
}

static void button_draw(uint8_t pick)
{
    uint8_t top = pick == PICK_BUY ? BUY_TOP : BACK_TOP;
    uint8_t fg = pick == PICK_BUY && !can_buy(upgrade) ? DIM_COLOR : TEXT_COLOR;

    video_box(BUTTON_LEFT, top, BUTTON_RIGHT, top + 2, picked == pick ? PICK_COLOR : BOX_FILL);
    video_text(BUTTON_LEFT + 2, top + 1, pick == PICK_BUY ? " BUY" : "BACK", fg, BOX_FILL);
}

/* The panel: what the upgrade does, now and with the next level, a word
   if there are not nuggets enough, then BUY and BACK. */
static void panel_draw(void)
{
    uint8_t level = upgrade_levels[upgrade];
    uint8_t max = level >= upgrades_max(upgrade);

    video_box(PANEL_LEFT, PANEL_TOP, PANEL_RIGHT, PANEL_BOTTOM, BOX_COLOR);
    video_text(NOW_COL, PANEL_TOP + 2, titles[upgrade], TEXT_COLOR, BOX_FILL);
    video_text(NOW_COL, PANEL_TOP + 3, line, BOX_COLOR, BOX_FILL);
    if (upgrade == UPGRADE_WIDTH)
    {
        sled_show(SPRITE(NOW_SLED), 1 + JETS_MAX, NOW_COL * 8, PREVIEW_ROW * 8, level, 1);
        sled_show(SPRITE(NEXT_SLED), 1 + JETS_MAX, NEXT_COL * 8, PREVIEW_ROW * 8,
                  max ? SLED_NONE : level + 1, 1);
    }
    else
    {
        sled_show(SPRITE(NOW_SLED), 1 + JETS_MAX, 0, 0, SLED_NONE, 0);
        sled_show(SPRITE(NEXT_SLED), 1 + JETS_MAX, 0, 0, SLED_NONE, 0);
        video_text(NOW_COL, PREVIEW_ROW, chevrons + 5 - level, TEXT_COLOR, BOX_FILL);
        if (!max)
            video_text(NEXT_COL, PREVIEW_ROW, chevrons + 4 - level, TEXT_COLOR, BOX_FILL);
    }
    if (max)
        video_text(ARROW_COL, PREVIEW_ROW, "MAX", TEXT_COLOR, BOX_FILL);
    else
    {
        video_text(ARROW_COL, PREVIEW_ROW, ARROW, TEXT_COLOR, BOX_FILL);
        if (!can_buy(upgrade))
            video_text(NOW_COL, HINT_ROW, "NOT ENOUGH NUGGETS", DIM_COLOR, BOX_FILL);
    }
    button_draw(PICK_BUY);
    button_draw(PICK_BACK);
}

static void redraw(void)
{
    count_draw();
    node_draw(UPGRADE_WIDTH);
    node_draw(UPGRADE_SPEED);
    panel_draw();
}

/* Hides the pictures, which would show over a menu on top of the screen. */
void shop_hide(void)
{
    uint8_t i;

    for (i = 0; i < MENU_SPRITES; i++)
        sprite_hide(SPRITE(i));
}

void shop_open(void)
{
    video_hide_sprites();
    scene_menu();
    video_rock();
    video_text_clear();
    video_text(NOW_COL + 4, TITLE_ROW, line + 10, BOX_COLOR, BOX_FILL);
    video_text(16, TITLE_ROW, "UPGRADES", TEXT_COLOR, BOX_FILL);
    video_text(25, TITLE_ROW, line + 10, BOX_COLOR, BOX_FILL);
    picked = UPGRADE_WIDTH;
    upgrade = UPGRADE_WIDTH;
    redraw();
    DEBUG_LOG("upgrades\n");
}

/* Up and left step back through WIDTH, SPEED, BUY and BACK, and down and
   right step on. Choose on an upgrade goes to BUY. Returns 1 when BACK is
   chosen. */
uint8_t shop_step(void)
{
    uint8_t was = picked;

    if (input_pressed & (INPUT_UP | INPUT_LEFT))
        picked = (picked + PICKS - 1) % PICKS;
    else if (input_pressed & (INPUT_DOWN | INPUT_RIGHT))
        picked = (picked + 1) % PICKS;
    else if (input_pressed & INPUT_CHOOSE)
    {
        if (picked < UPGRADES)
            picked = PICK_BUY;
        else if (picked == PICK_BUY)
        {
            if (upgrades_buy(upgrade))
            {
                sfx_play(SFX_BUY, SFX_CENTER);
                redraw();
            }
        }
        else
        {
            DEBUG_LOG("upgrades closed\n");
            return 1;
        }
    }
    if (picked != was)
    {
        sfx_play(SFX_MOVE, SFX_CENTER);
        if (picked < UPGRADES && picked != upgrade)
        {
            upgrade = picked;
            node_draw(UPGRADE_WIDTH);
            node_draw(UPGRADE_SPEED);
            panel_draw();
        }
        else
        {
            button_draw(PICK_BUY);
            button_draw(PICK_BACK);
        }
    }
    return 0;
}
