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
static const uint8_t jets[] = TUNE_JETS;

/* The ranks after the first, one for each cost. */
#define WIDTH_RANKS (sizeof width_costs / sizeof *width_costs)
#define SPEED_RANKS (sizeof speed_costs / sizeof *speed_costs)

_Static_assert(WIDTH_RANKS == sizeof widths / sizeof *widths - 1,
               "TUNE_WIDTH_COSTS needs a cost for each width after the first.");
_Static_assert(SPEED_RANKS == sizeof speeds / sizeof *speeds - 1,
               "TUNE_SPEED_COSTS needs a cost for each speed after the first.");
_Static_assert(WIDTH_RANKS <= UPGRADE_RANKS_MAX && SPEED_RANKS <= 5,
               "Too many ranks: 10 widths and 5 speeds after the first at most.");
_Static_assert(sizeof jets == sizeof widths, "TUNE_JETS needs the jets of each width.");
_Static_assert(sizeof widths <= SLEDS, "SLEDS in xram.h needs a sled for each width.");

uint8_t upgrade_ranks[UPGRADES];

/* The highest rank of an upgrade. */
uint8_t upgrades_max(uint8_t upgrade)
{
    return upgrade == UPGRADE_WIDTH ? WIDTH_RANKS : SPEED_RANKS;
}

/* The cost of the next rank, in gray nuggets. 0 at the highest rank. */
uint16_t upgrades_cost(uint8_t upgrade)
{
    uint8_t rank = upgrade_ranks[upgrade];

    if (rank >= upgrades_max(upgrade))
        return 0;
    return upgrade == UPGRADE_WIDTH ? width_costs[rank] : speed_costs[rank];
}

/* Buys the next rank if there are nuggets enough. Returns whether it did. */
uint8_t upgrades_buy(uint8_t upgrade)
{
    uint16_t cost = upgrades_cost(upgrade);

    if (!cost || nuggets[BRICK_GRAY] < cost)
        return 0;
    nuggets[BRICK_GRAY] -= cost;
    upgrade_ranks[upgrade]++;
    DEBUG_LOG("bought %s %u\n", upgrade == UPGRADE_WIDTH ? "width" : "speed",
              upgrade_ranks[upgrade]);
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
