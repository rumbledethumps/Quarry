#include <rp6502.h>
#include <stdlib.h>
#include "bricks.h"
#include "debug.h"
#include "frame.h"
#include "input.h"
#include "menu.h"
#include "nuggets.h"
#include "play.h"
#include "save.h"
#include "scene.h"
#include "sfx.h"
#include "shop.h"
#include "title.h"
#include "tuning.h"
#include "upgrades.h"
#include "video.h"

/* Steps after a stage ends before the menu takes a choice, so a press
   meant for the last ball doesn't choose. */
#define STAGE_OVER_WAIT 60

/* game_state */
#define STATE_PLAY 1
#define STATE_MENU 2    /* the end-of-stage menu */
#define STATE_SHOP 3    /* the upgrade screen */
#define STATE_TITLE 4
#define STATE_CONFIRM 5 /* yes or no to a new game over the save */
#define STATE_PAUSE 6

/* The menus. The items of each are numbered from 1, as menu_step()
   returns them. */
static const char *const end_items[] = {"UPGRADES", "PLAY"};
#define END_UPGRADES 1
#define END_PLAY 2
static const char *const pause_items[] = {"CONTINUE", "EXIT"};
#define PAUSE_CONTINUE 1
#define PAUSE_EXIT 2
static const char *const title_items[] = {"RESUME", "NEW GAME", "EXIT"};
#define TITLE_RESUME 1
#define TITLE_NEW_GAME 2
#define TITLE_EXIT 3
static const char *const confirm_items[] = {"YES", "NO"};
#define CONFIRM_YES 1
#define CONFIRM_NO 2

static const menu_t pause_menu = {20, 11, BOX_COLOR, "PAUSED", pause_items, 2};
static const menu_t title_menu = {20, 12, BOX_FILL, 0, title_items, 3};
static const menu_t confirm_menu = {20, 12, BOX_COLOR, "START OVER?", confirm_items, 2};
static menu_t end_menu = {20, 11, BOX_COLOR, 0, end_items, 2};

static uint8_t game_state;
static uint8_t paused_state; /* what the pause menu came from */
static uint8_t paused_pick;  /* the pick of the end-of-stage menu under it */
static uint8_t stage = 1;
static uint8_t stage_set; /* the playfield shows a stage ready to play */

/* Lays out the stage, centers the playfield with its frame and curtains,
   and sets up the paddle and every ball, ready to play. It starts from no
   sprites and the stage's own art, so nothing is left of another screen. */
static void stage_setup(void)
{
    int16_t width;

    video_hide_sprites();
    scene_stage(upgrade_levels[UPGRADE_WIDTH]);
    play_init();
    bricks_layout();
    width = bricks_cols * BRICK_W + 2 * bricks_margin;
    play_left = (SCREEN_W - width) / 2;
    play_right = play_left + width;
    frame_start(play_left, play_right);
    video_text_clear();
    bricks_start(play_left + bricks_margin, TUNE_BRICKS_Y);
    nuggets_start(1);
    play_start();
    stage_set = 1;
}

/* A stage starts, and the game saves. */
static void stage_play(void)
{
    if (stage_set)
        menu_close();
    else
        stage_setup();
    stage_set = 0;
    game_state = STATE_PLAY;
    save_write();
    DEBUG_LOG("stage start\n");
}

/* Clearing a stage unlocks the next, which Play starts. Otherwise Play
   starts the same stage again. The game saves. */
static void stage_end(uint8_t how)
{
    if (how == PLAY_CLEARED && stage < STAGES)
    {
        if (stage == stages_unlocked)
            stages_unlocked++;
        stage++;
    }
    end_menu.title = how == PLAY_CLEARED ? "STAGE CLEAR"
                     : how == PLAY_OUT   ? "OUT OF BALLS"
                                         : "OUT OF ENERGY";
    menu_open(&end_menu, END_UPGRADES - 1, 0, STAGE_OVER_WAIT);
    game_state = STATE_MENU;
    save_write();
}

