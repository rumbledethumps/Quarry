#include "upgrades.h"
#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "tuning.h"

static const uint8_t widths[] = TUNE_WIDTHS;
static const uint16_t width_costs[] = TUNE_WIDTH_COSTS;
static const uint16_t speeds[] = TUNE_SPEEDS;
static const uint16_t speed_costs[] = TUNE_SPEED_COSTS;

_Static_assert(sizeof width_costs / sizeof *width_costs == sizeof widths / sizeof *widths - 1,
               "TUNE_WIDTH_COSTS needs a cost for each width after the first.");
_Static_assert(sizeof speed_costs / sizeof *speed_costs == sizeof speeds / sizeof *speeds - 1,
               "TUNE_SPEED_COSTS needs a cost for each speed after the first.");
_Static_assert(sizeof width_costs / sizeof *width_costs <= UPGRADE_LEVELS_MAX &&
                   sizeof speed_costs / sizeof *speed_costs <= 5,
               "Too many levels: 6 widths and 5 speeds after the first at most.");

uint8_t upgrade_levels[UPGRADES];

/* The highest level of an upgrade. */
uint8_t upgrades_max(uint8_t upgrade)
{
    return upgrade == UPGRADE_WIDTH ? sizeof width_costs / sizeof *width_costs
                                    : sizeof speed_costs / sizeof *speed_costs;
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

uint16_t upgrades_speed(void)
{
    return speeds[upgrade_levels[UPGRADE_SPEED]];
}
