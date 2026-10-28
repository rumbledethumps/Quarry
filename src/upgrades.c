#include "upgrades.h"
#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "tuning.h"
#include "xram.h"

static const uint8_t widths[] = TUNE_WIDTHS;
static const uint16_t width_costs[] = TUNE_WIDTH_COSTS;
static const uint16_t speeds[] = TUNE_SPEEDS;
static const uint16_t speed_costs[] = TUNE_SPEED_COSTS;
static const uint8_t damages[] = TUNE_DAMAGES;
static const uint16_t damage_costs[] = TUNE_DAMAGE_COSTS;
static const uint8_t jets[] = TUNE_JETS;

/* The ranks after the first, one for each cost. */
#define WIDTH_RANKS (sizeof width_costs / sizeof *width_costs)
#define SPEED_RANKS (sizeof speed_costs / sizeof *speed_costs)
#define DAMAGE_RANKS (sizeof damage_costs / sizeof *damage_costs)

_Static_assert(WIDTH_RANKS == sizeof widths / sizeof *widths - 1,
               "TUNE_WIDTH_COSTS needs a cost for each width after the first.");
_Static_assert(SPEED_RANKS == sizeof speeds / sizeof *speeds - 1,
               "TUNE_SPEED_COSTS needs a cost for each speed after the first.");
_Static_assert(DAMAGE_RANKS == sizeof damages / sizeof *damages - 1,
               "TUNE_DAMAGE_COSTS needs a cost for each damage after the first.");
_Static_assert(WIDTH_RANKS <= UPGRADE_RANKS_MAX && SPEED_RANKS <= 5 && DAMAGE_RANKS <= UPGRADE_RANKS_MAX,
               "Too many ranks: 10 widths, 5 speeds and 10 damages after the first at most.");
_Static_assert(sizeof jets == sizeof widths, "TUNE_JETS needs the jets of each width.");
_Static_assert(sizeof widths <= SLEDS, "SLEDS in xram.h needs a sled for each width.");

/* Each upgrade's costs, its ranks after the first, and its name for the
   log. */
static const uint16_t *const costs[UPGRADES] = {width_costs, speed_costs, damage_costs};
static const uint8_t ranks[UPGRADES] = {WIDTH_RANKS, SPEED_RANKS, DAMAGE_RANKS};
#ifndef NDEBUG
static const char *const names[UPGRADES] = {"width", "speed", "damage"};
#endif

uint8_t upgrade_ranks[UPGRADES];

/* The highest rank of an upgrade. */
uint8_t upgrades_max(uint8_t upgrade)
{
    return ranks[upgrade];
}

/* The cost of the next rank, in gray nuggets. 0 at the highest rank. */
uint16_t upgrades_cost(uint8_t upgrade)
{
    uint8_t rank = upgrade_ranks[upgrade];

    return rank < ranks[upgrade] ? costs[upgrade][rank] : 0;
}

/* Buys the next rank if there are nuggets enough. Returns whether it did. */
uint8_t upgrades_buy(uint8_t upgrade)
{
    uint16_t cost = upgrades_cost(upgrade);

    if (!cost || nuggets[BRICK_GRAY] < cost)
        return 0;
    nuggets[BRICK_GRAY] -= cost;
    upgrade_ranks[upgrade]++;
    DEBUG_LOG("bought %s %u\n", names[upgrade], upgrade_ranks[upgrade]);
    return 1;
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

uint16_t upgrades_speed(void)
{
    return speeds[upgrade_ranks[UPGRADE_SPEED]];
}

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
