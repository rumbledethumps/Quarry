#include "save.h"
#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "play.h"
#include "upgrades.h"
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

/* One save, one file: the nugget counts of each color, the upgrade levels
   and the stages unlocked. It starts with a tag that names its layout, so
   a save of another layout is not read as this one. */
#define SAVE_PATH "SAVE:quarry.save"
#define SAVE_TAG "QRY1"

typedef struct
{
    char tag[4];
    uint16_t nuggets[BRICK_COLORS];
    uint8_t upgrades[UPGRADES];
    uint8_t stages_unlocked;
} save_t;

uint8_t save_exists;
uint8_t stages_unlocked = 1;

/* Reads the save into the game. Returns whether there was a good one; a
   missing, short or strange file is no save, and changes nothing. */
uint8_t save_load(void)
{
    save_t s;
    uint8_t i;
    int fd = open(SAVE_PATH, O_RDONLY);
    int n;

    if (fd < 0)
        return 0;
    n = read(fd, &s, sizeof s);
    close(fd);
    if (n != sizeof s || memcmp(s.tag, SAVE_TAG, sizeof s.tag) ||
        s.stages_unlocked < 1 || s.stages_unlocked > STAGES)
        return 0;
    for (i = 0; i < UPGRADES; i++)
        if (s.upgrades[i] > upgrades_max(i))
            return 0;
    memcpy(nuggets, s.nuggets, sizeof nuggets);
    memcpy(upgrade_levels, s.upgrades, sizeof upgrade_levels);
    stages_unlocked = s.stages_unlocked;
    save_exists = 1;
    DEBUG_LOG("loaded\n");
    return 1;
}

/* Writes the game to the save, with the nuggets still on their way to the
   panel counted, and waits until it is stored. */
void save_write(void)
{
    save_t s;
    uint8_t i;
    int fd;

    memcpy(s.tag, SAVE_TAG, sizeof s.tag);
    for (i = 0; i < BRICK_COLORS; i++)
    {
        uint16_t pending = play_pending(i);
        s.nuggets[i] = nuggets[i] > 0xFFFF - pending ? 0xFFFF : nuggets[i] + pending;
    }
    memcpy(s.upgrades, upgrade_levels, sizeof s.upgrades);
    s.stages_unlocked = stages_unlocked;
    fd = open(SAVE_PATH, O_WRONLY | O_CREAT | O_TRUNC);
    if (fd < 0)
    {
        DEBUG_LOG("save failed\n");
        return;
    }
    write(fd, &s, sizeof s);
    syncfs(fd);
    close(fd);
    save_exists = 1;
    DEBUG_LOG("saved\n");
}

/* Starts over: no nuggets, no upgrades, only stage 1, and replaces the
   save with that. */
void save_new_game(void)
{
    memset(nuggets, 0, sizeof nuggets);
    memset(upgrade_levels, 0, sizeof upgrade_levels);
    stages_unlocked = 1;
    save_write();
}
