/* A spike, not part of the game: random number generators on the 6502,
   for how fast they are and how even. Run its ROM on the hardware and
   read the console.

   Each generator is seeded once from the RIA's lrand, as the game would,
   and gives 16 bits a call. Its speed is how many calls it makes in
   RUN_MS by clock(), less the time the loop takes calling a generator
   that does nothing. Its evenness is from SAMPLES calls:
   - chi lo and chi hi, the chi-square of its low and high bytes over 256
     buckets, 255 degrees of freedom: about 210 to 300 is as even as a
     good generator, and far above is lumpy;
   - chi pair, the same of the top halves of the low bytes of each two
     calls running, 16 by 16 buckets, which shows one call leaning on the
     last;
   - runs, of the top bit of the low byte, the times it changes: about
     12800, give or take 80, and far off is streaky or too regular. */

#include <rp6502.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define RUN_MS 3000
#define SAMPLES 25600u /* 100 a bucket */

typedef uint16_t (*gen_t)(void);

/* None, for the time of the loop alone. */
static uint16_t gen_none(void)
{
    return 0;
}

/* The RIA's own, an OS call each time. */
static uint16_t gen_lrand(void)
{
    return (uint16_t)ria_attr_get(RIA_ATTR_LRAND);
}

/* The C library's, 15 bits: the high byte is its top 8. */
static uint16_t gen_rand(void)
{
    return (uint16_t)rand();
}

/* Marsaglia's xorshift on 16 bits, (7, 9, 8), as the game's chunks use. */
static uint16_t xs16;
static uint16_t gen_xorshift16(void)
{
    xs16 ^= xs16 << 7;
    xs16 ^= xs16 >> 9;
    xs16 ^= xs16 << 8;
    return xs16;
}

/* Marsaglia's xorshift on 32 bits, (13, 17, 5), its low 16. */
static uint32_t xs32;
static uint16_t gen_xorshift32(void)
{
    xs32 ^= xs32 << 13;
    xs32 ^= xs32 >> 17;
    xs32 ^= xs32 << 5;
    return (uint16_t)xs32;
}

/* A 16-bit Galois LFSR, taps 0xB400, the longest it goes, a bit a step,
   so 16 steps a call. */
static uint16_t lfsr;
static uint16_t gen_lfsr16(void)
{
    uint8_t i;

    for (i = 0; i < 16; i++)
        lfsr = (lfsr >> 1) ^ (-(lfsr & 1u) & 0xB400u);
    return lfsr;
}

/* A 32-bit LCG, Numerical Recipes's, its top 16 bits, as its low bits
   repeat quickly. */
static uint32_t lcg;
static uint16_t gen_lcg32(void)
{
    lcg = lcg * 1664525ul + 1013904223ul;
    return (uint16_t)(lcg >> 16);
}

typedef struct
{
    const char *name;
    gen_t gen;
    uint8_t high_shift; /* where its high byte starts */
} algorithm_t;

static const algorithm_t algorithms[] = {
    {"lrand", gen_lrand, 8},
    {"rand", gen_rand, 7},
    {"xorshift16", gen_xorshift16, 8},
    {"xorshift32", gen_xorshift32, 8},
    {"lfsr16", gen_lfsr16, 8},
    {"lcg32", gen_lcg32, 8},
};
#define ALGORITHMS (sizeof algorithms / sizeof *algorithms)

static uint16_t lo[256], hi[256], pairs[256];
static volatile uint16_t sink;

/* Nanoseconds a call, over RUN_MS. */
static uint32_t ns_per_call(gen_t gen)
{
    uint32_t calls = 0;
    clock_t start = clock(), now;

    do
    {
        uint8_t i = 0;
        do
            sink = gen();
        while (++i);
        calls += 256;
        now = clock();
    } while (now - start < RUN_MS);
    return (uint32_t)(now - start) * 1000000ul / calls;
}

static uint32_t chi(const uint16_t *counts, uint16_t expect)
{
    uint32_t sum = 0;
    uint16_t i;

    for (i = 0; i < 256; i++)
    {
        int32_t d = (int32_t)counts[i] - expect;
        sum += (uint32_t)(d * d);
    }
    return sum / expect;
}

int main(void)
{
    uint32_t base;
    uint8_t a;
    long seed = ria_attr_get(RIA_ATTR_LRAND);

    srand((unsigned)seed);
    xs16 = (uint16_t)seed | 1;
    xs32 = (uint32_t)seed | 1;
    lfsr = (uint16_t)(seed >> 16) | 1;
    lcg = (uint32_t)seed;
    printf("\nRandom number generators, at %ld kHz, seeded from lrand: %08lX\n",
           ria_attr_get(RIA_ATTR_PHI2_KHZ), (unsigned long)seed);
    printf("Speed: calls in %u ms, less the loop's own time.\n", RUN_MS);
    printf("Evenness: %u calls. Chi-square: about 210 to 300 is fine.\n", SAMPLES);
    printf("Runs of the low byte's top bit: about 12800, give or take 80.\n\n");
    base = ns_per_call(gen_none);
    printf("The loop alone: %lu.%lu us a call\n\n", base / 1000, base % 1000 / 100);
    printf("%-12s %9s %7s %7s %8s %7s\n", "", "us/call", "chi lo", "chi hi", "chi pair", "runs");
    for (a = 0; a < ALGORITHMS; a++)
    {
        const algorithm_t *alg = &algorithms[a];
        uint32_t ns = ns_per_call(alg->gen);
        uint16_t n, runs = 0, i;
        uint8_t last = 0, bit = 0;

        ns = ns > base ? ns - base : 0;
        for (i = 0; i < 256; i++)
            lo[i] = hi[i] = pairs[i] = 0;
        for (n = 0; n < SAMPLES; n++)
        {
            uint16_t r = alg->gen();
            uint8_t low = (uint8_t)r;

            lo[low]++;
            hi[(uint8_t)(r >> alg->high_shift)]++;
            if (n)
            {
                pairs[(last & 0xF0) | (low >> 4)]++;
                if ((low >> 7) != bit)
                    runs++;
            }
            last = low;
            bit = low >> 7;
        }
        printf("%-12s %5lu.%lu %7lu %7lu %8lu %7u\n", alg->name, ns / 1000, ns % 1000 / 100,
               chi(lo, SAMPLES / 256), chi(hi, SAMPLES / 256), chi(pairs, (SAMPLES - 1) / 256), runs + 1);
    }
    printf("\nDone.\n");
    return 0;
}