/* Resume is grayed out until there is a save. */
static void title_show(void)
{
    title_open();
    menu_open(&title_menu, save_exists ? TITLE_RESUME - 1 : TITLE_NEW_GAME - 1,
              save_exists ? 0 : 1 << (TITLE_RESUME - 1), 0);
    game_state = STATE_TITLE;
    DEBUG_LOG("title\n");
}

/* Play from the highest stage unlocked. */
static void game_start(void)
{
    stage = stages_unlocked;
    stage_setup();
    stage_play();
}

/* Pausing saves. The menu goes over whatever was on the screen, but for
   the pictures of the upgrade screen, which would show over it. */
static void pause_open(void)
{
    save_write();
    paused_state = game_state;
    if (game_state == STATE_MENU)
        paused_pick = menu_picked();
    else if (game_state == STATE_SHOP)
        shop_hide();
    menu_open(&pause_menu, PAUSE_CONTINUE - 1, 0, 0);
    game_state = STATE_PAUSE;
    DEBUG_LOG("paused\n");
}

/* Takes the pause menu away and puts back what was under it. */
static void pause_close(void)
{
    menu_close();
    game_state = paused_state;
    paused_state = 0;
    if (game_state == STATE_MENU)
        menu_open(&end_menu, paused_pick, 0, 0);
    else if (game_state == STATE_SHOP)
        shop_open();
    DEBUG_LOG("continue\n");
}

static void wait_vsync(void)
{
    static uint8_t last;

    while (ria_vsync() == last)
        ;
    last = ria_vsync();
}

/* The title screen first. Then play, and the end-of-stage menu: Upgrades
   opens the upgrade screen, whose Back sets up the next stage behind the
   menu with the upgrades on the paddle, and Play plays. Esc or Start
   pauses at any time, and Exit there goes back to the title screen. */
int main(void)
{
    /* The panel frames are line-drawing glyphs from code page 437. */
    ria_attr_set(437, RIA_ATTR_CODE_PAGE);
    video_init();
    input_init();
    sfx_init();
    save_load();
    title_show();
    video_start();

    for (;;)
    {
        wait_vsync();
        if (game_state == STATE_TITLE || game_state == STATE_CONFIRM)
            title_draw();
        else if (game_state != STATE_SHOP && paused_state != STATE_SHOP)
            play_draw();
        input_read();
        sfx_step();
        if ((input_pressed & INPUT_PAUSE) && game_state <= STATE_SHOP)
        {
            pause_open();
            continue;
        }
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
            case END_PLAY:
                stage_play();
                break;
            case END_UPGRADES:
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
                menu_open(&end_menu, END_PLAY - 1, 0, 0);
                game_state = STATE_MENU;
            }
            break;
        case STATE_PAUSE:
            if (input_pressed & INPUT_PAUSE)
                pause_close();
            else
                switch (menu_step())
                {
                case PAUSE_CONTINUE:
                    pause_close();
                    break;
                case PAUSE_EXIT:
                    play_finish();
                    paused_state = 0;
                    title_show();
                    break;
                }
            break;
        case STATE_TITLE:
            title_step();
            switch (menu_step())
            {
            case TITLE_RESUME:
                save_load();
                game_start();
                break;
            case TITLE_NEW_GAME:
                if (save_exists)
                {
                    menu_close();
                    menu_open(&confirm_menu, CONFIRM_NO - 1, 0, 0);
                    game_state = STATE_CONFIRM;
                }
                else
                {
                    save_new_game();
                    game_start();
                }
                break;
            case TITLE_EXIT:
                exit(0);
            }
            break;
        case STATE_CONFIRM:
            title_step();
            switch (menu_step())
            {
            case CONFIRM_YES:
                DEBUG_LOG("new game\n");
                save_new_game();
                game_start();
                break;
            case CONFIRM_NO:
                menu_close();
                menu_open(&title_menu, TITLE_NEW_GAME - 1, 0, 0);
                game_state = STATE_TITLE;
                break;
            }
            break;
        }
    }
}
