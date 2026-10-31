#include "save.h"
#include "bricks.h"
#include "debug.h"
#include "nuggets.h"
#include "play.h"
#include "upgrades.h"
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

/* One save, one file: the nugget counts of each color, the coins, the
   upgrade ranks, the levels cleared, the level picked to play, the
   highest level the upgrade screen has shown open, the talks of the
   dwarves already seen, and the lines of the counts reached. It starts
   with a tag that names its layout, so a save of another layout is not
   read as this one. */
#define SAVE_PATH "SAVE:quarry.save"
#define SAVE_TAG "QRY9"

typedef struct
{
    char tag[4];
    uint16_t nuggets[BRICK_COLORS];
    uint16_t coins;
    uint8_t upgrades[UPGRADES];
    uint8_t levels_cleared;
    uint8_t level_picked;
    uint8_t levels_shown;
    uint8_t talks_seen;
    uint8_t counts_shown;
} save_t;

#define SAVE_BYTES sizeof(save_t) /* for tests/saves.py */

uint8_t save_exists;
uint8_t levels_cleared;
uint8_t level_picked = 1;
uint8_t levels_shown = 1;
uint8_t talks_seen;

/* The levels that can be played: every one cleared, and the next. */
uint8_t save_levels_open(void)
{
    return levels_cleared < LEVELS ? levels_cleared + 1 : LEVELS;
}

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
    if (n != sizeof s || memcmp(s.tag, SAVE_TAG, sizeof s.tag) || s.levels_cleared > LEVELS ||
        s.level_picked < 1 || s.level_picked > LEVELS || s.level_picked > s.levels_cleared + 1 ||
        s.levels_shown < 1 || s.levels_shown > LEVELS)
        return 0;
    for (i = 0; i < UPGRADES; i++)
        if (s.upgrades[i] > upgrades_max(i))
            return 0;
    memcpy(nuggets, s.nuggets, sizeof nuggets);
    coins = s.coins;
    memcpy(upgrade_ranks, s.upgrades, sizeof upgrade_ranks);
    levels_cleared = s.levels_cleared;
    level_picked = s.level_picked;
    levels_shown = s.levels_shown;
    talks_seen = s.talks_seen;
    counts_shown = s.counts_shown;
    save_exists = 1;
    DEBUG_LOG("loaded\n");
    return 1;
}

/* Writes the game to the save, with the nuggets still on their way to the
   panel counted, and their lines shown, and waits until it is stored. */
void save_write(void)
{
    save_t s;
    uint8_t i;
    int fd;

    memcpy(s.tag, SAVE_TAG, sizeof s.tag);
    s.counts_shown = counts_shown;
    for (i = 0; i < BRICK_COLORS; i++)
    {
        uint16_t pending = play_pending(i);
        s.nuggets[i] = nuggets[i] > 0xFFFF - pending ? 0xFFFF : nuggets[i] + pending;
        if (pending)
            s.counts_shown |= 1 << i;
    }
    s.coins = coins;
    memcpy(s.upgrades, upgrade_ranks, sizeof s.upgrades);
    s.levels_cleared = levels_cleared;
    s.level_picked = level_picked;
    s.levels_shown = levels_shown;
    s.talks_seen = talks_seen;
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

/* No nuggets, no coins, no upgrades, no level cleared, level 1 picked and
   shown open, no talk seen and no line of the counts. */
static void start_over(void)
{
    memset(nuggets, 0, sizeof nuggets);
    coins = 0;
    memset(upgrade_ranks, 0, sizeof upgrade_ranks);
    levels_cleared = 0;
    level_picked = 1;
    levels_shown = 1;
    talks_seen = 0;
    counts_shown = 0;
}

/* Starts over, and replaces the save with that. */
void save_new_game(void)
{
    start_over();
    save_write();
}

/* Deletes the save, and starts over, with no save until the game writes
   one. unlink() of a file on SAVE: fails, with ENODEV, so it empties the
   file, and an empty file is no save. */
void save_delete(void)
{
    int fd = open(SAVE_PATH, O_WRONLY | O_CREAT | O_TRUNC);

    if (fd >= 0)
    {
        syncfs(fd);
        close(fd);
    }
    start_over();
    save_exists = 0;
    DEBUG_LOG("deleted\n");
}
