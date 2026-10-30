#include "talk.h"
#include "cursor.h"
#include "debug.h"
#include "input.h"
#include "menu.h"
#include "save.h"
#include "scene.h"
#include "video.h"
#include "xram.h"

/* A dwarf with something to say, when a screen opens. He comes up from
   the foot of the screen, in a lower corner, as his bubble comes in from
   the other side, the two meeting as they stop, with what he says already
   in it. Half a second later the OK shows, with the cursor round it, and
   the button sends his bubble back the way it came, and his next comes in
   the same way while he stays, or after his last sends them both back. While he talks the screen under
   him takes no input, and the cursor is off until each OK shows, and off
   again when it is pressed. More can wait their turn, each coming in as
   the last goes. A talk of TALK_STAYS has no OK: he stays, and the screen
   under him keeps the input and the cursor, until another talk takes his
   place or the screen goes. He and his bubble are in the menus' place, so
   the menus' tiles load again once the last has gone. A bubble can have
   the big coin in it, which comes and goes with it, on a level. */

#define QUEUE 4
#define IN_STEPS 18
#define OK_STEPS 30 /* half a second */
#define OUT_STEPS 12


#define DWARF(i) (XRAM_DWARF_SPRITES + (i) * sizeof(mode5_csprite_t))

/* How far from where they stop he and his bubble are, in 1/256 of the
   way from off the screen, for each step coming in, fast and then
   settling, and going, slow and then faster. */
static const uint16_t coming[IN_STEPS + 1] = {256, 219, 187, 157, 131, 108, 88, 70, 55, 43,
                                              32,  23,  16,  11,  7,   4,   2,  1,  0};
static const uint16_t going[OUT_STEPS + 1] = {0, 2, 7, 16, 28, 44, 64, 87, 114, 144, 178, 215, 256};

/* Each talk's dwarf, its first bubble, and how many it has, and its bit
   of talks_seen, if it is shown once. */
static const uint8_t talks[TALKS][3] = TALK_TABLE;
static const uint8_t seen[TALKS] = TALK_SEEN;

uint8_t talk_state;
static uint8_t queue[QUEUE], queued;
static uint8_t showing; /* the talk up, while talk_state isn't TALK_OFF */
static uint8_t stays;   /* whether it is of TALK_STAYS */
static uint8_t once;    /* the seen bits of the talks waiting or up that talk_once() asked for */
static uint8_t said;    /* the bubble up, of ROM:bubbles */
static uint8_t to_say;  /* his bubbles after it */
static uint8_t steps;
static uint16_t away;        /* his, as in coming and going */
static uint16_t bubble_away; /* his bubble's */
static uint8_t big_coin;     /* whether the bubble up has the big coin in it */
static dwarf_head_t dwarf;   /* his, as it loaded */
static bubble_head_t bubble; /* the bubble's */

/* The talk, after any already waiting, unless it is up or waiting
   already. Returns whether it waits now. */
static uint8_t queue_add(uint8_t talk)
{
    uint8_t i;

    if (queued == QUEUE || (talk_state != TALK_OFF && showing == talk))
        return 0;
    for (i = 0; i < queued; i++)
        if (queue[i] == talk)
            return 0;
    queue[queued++] = talk;
    return 1;
}

/* The talk, as often as it is asked for. */
void talk_queue(uint8_t talk)
{
    queue_add(talk);
}

/* The talk, unless the player has seen it. It counts as seen once its
   last OK is pressed, and the save keeps that the next time the game
   saves. */
void talk_once(uint8_t talk)
{
    uint8_t bit = seen[talk - 1];

    if (!(talks_seen & bit) && queue_add(talk))
        once |= bit;
}

/* The talk of the coin for the first clear of a level: its own, or the
   first level's for a level past them. */
uint8_t talk_coin(uint8_t level)
{
    return level && level <= TALK_COINS ? TALK_COIN1 + level - 1 : TALK_COIN1;
}

/* Whether a dwarf is talking, or about to. */
uint8_t talk_busy(void)
{
    return talk_state != TALK_OFF || queued;
}

/* Whether the last dwarf is going, with none to follow. */
uint8_t talk_leaving(void)
{
    return talk_state == TALK_OUT && !queued;
}

/* The bubble on plane 2's fill at x, in the menus' place. */
static void bubble_config(int16_t x)
{
    mode2_config_t config;

    config.x_wrap = false;
    config.y_wrap = false;
    config.x_pos_px = x;
    config.y_pos_px = bubble.y;
    config.width_tiles = BUBBLE_COLS;
    config.height_tiles = bubble.rows;
    config.xram_data_ptr = XRAM_BUBBLE_MAP;
    config.xram_palette_ptr = XRAM_BUBBLE_PALETTE;
    config.xram_tile_ptr = XRAM_BUBBLE_TILES;
    xram0_write(XRAM_TALK_CONFIG, &config, sizeof config);
}

/* The bubble said loads off the screen, and talk_draw() brings it back,
   with the big coin, if it has it. */
static void bubble_load(void)
{
    bubble_config(SCREEN_W);
    if (big_coin)
        sprite_hide(XRAM_BIG_COIN_SPRITE);
    scene_bubble(said);
    xram0_read(&bubble, XRAM_TALK_BUBBLE, sizeof bubble);
    bubble_config(SCREEN_W);
    big_coin = bubble.coin_y && scene_big_coin();
    if (big_coin)
        sprite_set(XRAM_BIG_COIN_SPRITE, XRAM_BIG_COIN_IMAGE, XRAM_PALETTE_SLED, MODE5_SIZE(BIG_COIN_SIZE, BIG_COIN_SIZE));
}

