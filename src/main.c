#include <rp6502.h>
#include "bricks.h"
#include "cursor.h"
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
#include "talk.h"
#include "title.h"
#include "tuning.h"
#include "upgrades.h"
#include "video.h"

/* Steps after a level ends before the menu takes a choice, so a press
   meant for the last ball doesn't choose. */
#define LEVEL_OVER_WAIT 60
/* And after a dwarf, so a second press meant for him doesn't choose. */
#define TALK_OVER_WAIT 20

/* game_state */
#define STATE_PLAY 1
#define STATE_MENU 2    /* the menu when a level ends */
#define STATE_SHOP 3    /* the upgrade screen */
#define STATE_TITLE 4
#define STATE_CONFIRM 5 /* yes or no to a new game over the save */
#define STATE_PAUSE 6

/* The menus. The items of each are numbered from 1, as menu_step()
   returns them. */
static const char *const end_items[] = {"UPGRADES", "REPLAY", "MAIN MENU"};
#define END_UPGRADES 1
#define END_REPLAY 2
#define END_MAIN_MENU 3
static const char *const pause_items[] = {"RESUME", "UPGRADES", "RESTART", "MAIN MENU"};
#define PAUSE_RESUME 1
#define PAUSE_UPGRADES 2
#define PAUSE_RESTART 3
#define PAUSE_MAIN_MENU 4
static const char *const title_items[] = {"RESUME", "NEW GAME"};
#define TITLE_RESUME 1
#define TITLE_NEW_GAME 2
static const char *const confirm_items[] = {"YES", "NO"};
#define CONFIRM_YES 1
#define CONFIRM_NO 2

/* The question to start over takes the title menu's place. */
static const menu_t pause_menu = {20, 7, BOX_TAPE, "PAUSED", pause_items, 4};
static const menu_t title_menu = {20, 11, BOX_PLAIN, 0, title_items, 2};
static const menu_t confirm_menu = {20, 11, BOX_TAPE, "START OVER?", confirm_items, 2};
/* The menu when a level ends says how, by what play_step() returned, from
   PLAY_CLEARED. */
static const menu_t end_menus[] = {
    {20, 9, BOX_TAPE, "LEVEL COMPLETE", end_items, 3},
    {20, 9, BOX_TAPE, "OUT OF BALLS", end_items, 3},
    {20, 9, BOX_TAPE, "OUT OF FUEL", end_items, 3},
};
_Static_assert(PLAY_OUT == PLAY_CLEARED + 1 && PLAY_NO_ENERGY == PLAY_CLEARED + 2, "end_menus is in order.");

static uint8_t game_state;
static uint8_t level = 1; /* the level being played, from 1 */
static uint8_t level_how; /* how it ended, as play_step() returned */

/* Lays out the level, centers the playfield with its frame and curtains,
   and sets up the paddle and every ball, ready to play. It starts from no
   sprites and the level's own art, so nothing is left of another screen. */
static void level_setup(void)
{
    int16_t width;

    video_hide_sprites();
    cursor_hide();
    scene_level(upgrade_ranks[UPGRADE_WIDTH]);
    play_init();
    bricks_layout(level);
    width = bricks_cols * BRICK_W + 2 * bricks_margin;
    play_left = (SCREEN_W - width) / 2;
    play_right = play_left + width;
    frame_start(play_left, play_right);
    menu_clear();
    bricks_start(play_left + bricks_margin, TUNE_BRICKS_Y);
    nuggets_start(1);
    play_start();
}

/* A level starts, set up from the start, and the game saves. The first
   level of a game starts with a dwarf's welcome. */
static void level_play(void)
{
    menu_close();
    level_setup();
    game_state = STATE_PLAY;
    talk_once(TALK_WELCOME);
    save_write();
    DEBUG_LOG("level %u start\n", level);
}

/* The menu when a level ends, which waits wait steps before it takes a
   choice. */
static void end_menu(uint8_t wait)
{
    menu_open(&end_menus[level_how - PLAY_CLEARED], END_UPGRADES - 1, 0, wait);
}

/* The first clear of a level earns a coin and opens the next, which the
   upgrade screen then picks, and a dwarf hands the coin over before the
   menu opens. The game saves. */
static void level_end(uint8_t how)
{
    level_how = how;
    if (how == PLAY_CLEARED && level > levels_cleared)
    {
        levels_cleared = level;
        level_picked = save_levels_open();
        coins_add();
        talk_queue(TALK_COIN);
        DEBUG_LOG("coin for level %u\n", level);
    }
    else
        end_menu(LEVEL_OVER_WAIT);
    game_state = STATE_MENU;
    save_write();
}

/* The last dwarf has gone: the menu waiting for him opens, or the upgrade
   screen's cursor comes back. */
