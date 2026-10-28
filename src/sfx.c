#include "sfx.h"
#include "debug.h"
#include "xram.h"

/* Sound effects on the PSG. Each effect is a few notes, played one after
   another on a channel of its own, with a step of silence between notes so
   each starts its envelope anew. Effects take the channel that has been
   quiet longest, or the oldest effect's channel when every one is busy. */

typedef struct
{
    uint16_t freq;  /* Hz * 3 */
    int16_t slide;  /* added to freq each step */
    uint8_t steps;  /* the gate is held this long; 0 ends the effect */
    uint8_t wave;   /* PSG_WAVE_ | release rate */
    uint8_t attack; /* peak attenuation << 4 | attack rate */
    uint8_t decay;  /* sustain attenuation << 4 | decay rate */
} note_t;

#define NOTE(hz, slide, steps, wave, release, attack, decay) \
    {PSG_FREQ_HZ(hz), (slide) * 3, steps, (wave) | (release), attack, decay}
#define REST(steps) {PSG_FREQ_HZ(100), 0, steps, PSG_WAVE_SINE, 0xF0, 0xF0}
#define END {0, 0, 0, 0, 0, 0}

#define SQUARE PSG_WAVE_SQUARE
#define TRIANGLE PSG_WAVE_TRIANGLE
#define SAWTOOTH PSG_WAVE_SAWTOOTH
#define NOISE PSG_WAVE_NOISE

static const note_t paddle_notes[] = {NOTE(196, 0, 4, SQUARE, 2, 0x20, 0xF3), END};
static const note_t wall_notes[] = {NOTE(523, 0, 2, TRIANGLE, 1, 0x30, 0xF2), END};
static const note_t brick_notes[] = {NOTE(988, 0, 2, SQUARE, 1, 0x40, 0xF2), END};
static const note_t break_notes[] = {NOTE(2400, -20, 6, NOISE, 3, 0x20, 0xF4), END};
static const note_t nugget_notes[] = {
    NOTE(1319, 0, 2, TRIANGLE, 0, 0x50, 0x52),
    NOTE(1760, 0, 3, TRIANGLE, 3, 0x50, 0xF4),
    END,
};
static const note_t lost_notes[] = {NOTE(660, -15, 36, SQUARE, 4, 0x30, 0x34), END};
static const note_t low_notes[] = {
    NOTE(1047, 0, 5, SQUARE, 1, 0x40, 0x40),
    REST(3),
    NOTE(1047, 0, 5, SQUARE, 1, 0x40, 0x40),
    END,
};
static const note_t low_beep_notes[] = {NOTE(1047, 0, 4, SQUARE, 1, 0x60, 0x60), END};
static const note_t sputter_notes[] = {
    NOTE(1500, -10, 4, NOISE, 2, 0x30, 0xF3),
    REST(3),
    NOTE(1100, -10, 4, NOISE, 2, 0x30, 0xF3),
    REST(5),
    NOTE(800, -10, 6, NOISE, 3, 0x40, 0xF4),
    END,
};
static const note_t fall_notes[] = {NOTE(700, -18, 32, SAWTOOTH, 5, 0x30, 0x33), END};
static const note_t buy_notes[] = {
    NOTE(523, 0, 3, TRIANGLE, 1, 0x20, 0x20),
    NOTE(659, 0, 3, TRIANGLE, 1, 0x20, 0x20),
    NOTE(784, 0, 3, TRIANGLE, 1, 0x20, 0x20),
    NOTE(1047, 0, 8, TRIANGLE, 4, 0x20, 0xF6),
    END,
};
static const note_t move_notes[] = {NOTE(1568, 0, 1, SQUARE, 0, 0x60, 0xF1), END};
static const note_t rattle_notes[] = {NOTE(2093, 0, 1, SQUARE, 0, 0x70, 0xF1), END};
static const note_t snap_notes[] = {
    NOTE(3000, -60, 4, NOISE, 2, 0x20, 0xF3),
    NOTE(262, 0, 3, SQUARE, 3, 0x40, 0xF4),
    END,
};
static const note_t unlock_notes[] = {
    NOTE(1319, 0, 3, TRIANGLE, 1, 0x20, 0x20),
    NOTE(1760, 0, 3, TRIANGLE, 1, 0x20, 0x20),
    NOTE(2637, 0, 10, TRIANGLE, 5, 0x20, 0xF6),
    END,
};

