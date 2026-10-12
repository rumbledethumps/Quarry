#include "input.h"
#include "hidkeys.h"
#include "xram.h"

uint8_t input_held;
uint8_t input_pressed;

/* Everything counts as held to begin with, so a key that is already down
   when the game starts, such as the Enter that loaded it, is not a press. */
void input_init(void)
{
    xreg_ria_keyboard(XRAM_KEYBOARD);
    xreg_ria_gamepad(XRAM_GAMEPAD);
    input_held = 0xFF;
}

/* Keyboard from the key bitmap, so held keys work, and every connected
   gamepad: the d-pad merged with the left stick, and A, B, X or Y to
   launch and choose. Up launches too. */
void input_read(void)
{
    uint8_t keys[sizeof(keyboard_t)];
    gamepad_t pads;
    uint8_t held = 0;
    uint8_t i;

    xram0_read(keys, XRAM_KEYBOARD, sizeof keys);
    if (KEYBOARD_PRESSED(keys, HID_KEY_A) ||
        KEYBOARD_PRESSED(keys, HID_KEY_ARROW_LEFT) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_4))
        held |= INPUT_LEFT;
    if (KEYBOARD_PRESSED(keys, HID_KEY_D) ||
        KEYBOARD_PRESSED(keys, HID_KEY_ARROW_RIGHT) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_6))
        held |= INPUT_RIGHT;
    if (KEYBOARD_PRESSED(keys, HID_KEY_W) ||
        KEYBOARD_PRESSED(keys, HID_KEY_ARROW_UP) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_8))
        held |= INPUT_UP | INPUT_LAUNCH;
    if (KEYBOARD_PRESSED(keys, HID_KEY_S) ||
        KEYBOARD_PRESSED(keys, HID_KEY_ARROW_DOWN) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_2))
        held |= INPUT_DOWN;
    if (KEYBOARD_PRESSED(keys, HID_KEY_SPACE) ||
        KEYBOARD_PRESSED(keys, HID_KEY_ENTER) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_ENTER))
        held |= INPUT_LAUNCH | INPUT_CHOOSE;
    if (KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_0))
        held |= INPUT_LAUNCH;

    xram0_read(&pads, XRAM_GAMEPAD, sizeof pads);
    for (i = 0; i < GAMEPAD_PLAYERS; i++)
    {
        const gamepad_player_t *pad = &pads.player[i];
        uint8_t dirs;
        if (!(pad->dpad & GAMEPAD_FEAT_CONNECTED))
            continue;
        dirs = pad->dpad | pad->sticks;
        if (dirs & GAMEPAD_DPAD_LEFT)
            held |= INPUT_LEFT;
        if (dirs & GAMEPAD_DPAD_RIGHT)
            held |= INPUT_RIGHT;
        if (dirs & GAMEPAD_DPAD_UP)
            held |= INPUT_UP | INPUT_LAUNCH;
        if (dirs & GAMEPAD_DPAD_DOWN)
            held |= INPUT_DOWN;
        if (pad->btn0 & (GAMEPAD_BTN0_A | GAMEPAD_BTN0_B |
                         GAMEPAD_BTN0_X | GAMEPAD_BTN0_Y))
            held |= INPUT_LAUNCH | INPUT_CHOOSE;
    }

    input_pressed = held & ~input_held;
    input_held = held;
}
