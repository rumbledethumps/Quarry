/* Debug builds log game events to stdout, where emulator test scripts
   wait for them. Release builds log nothing. */

#ifndef DEBUG_H
#define DEBUG_H

#ifdef NDEBUG
#define DEBUG_LOG(...) ((void)0)
#else
#include <stdio.h>
#define DEBUG_LOG(...) printf(__VA_ARGS__)
#endif

#endif
