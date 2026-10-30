#include "input.h"
#include "hidkeys.h"
#include "xram.h"

uint8_t input_held;
uint8_t input_pressed;
uint8_t shift_pressed;
uint8_t shift_letter;
uint8_t shift_number;

/* A held key repeats after REPEAT_DELAY steps, then every REPEAT_STEPS. */
#define REPEAT_DELAY 20
#define REPEAT_STEPS 6

static uint8_t shift_held;
static uint8_t shift_steps;
static uint16_t digits_held;  /* a bit for each number key, from 0 */
static uint16_t letters_held; /* and each letter of the top row */
static uint8_t typed;         /* the number typed while Shift is held */
static uint8_t typing;        /* whether one is */

/* The top row of letters, in order. */
static const uint8_t top_row[] = {HID_KEY_Q, HID_KEY_W, HID_KEY_E, HID_KEY_R, HID_KEY_T,
                                  HID_KEY_Y, HID_KEY_U, HID_KEY_I, HID_KEY_O, HID_KEY_P};
static uint8_t repeat_keys; /* the INPUT_ bits of the last press input_repeat() saw */
static uint8_t repeat_steps;

static void shift_read(const uint8_t *keys)
{
    uint16_t digits = 0, letters = 0;
    uint8_t held = 0, i;

    for (i = 0; i < 10; i++)
    {
        if (KEYBOARD_PRESSED(keys, i ? HID_KEY_1 + i - 1 : HID_KEY_0))
            digits |= 1u << i;
        if (KEYBOARD_PRESSED(keys, top_row[i]))
            letters |= 1u << i;
    }
    for (i = 0; i < 10; i++)
        if (digits & ~digits_held & 1u << i)
        {
            typed = typed % 10 * 10 + i;
            typing = 1;
        }
    shift_letter = 0;
    for (i = 10; i; i--)
        if (letters & ~letters_held & 1u << (i - 1))
            shift_letter = i;
    digits_held = digits;
    letters_held = letters;

    if (KEYBOARD_PRESSED(keys, HID_KEY_ARROW_RIGHT))
        held |= SHIFT_RIGHT;
    if (KEYBOARD_PRESSED(keys, HID_KEY_ARROW_LEFT))
        held |= SHIFT_LEFT;
    if (KEYBOARD_PRESSED(keys, HID_KEY_ARROW_UP))
        held |= SHIFT_UP;
    if (KEYBOARD_PRESSED(keys, HID_KEY_ARROW_DOWN))
        held |= SHIFT_DOWN;
    if (held != shift_held)
    {
        shift_pressed = held & ~shift_held;
        shift_steps = 0;
    }
    else if (held && ++shift_steps >= REPEAT_DELAY)
    {
        shift_pressed = held;
        shift_steps = REPEAT_DELAY - REPEAT_STEPS;
    }
    else
        shift_pressed = 0;
    shift_held = held;
}

/* Everything counts as held to begin with, so a key that is already down
   when the game starts, such as the Enter that loaded it, is not a press. */
void input_init(void)
{
    xreg_ria_keyboard(XRAM_KEYBOARD);
    xreg_ria_gamepad(XRAM_GAMEPAD);
    input_held = 0xFF;
}

/* One stick and one button. Keyboard from the key bitmap, so held keys
   work: arrows, WASD or the keypad to move, and Space, Enter or Ctrl for
   the button. Every connected gamepad: the d-pad merged with the left
   stick, and A, B, X or Y, which every pad has where you expect them,
   for the button, which launches. Esc, P or Pause, or Start or
   Select, is the menu. With Shift, the arrows, WASD and P are keys for
   testing instead. */
void input_read(void)
{
    uint8_t keys[sizeof(keyboard_t)];
    gamepad_t pads;
    uint8_t held = 0;
    uint8_t plain; /* no Shift */
    uint8_t i;

    xram0_read(keys, XRAM_KEYBOARD, sizeof keys);
    plain = !KEYBOARD_PRESSED(keys, HID_KEY_SHIFT_LEFT) &&
            !KEYBOARD_PRESSED(keys, HID_KEY_SHIFT_RIGHT);
    shift_number = 0;
    if (plain)
    {
        /* Letting Shift go gives the number typed. */
        if (typing)
            shift_number = typed;
        shift_held = shift_pressed = shift_letter = typed = typing = 0;
        digits_held = letters_held = 0;
    }
    else
        shift_read(keys);
    if ((plain && (KEYBOARD_PRESSED(keys, HID_KEY_A) || KEYBOARD_PRESSED(keys, HID_KEY_ARROW_LEFT))) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_4))
        held |= INPUT_LEFT;
    if ((plain && (KEYBOARD_PRESSED(keys, HID_KEY_D) || KEYBOARD_PRESSED(keys, HID_KEY_ARROW_RIGHT))) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_6))
        held |= INPUT_RIGHT;
    if ((plain && (KEYBOARD_PRESSED(keys, HID_KEY_W) || KEYBOARD_PRESSED(keys, HID_KEY_ARROW_UP))) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_8))
        held |= INPUT_UP;
    if ((plain && (KEYBOARD_PRESSED(keys, HID_KEY_S) || KEYBOARD_PRESSED(keys, HID_KEY_ARROW_DOWN))) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_2))
        held |= INPUT_DOWN;
    if (KEYBOARD_PRESSED(keys, HID_KEY_SPACE) ||
        KEYBOARD_PRESSED(keys, HID_KEY_ENTER) ||
        KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_ENTER) ||
        KEYBOARD_PRESSED(keys, HID_KEY_CONTROL_LEFT) ||
        KEYBOARD_PRESSED(keys, HID_KEY_CONTROL_RIGHT))
        held |= INPUT_LAUNCH | INPUT_CHOOSE;
    if (KEYBOARD_PRESSED(keys, HID_KEY_KEYPAD_0))
        held |= INPUT_LAUNCH;
    if (KEYBOARD_PRESSED(keys, HID_KEY_ESCAPE) ||
        (plain && KEYBOARD_PRESSED(keys, HID_KEY_P)) ||
        KEYBOARD_PRESSED(keys, HID_KEY_PAUSE))
        held |= INPUT_PAUSE;

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
            held |= INPUT_UP;
        if (dirs & GAMEPAD_DPAD_DOWN)
            held |= INPUT_DOWN;
        if (pad->btn0 & (GAMEPAD_BTN0_A | GAMEPAD_BTN0_B |
                         GAMEPAD_BTN0_X | GAMEPAD_BTN0_Y))
            held |= INPUT_LAUNCH | INPUT_CHOOSE;
        if (pad->btn1 & (GAMEPAD_BTN1_START | GAMEPAD_BTN1_SELECT))
            held |= INPUT_PAUSE;
    }

    input_pressed = held & ~input_held;
    input_held = held;
}

/* The INPUT_ bits pressed this step, or those of the last press it saw
   again, once they have been held REPEAT_DELAY steps and then every
   REPEAT_STEPS, for a screen that calls it each step it takes input. */
uint8_t input_repeat(void)
{
    if (input_pressed)
    {
        repeat_keys = input_pressed;
        repeat_steps = 0;
        return input_pressed;
    }
    if (!repeat_keys || (input_held & repeat_keys) != repeat_keys)
    {
        repeat_keys = 0;
        return 0;
    }
    if (++repeat_steps < REPEAT_DELAY)
        return 0;
    repeat_steps = REPEAT_DELAY - REPEAT_STEPS;
    return repeat_keys;
}

/* Forgets the last press, so a key held into another screen or question
   doesn't repeat there. */
void input_repeat_stop(void)
{
    repeat_keys = 0;
}
