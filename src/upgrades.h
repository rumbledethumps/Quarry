#ifndef UPGRADES_H
#define UPGRADES_H

#include <stdint.h>

#define UPGRADE_WIDTH 0
#define UPGRADE_SPEED 1
#define UPGRADE_DAMAGE 2
#define UPGRADES 3
#define UPGRADE_RANKS_MAX 10 /* ranks after the first, of any upgrade */

/* The rank bought of each upgrade, 0 before any. */
extern uint8_t upgrade_ranks[UPGRADES];

uint8_t upgrades_max(uint8_t upgrade);
uint16_t upgrades_cost(uint8_t upgrade);
uint8_t upgrades_buy(uint8_t upgrade);
uint8_t upgrades_width(void);
uint8_t upgrades_width_at(uint8_t rank);
uint8_t upgrades_jets_at(uint8_t rank);
uint16_t upgrades_speed(void);
uint16_t upgrades_speed_at(uint8_t rank);
uint8_t upgrades_damage(void);
uint8_t upgrades_damage_at(uint8_t rank);

#endif