static void talk_over(void)
{
    if (game_state == STATE_MENU)
        end_menu(TALK_OVER_WAIT);
    else if (game_state == STATE_SHOP)
        shop_resume();
}

/* Resume is left off until there is a save. */
static void title_show(void)
{
    title_open(&title_menu);
    menu_open(&title_menu, save_exists ? TITLE_RESUME - 1 : TITLE_NEW_GAME - 1,
              save_exists ? 0 : 1 << (TITLE_RESUME - 1), 0);
    game_state = STATE_TITLE;
    DEBUG_LOG("title\n");
}

/* The upgrade screen, on its upgrades from a level, or on its level select
   from the title. */
static void shop_show(uint8_t on)
{
    shop_open(on);
    game_state = STATE_SHOP;
}

/* A new game starts at once on level 1. */
static void new_game(void)
{
    save_new_game();
    level = 1;
    level_play();
}

/* Pausing saves, and the menu goes over the level. */
static void pause_open(void)
{
    save_write();
    menu_open(&pause_menu, PAUSE_RESUME - 1, 0, 0);
    game_state = STATE_PAUSE;
    DEBUG_LOG("paused\n");
}

static void pause_close(void)
{
    menu_close();
    cursor_hide();
    game_state = STATE_PLAY;
    DEBUG_LOG("resume\n");
}

static void wait_vsync(void)
{
    static uint8_t last;

    while (ria_vsync() == last)
        ;
    last = ria_vsync();
}

/* The title screen first. Resume opens the upgrade screen, where a level
   begins, and New Game begins level 1. When a level ends, its menu goes
   to the upgrade screen, plays it again, or goes to the title. Esc pauses
   a level, with the same choices and Restart. There is no way out of the
   game: every menu leads to another screen. */
int main(void)
{
    uint8_t talked = 0; /* whether a dwarf talked the step before */

    video_init();
    scene_menus();
    input_init();
    sfx_init();
    save_load();
    title_show();

    for (;;)
    {
        wait_vsync();
        cursor_draw();
        menu_draw();
        talk_draw();
        if (game_state == STATE_PLAY || game_state == STATE_MENU || game_state == STATE_PAUSE)
            play_draw();
        else if (game_state == STATE_SHOP)
            shop_draw();
        input_read();
        sfx_step();
        if (talk_step())
        {
            /* A dwarf takes the input, and the screen under him carries on. */
            if (game_state == STATE_PLAY || game_state == STATE_MENU)
                play_idle();
            else if (game_state == STATE_SHOP)
                shop_idle();
            talked = 1;
            cursor_step();
            continue;
        }
        if (talked)
        {
            talked = 0;
            talk_over();
        }
        switch (game_state)
        {
        case STATE_PLAY:
        {
            uint8_t how;
            if (input_pressed & INPUT_PAUSE)
            {
                pause_open();
                break;
            }
            how = play_step();
            if (how != PLAY_ON)
                level_end(how);
            break;
        }
        case STATE_MENU:
            play_idle();
            switch (menu_step())
            {
            case END_UPGRADES:
                play_finish();
                shop_show(SHOP_ON_UPGRADES);
                break;
            case END_REPLAY:
                play_finish();
                level_play();
                break;
            case END_MAIN_MENU:
                play_finish();
                title_show();
                break;
            }
            break;
        case STATE_PAUSE:
            if (input_pressed & INPUT_PAUSE)
                pause_close();
            else
                switch (menu_step())
                {
                case PAUSE_RESUME:
                    pause_close();
                    break;
                case PAUSE_UPGRADES:
                    play_finish();
                    shop_show(SHOP_ON_UPGRADES);
                    break;
                case PAUSE_RESTART:
                    play_finish();
                    level_play();
                    break;
                case PAUSE_MAIN_MENU:
                    play_finish();
                    title_show();
                    break;
                }
            break;
        case STATE_SHOP:
            switch (shop_step())
            {
            case SHOP_BEGIN:
                level = level_picked;
                level_play();
                break;
            case SHOP_TITLE:
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
                shop_show(SHOP_ON_LEVELS);
                break;
            case TITLE_NEW_GAME:
                if (save_exists)
                {
                    menu_close();
                    menu_open(&confirm_menu, CONFIRM_NO - 1, 0, 0);
                    game_state = STATE_CONFIRM;
                }
                else
                    new_game();
                break;
            }
            break;
        case STATE_CONFIRM:
            /* Esc is No. */
            switch (input_pressed & INPUT_PAUSE ? CONFIRM_NO : menu_step())
            {
            case CONFIRM_YES:
                DEBUG_LOG("new game\n");
                new_game();
                break;
            case CONFIRM_NO:
                menu_close();
                menu_open(&title_menu, TITLE_NEW_GAME - 1, 0, 0);
                game_state = STATE_TITLE;
                break;
            }
            break;
        }
        cursor_step();
    }
}
