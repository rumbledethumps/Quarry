#include "upgrades.h"
#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "tuning.h"
#include "xram.h"

/* The tables are used and retained, so they stay whole in RAM for the
   tests to read: without, the compiler and the linker could do without
   one such as {1, 2, 3}, working its values out instead. */
__attribute__((used, retain)) static const uint8_t ball_counts[] = TUNE_BALLS;
__attribute__((used, retain)) static const uint16_t ball_costs[] = TUNE_BALL_COSTS;
__attribute__((used, retain)) static const uint8_t damages[] = TUNE_DAMAGES;
__attribute__((used, retain)) static const uint16_t damage_costs[] = TUNE_DAMAGE_COSTS;
__attribute__((used, retain)) static const uint8_t burns[] = TUNE_BURNS;
__attribute__((used, retain)) static const uint16_t burn_costs[] = TUNE_BURN_COSTS;
__attribute__((used, retain)) static const uint16_t speeds[] = TUNE_SPEEDS;
__attribute__((used, retain)) static const uint16_t speed_costs[] = TUNE_SPEED_COSTS;
__attribute__((used, retain)) static const uint8_t widths[] = TUNE_WIDTHS;
__attribute__((used, retain)) static const uint16_t width_costs[] = TUNE_WIDTH_COSTS;
__attribute__((used, retain)) static const uint8_t jets[] = TUNE_JETS;

/* The ranks after the first, one for each cost. */
#define BALL_RANKS (sizeof ball_costs / sizeof *ball_costs)
#define DAMAGE_RANKS (sizeof damage_costs / sizeof *damage_costs)
#define BURN_RANKS (sizeof burn_costs / sizeof *burn_costs)
#define SPEED_RANKS (sizeof speed_costs / sizeof *speed_costs)
#define WIDTH_RANKS (sizeof width_costs / sizeof *width_costs)

_Static_assert(BALL_RANKS == sizeof ball_counts / sizeof *ball_counts - 1,
               "TUNE_BALL_COSTS needs a cost for each count of balls after the first.");
_Static_assert(DAMAGE_RANKS == sizeof damages / sizeof *damages - 1,
               "TUNE_DAMAGE_COSTS needs a cost for each damage after the first.");
_Static_assert(BURN_RANKS == sizeof burns / sizeof *burns - 1,
               "TUNE_BURN_COSTS needs a cost for each burn after the first.");
_Static_assert(SPEED_RANKS == sizeof speeds / sizeof *speeds - 1,
               "TUNE_SPEED_COSTS needs a cost for each speed after the first.");
_Static_assert(WIDTH_RANKS == sizeof widths / sizeof *widths - 1,
               "TUNE_WIDTH_COSTS needs a cost for each width after the first.");
_Static_assert(BALL_RANKS <= UPGRADE_RANKS_MAX && DAMAGE_RANKS <= UPGRADE_RANKS_MAX &&
                   BURN_RANKS <= UPGRADE_RANKS_MAX && SPEED_RANKS <= UPGRADE_RANKS_MAX &&
                   WIDTH_RANKS <= UPGRADE_RANKS_MAX,
               "Too many ranks: 10 of each upgrade after the first at most.");
_Static_assert(sizeof jets == sizeof widths, "TUNE_JETS needs the jets of each width.");
_Static_assert(sizeof widths <= SLEDS, "SLEDS in xram.h needs a sled for each width.");
_Static_assert(BRICK_GOLD < 1 << (16 - COST_COLOR_SHIFT), "A cost's color fits its top bits.");

/* Each upgrade's costs, its ranks after the first, and its name for the
   log. */
static const uint16_t *const costs[UPGRADES] = {
    [UPGRADE_BALLS] = ball_costs,   [UPGRADE_DAMAGE] = damage_costs, [UPGRADE_EFFICIENCY] = burn_costs,
    [UPGRADE_SPEED] = speed_costs, [UPGRADE_WIDTH] = width_costs,
};
__attribute__((used, retain)) static const uint8_t ranks[UPGRADES] = {
    [UPGRADE_BALLS] = BALL_RANKS,   [UPGRADE_DAMAGE] = DAMAGE_RANKS, [UPGRADE_EFFICIENCY] = BURN_RANKS,
    [UPGRADE_SPEED] = SPEED_RANKS, [UPGRADE_WIDTH] = WIDTH_RANKS,
};
#ifndef NDEBUG
static const char *const names[UPGRADES] = {
    [UPGRADE_BALLS] = "balls", [UPGRADE_DAMAGE] = "damage", [UPGRADE_EFFICIENCY] = "efficiency",
    [UPGRADE_SPEED] = "speed", [UPGRADE_WIDTH] = "width",
};
#endif

uint8_t upgrade_ranks[UPGRADES];

/* The highest rank of an upgrade. */
uint8_t upgrades_max(uint8_t upgrade)
{
    return ranks[upgrade];
}

/* The next rank's cost as tuning.h has it, with its color, or 0 at the
   highest rank. */
static uint16_t next_cost(uint8_t upgrade)
{
    uint8_t rank = upgrade_ranks[upgrade];

    return rank < ranks[upgrade] ? costs[upgrade][rank] : 0;
}

/* The nuggets the next rank costs, 0 at the highest rank. */
uint16_t upgrades_cost(uint8_t upgrade)
{
    return COST_COUNT(next_cost(upgrade));
}

/* The color of the nuggets the next rank costs. */
uint8_t upgrades_cost_color(uint8_t upgrade)
{
    return COST_COLOR(next_cost(upgrade));
}

/* Buys the next rank if there are nuggets enough. Returns whether it did. */
uint8_t upgrades_buy(uint8_t upgrade)
{
    uint16_t cost = upgrades_cost(upgrade);
    uint8_t color = upgrades_cost_color(upgrade);

    if (!cost || nuggets[color] < cost)
        return 0;
    nuggets[color] -= cost;
    upgrade_ranks[upgrade]++;
    DEBUG_LOG("bought %s %u\n", names[upgrade], upgrade_ranks[upgrade]);
    return 1;
}

uint8_t upgrades_balls(void)
{
    return ball_counts[upgrade_ranks[UPGRADE_BALLS]];
}

uint8_t upgrades_balls_at(uint8_t rank)
{
    return ball_counts[rank];
}

uint8_t upgrades_width(void)
{
    return widths[upgrade_ranks[UPGRADE_WIDTH]];
}

uint8_t upgrades_width_at(uint8_t rank)
{
    return widths[rank];
}

uint8_t upgrades_jets_at(uint8_t rank)
{
    return jets[rank];
}

/* The sled's speed, in 1/256 px a step, from its px a second, to the
   nearest. */
uint16_t upgrades_speed(void)
{
    return ((uint32_t)speeds[upgrade_ranks[UPGRADE_SPEED]] * 256 + 30) / 60;
}

/* A rank's speed in px a second, as its panel shows it. */
uint16_t upgrades_speed_at(uint8_t rank)
{
    return speeds[rank];
}

uint8_t upgrades_damage(void)
{
    return damages[upgrade_ranks[UPGRADE_DAMAGE]];
}

uint8_t upgrades_damage_at(uint8_t rank)
{
    return damages[rank];
}

/* The fuel burned a step, in 1/600 L, which is tenths of a liter a
   second. */
uint8_t upgrades_burn(void)
{
    return burns[upgrade_ranks[UPGRADE_EFFICIENCY]];
}

uint8_t upgrades_burn_at(uint8_t rank)
{
    return burns[rank];
}