static const note_t *const sounds[SFX_COUNT] = {
    paddle_notes, wall_notes, brick_notes, break_notes, nugget_notes, lost_notes,
    low_notes, low_beep_notes, sputter_notes, fall_notes, buy_notes, move_notes,
    rattle_notes, snap_notes, unlock_notes,
};

typedef struct
{
    const note_t *note; /* the note playing, or next; NULL when quiet */
    uint8_t left;       /* steps left of the note, 0 between notes */
    uint16_t freq;
    uint8_t pan;
    uint8_t quiet; /* steps since the effect ended, to 255 */
    uint8_t age;   /* steps since the effect began, to 255 */
} voice_t;

static voice_t voices[PSG_CHANNELS];

#define CHANNEL(i) (XRAM_PSG + (i) * sizeof(psg_channel_t))

static void note_start(uint8_t i)
{
    voice_t *v = &voices[i];
    const note_t *n = v->note;
    psg_channel_t c;

    v->freq = n->freq;
    v->left = n->steps;
    c.freq = n->freq;
    c.duty = 128;
    c.attack = n->attack;
    c.decay = n->decay;
    c.release_wave = n->wave;
    c.pan_gate = v->pan | PSG_GATE;
    c.reserved = 0;
    xram0_write(CHANNEL(i), &c, sizeof c);
}

static void gate_off(uint8_t i)
{
    xram0_poke8(CHANNEL(i) + offsetof(psg_channel_t, pan_gate), voices[i].pan);
}

/* Every channel quiet, then the PSG on. */
void sfx_init(void)
{
    uint8_t i;

    xram0_set(XRAM_PSG, 0, sizeof(psg_t));
    for (i = 0; i < PSG_CHANNELS; i++)
        voices[i].quiet = 255;
    xreg_ria_psg(XRAM_PSG);
}

/* Plays an effect from x across the screen, panned left to right. */
void sfx_play(uint8_t sound, int16_t x)
{
    uint8_t i, best = 0;
    int16_t pan = (x - SFX_CENTER) / 4;
    voice_t *v;

    for (i = 1; i < PSG_CHANNELS; i++)
    {
        voice_t *a = &voices[i], *b = &voices[best];
        if (!a->note && (b->note || a->quiet > b->quiet))
            best = i;
        else if (a->note && b->note && a->age > b->age)
            best = i;
    }
    v = &voices[best];
    v->pan = PSG_PAN(pan < -63 ? -63 : pan > 63 ? 63 : pan);
    v->age = 0;
    v->note = sounds[sound];
    /* It starts on the next step, so each note holds its gate for whole
       steps however late in a step it was played. A channel that was
       busy gets the step of silence first. */
    gate_off(best);
    v->left = 0;
    DEBUG_LOG("sfx %u\n", sound);
}

/* Steps every effect: notes slide, end, and the next begins. */
void sfx_step(void)
{
    uint8_t i;

    for (i = 0; i < PSG_CHANNELS; i++)
    {
        voice_t *v = &voices[i];
        if (!v->note)
        {
            if (v->quiet < 255)
                v->quiet++;
            continue;
        }
        if (v->age < 255)
            v->age++;
        if (!v->left)
        {
            note_start(i);
            continue;
        }
        if (--v->left == 0)
        {
            gate_off(i);
            if (!(++v->note)->steps)
            {
                v->note = 0;
                v->quiet = 0;
            }
            continue;
        }
        if (v->note->slide)
        {
            v->freq += v->note->slide;
            xram0_poke16(CHANNEL(i), v->freq);
        }
    }
}
