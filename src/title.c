#include "title.h"
#include "paddle.h"
#include "play.h"
#include "video.h"
#include "scene.h"
#include "xram.h"

/* The title screen, after the concept: rock all around, the logo at the
   top, the menu under it, and the paddle hovering at the bottom. */

#define LOGO_X 64 /* the logo is three 64x64 sprites side by side */
#define LOGO_Y 12
#define LOGO_SPRITE(i) (XRAM_MENU_SPRITES + (i) * sizeof(mode5_csprite_t))
#define LOGO_IMAGE(i) (XRAM_LOGO_IMAGES + (i) * sizeof(logo_image_t))

void title_open(void)
{
    uint8_t i;

    video_hide_sprites();
    scene_menu();
    video_rock();
    video_text_clear();
    for (i = 0; i < 3; i++)
    {
        sprite_set(LOGO_SPRITE(i), LOGO_IMAGE(i), XRAM_PALETTE_LOGO, MODE5_SIZE(64, 64));
        sprite_move(LOGO_SPRITE(i), LOGO_X + i * 64, LOGO_Y);
    }
    play_left = 0;
    play_right = SCREEN_W;
    paddle_start();
}

/* The flames still burn. */
void title_step(void)
{
    paddle_step(0);
}

void title_draw(void)
{
    paddle_draw();
}
