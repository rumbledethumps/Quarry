#include <rp6502.h>
#include <string.h>
#include "bricks.h"
#include "debug.h"
#include "input.h"
#include "nuggets.h"
#include "play.h"
#include "tuning.h"
#include "video.h"

/* Steps after a stage ends before launch starts it again, so a press
   meant for the last ball doesn't skip the message. */
#define STAGE_OVER_WAIT 60

static uint8_t stage_over_wait;
static uint8_t stage_playing;

/* Lays out the stage, centers the playfield between the panels, and
   starts play with every ball. */
static void stage_start(void)
{
    int16_t width;

    bricks_layout();
    width = bricks_cols * BRICK_W;
    play_left = (SCREEN_W - width) / 2;
    play_right = play_left + width;
    video_walls(play_left, play_right);
    video_text_clear();
    bricks_start(play_left, TUNE_BRICKS_Y);
    nuggets_start(1, play_left - WALL_SIZE);
    play_start();
    stage_playing = 1;
    DEBUG_LOG("stage start\n");
}

static void text_centered(uint8_t row, const char *s)
{
    uint8_t center = (play_left + play_right) / 2 / 8;

    video_text(center - strlen(s) / 2, row, s, CLEAR);
}

static void stage_over(const char *message)
{
    text_centered(15, message);
    text_centered(17, "LAUNCH TO PLAY");
    stage_playing = 0;
    stage_over_wait = STAGE_OVER_WAIT;
}

static void wait_vsync(void)
{
    static uint8_t last;

    while (ria_vsync() == last)
        ;
    last = ria_vsync();
}

int main(void)
{
    /* The panel frames are line-drawing glyphs from code page 437. */
    ria_attr_set(437, RIA_ATTR_CODE_PAGE);
    video_init();
    input_init();
    play_init();
    stage_start();
    video_start();

    for (;;)
    {
        wait_vsync();
        play_draw();
        input_read();
        if (stage_playing)
        {
            switch (play_step())
            {
            case PLAY_CLEARED:
                stage_over("STAGE CLEAR");
                break;
            case PLAY_OUT:
                stage_over("OUT OF BALLS");
                break;
            case PLAY_NO_ENERGY:
                stage_over("OUT OF ENERGY");
                break;
            }
        }
        else
        {
            play_idle();
            if (stage_over_wait)
                stage_over_wait--;
            else if (input_pressed & INPUT_LAUNCH)
                stage_start();
        }
    }
}
