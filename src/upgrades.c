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

/* The levels after the first, one for each cost. */
#define WIDTH_LEVELS (sizeof width_costs / sizeof *width_costs)
#define SPEED_LEVELS (sizeof speed_costs / sizeof *speed_costs)

_Static_assert(WIDTH_LEVELS == sizeof widths / sizeof *widths - 1,
               "TUNE_WIDTH_COSTS needs a cost for each width after the first.");
_Static_assert(SPEED_LEVELS == sizeof speeds / sizeof *speeds - 1,
               "TUNE_SPEED_COSTS needs a cost for each speed after the first.");
_Static_assert(WIDTH_LEVELS <= UPGRADE_LEVELS_MAX && SPEED_LEVELS <= 5,
               "Too many levels: 10 widths and 5 speeds after the first at most.");
_Static_assert(sizeof jets == sizeof widths, "TUNE_JETS needs the jets of each width.");
_Static_assert(sizeof widths <= SLEDS, "SLEDS in xram.h needs a sled for each width.");

uint8_t upgrade_levels[UPGRADES];

/* The highest level of an upgrade. */
uint8_t upgrades_max(uint8_t upgrade)
{
    return upgrade == UPGRADE_WIDTH ? WIDTH_LEVELS : SPEED_LEVELS;
}

/* The cost of the next level, in white nuggets. 0 at the highest level. */
uint16_t upgrades_cost(uint8_t upgrade)
{
    uint8_t level = upgrade_levels[upgrade];

    if (level >= upgrades_max(upgrade))
        return 0;
    return upgrade == UPGRADE_WIDTH ? width_costs[level] : speed_costs[level];
}

/* Buys the next level if there are nuggets enough. Returns whether it did. */
uint8_t upgrades_buy(uint8_t upgrade)
{
    uint16_t cost = upgrades_cost(upgrade);

    if (!cost || nuggets[BRICK_WHITE] < cost)
        return 0;
    nuggets[BRICK_WHITE] -= cost;
    upgrade_levels[upgrade]++;
    DEBUG_LOG("bought %s %u\n", upgrade == UPGRADE_WIDTH ? "width" : "speed",
              upgrade_levels[upgrade]);
    return 1;
}

uint8_t upgrades_width(void)
{
    return widths[upgrade_levels[UPGRADE_WIDTH]];
}

uint8_t upgrades_width_at(uint8_t level)
{
    return widths[level];
}

uint8_t upgrades_jets_at(uint8_t level)
{
    return jets[level];
}

uint16_t upgrades_speed(void)
{
    return speeds[upgrade_levels[UPGRADE_SPEED]];
}
