#ifndef UPGRADES_H
#define UPGRADES_H

#include <stdint.h>

/* The upgrades, in the order of their panels on the rail. */
#define UPGRADE_BALLS 0
#define UPGRADE_DAMAGE 1
#define UPGRADE_EFFICIENCY 2
#define UPGRADE_SPEED 3
#define UPGRADE_WIDTH 4
#define UPGRADES 5
#define UPGRADE_RANKS_MAX 10 /* ranks after the first, of any upgrade */

/* A cost of tuning.h is up to COST_PARTS parts, each a count of nuggets,
   with their color, of bricks.h, in its top bits: gray unless it says
   another, as RED(4). The parts it doesn't use are 0. */
#define COST_PARTS 3
#define COST_COLOR_SHIFT 12
#define COST_COUNT(part) ((part) & ((1u << COST_COLOR_SHIFT) - 1))
#define COST_COLOR(part) ((part) >> COST_COLOR_SHIFT)

/* The rank bought of each upgrade, 0 before any. */
extern uint8_t upgrade_ranks[UPGRADES];

uint8_t upgrades_max(uint8_t upgrade);
const uint16_t *upgrades_cost(uint8_t upgrade);
uint16_t upgrades_cost_in(uint8_t upgrade, uint8_t color);
uint8_t upgrades_buy(uint8_t upgrade);
uint8_t upgrades_balls(void);
uint8_t upgrades_balls_at(uint8_t rank);
uint8_t upgrades_width(void);
uint8_t upgrades_width_at(uint8_t rank);
uint8_t upgrades_jets_at(uint8_t rank);
uint16_t upgrades_speed(void);
uint16_t upgrades_speed_at(uint8_t rank);
uint8_t upgrades_damage(void);
uint8_t upgrades_damage_at(uint8_t rank);
uint8_t upgrades_burn(void);
uint8_t upgrades_burn_at(uint8_t rank);

#endif