/* The next talk comes in from off the screen. The cursor goes, but for
   one that stays, and the bubble takes the menus' place on plane 2, off
   the screen, before its art loads over the menus'. */
static void talk_start(void)
{
    const uint8_t *talk;
    uint8_t i;

    showing = queue[0];
    talk = talks[showing - 1];
    stays = TALK_STAYS >> (showing - 1) & 1;
    if (!stays)
    {
        cursor_hide();
        menu_close(); /* he takes the menus' place, so any menu goes */
    }
    bubble.rows = BUBBLE_ROWS;
    bubble_config(SCREEN_W);
    video_talk();
    scene_dwarf(talk[0]);
    said = talk[1];
    to_say = talk[2] - 1;
    bubble_load();
    DEBUG_LOG("talk %u\n", showing);
    for (i = 1; i < queued; i++)
        queue[i - 1] = queue[i];
    queued--;
    xram0_read(&dwarf, XRAM_TALK_DWARF, sizeof dwarf);
    for (i = 0; i < DWARF_PIECES; i++)
        if (i < dwarf.pieces)
            sprite_set(DWARF(i), XRAM_DWARF_IMAGES + dwarf.piece[i].image, XRAM_DWARF_PALETTE, dwarf.piece[i].size);
        else
            sprite_hide(DWARF(i));
    talk_state = TALK_IN;
    steps = 0;
    away = bubble_away = coming[0];
}

/* The last talk is over: the dwarf goes, and the menus come back. */
static void talk_end(void)
{
    uint8_t i;

    for (i = 0; i < DWARF_PIECES; i++)
        sprite_hide(DWARF(i));
    if (big_coin)
        sprite_hide(XRAM_BIG_COIN_SPRITE);
    big_coin = 0;
    scene_menus();
    video_text_clear();
    video_menus();
    talk_state = TALK_OFF;
    DEBUG_LOG("talk over\n");
}

/* Returns whether a dwarf is talking and takes the input from the screen
   under him, which one that stays doesn't. */
uint8_t talk_step(void)
{
    switch (talk_state)
    {
    case TALK_OFF:
        if (!queued)
            return 0;
        talk_start();
        break;
    case TALK_IN:
        /* He comes in with his first bubble, and stays for the rest. */
        bubble_away = coming[++steps];
        if (away)
            away = bubble_away;
        if (steps == IN_STEPS)
        {
            talk_state = TALK_WAIT;
            steps = 0;
        }
        break;
    case TALK_WAIT:
        if (stays)
        {
            if (queued)
            {
                talk_state = TALK_OUT;
                steps = 0;
            }
        }
        else if (++steps == OK_STEPS)
        {
            /* The cursor goes round the OK's letters, 14 px across and 7
               down from a pixel into its cells, 4 px clear of them all
               round. */
            int16_t left = bubble.x + bubble.ok_col * 8 - 4, top = bubble.y + bubble.ok_row * 8 - 5;

            xram0_write(XRAM_BUBBLE_MAP + bubble.ok_row * BUBBLE_COLS + bubble.ok_col, bubble.ok_tiles, 2);
            cursor_place(left, top, left + 24, top + 17);
            talk_state = TALK_READY;
        }
        break;
    case TALK_READY:
        if (input_pressed & INPUT_CHOOSE)
        {
            uint8_t bit = seen[showing - 1];

            cursor_hide();
            steps = 0;
            if (to_say)
            {
                talk_state = TALK_NEXT;
                break;
            }
            if (once & bit)
            {
                talks_seen |= bit;
                once &= ~bit;
            }
            talk_state = TALK_OUT;
        }
        break;
    case TALK_NEXT:
        /* Once his bubble is off the screen, his next comes in. */
        if (steps == OUT_STEPS)
        {
            said++;
            to_say--;
            bubble_load();
            talk_state = TALK_IN;
            steps = 0;
            DEBUG_LOG("bubble %u\n", said);
        }
        else
            bubble_away = going[++steps];
        break;
    case TALK_OUT:
        /* Once they are off the screen, the next comes in, or the menus
           come back. */
        if (steps == OUT_STEPS)
        {
            if (queued)
                talk_start();
            else
                talk_end();
        }
        else
            away = bubble_away = going[++steps];
        break;
    }
    return !stays;
}

/* The talk up goes at once, with the screen it was on, and none waits. */
void talk_stop(void)
{
    queued = 0;
    once = 0;
    if (talk_state != TALK_OFF)
        talk_end();
}

/* At the start of a frame: the dwarf and his bubble where they got to,
   the bubble coming from the side of the screen away from him. */
void talk_draw(void)
{
    uint8_t i;
    int16_t y, x;

    if (talk_state == TALK_OFF)
        return;
    y = dwarf.y + (int16_t)((int32_t)(SCREEN_H - dwarf.y) * away >> 8);
    for (i = 0; i < dwarf.pieces; i++)
        sprite_move(DWARF(i), dwarf.x + dwarf.piece[i].x, y + dwarf.piece[i].y);
    if (bubble.x < dwarf.x)
        x = bubble.x - (int16_t)((int32_t)(bubble.x + bubble.cols * 8) * bubble_away >> 8);
    else
        x = bubble.x + (int16_t)((int32_t)(SCREEN_W - bubble.x) * bubble_away >> 8);
    xram0_poke16(XRAM_TALK_CONFIG + offsetof(mode2_config_t, x_pos_px), x);
    if (big_coin)
        sprite_move(XRAM_BIG_COIN_SPRITE, x + bubble.coin_x, bubble.y + bubble.coin_y);
}
