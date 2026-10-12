#include <rp6502.h>
#include "bricks.h"
#include "debug.h"
#include "input.h"
#include "menu.h"
#include "nuggets.h"
#include "play.h"
#include "shop.h"
#include "tuning.h"
#include "video.h"

/* Steps after a stage ends before the menu takes a choice, so a press
   meant for the last ball doesn't choose. */
#define STAGE_OVER_WAIT 60

/* There is only stage 1 so far. */
#define STAGES 1

/* game_state */
#define STATE_PLAY 1
#define STATE_MENU 2 /* the end-of-stage menu */
#define STATE_SHOP 3 /* the upgrade screen */

static uint8_t game_state;
static uint8_t stage = 1;
static uint8_t stage_set; /* the playfield shows a stage ready to play */
static const char *stage_result;

/* Lays out the stage, centers the playfield between the panels, and sets
   up the paddle and every ball, ready to play. It starts from no sprites,
   so nothing is left of the upgrade screen. */
static void stage_setup(void)
{
    int16_t width;

    video_hide_sprites();
    play_init();
    bricks_layout();
    width = bricks_cols * BRICK_W;
    play_left = (SCREEN_W - width) / 2;
    play_right = play_left + width;
    video_walls(play_left, play_right);
    video_text_clear();
    bricks_start(play_left, TUNE_BRICKS_Y);
    nuggets_start(1, play_left - WALL_SIZE);
    play_start();
    stage_set = 1;
}

static void stage_play(void)
{
    if (stage_set)
        menu_close();
    else
        stage_setup();
    stage_set = 0;
    game_state = STATE_PLAY;
    DEBUG_LOG("stage start\n");
}

/* Clearing a stage unlocks the next, which Play starts. Otherwise Play
   starts the same stage again. */
static void stage_end(uint8_t how)
{
    if (how == PLAY_CLEARED && stage < STAGES)
        stage++;
    stage_result = how == PLAY_CLEARED ? "STAGE CLEAR"
                   : how == PLAY_OUT   ? "OUT OF BALLS"
                                       : "OUT OF ENERGY";
    menu_open(stage_result, MENU_UPGRADES, STAGE_OVER_WAIT);
    game_state = STATE_MENU;
}

static void wait_vsync(void)
{
    static uint8_t last;

    while (ria_vsync() == last)
        ;
    last = ria_vsync();
}

/* Play, then the end-of-stage menu: Upgrades opens the upgrade screen, and
   its Back sets up the next stage behind the menu, with the upgrades on
   the paddle. Play plays. */
int main(void)
{
    /* The panel frames are line-drawing glyphs from code page 437. */
    ria_attr_set(437, RIA_ATTR_CODE_PAGE);
    video_init();
    input_init();
    stage_setup();
    video_start();
    stage_play();

    for (;;)
    {
        wait_vsync();
        if (game_state != STATE_SHOP)
            play_draw();
        input_read();
        switch (game_state)
        {
        case STATE_PLAY:
        {
            uint8_t how = play_step();
            if (how != PLAY_ON)
                stage_end(how);
            break;
        }
        case STATE_MENU:
            play_idle();
            switch (menu_step())
            {
            case MENU_PLAY:
                stage_play();
                break;
            case MENU_UPGRADES:
                play_finish();
                shop_open();
                game_state = STATE_SHOP;
                break;
            }
            break;
        case STATE_SHOP:
            if (shop_step())
            {
                stage_setup();
                menu_open(stage_result, MENU_PLAY, 0);
                game_state = STATE_MENU;
            }
            break;
        }
    }
}
