cmake_minimum_required(VERSION 3.28)

include(${CMAKE_CURRENT_LIST_DIR}/tools/rp6502.cmake)

project(QUARRY C CXX ASM)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Converts art/<png> into <output> in the build folder with art/png2bin.py.
function(quarry_art output mode png)
    add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${output}
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/art/png2bin.py ${mode} ${ARGN}
            ${CMAKE_CURRENT_SOURCE_DIR}/art/${png}
            ${CMAKE_CURRENT_BINARY_DIR}/${output}
        DEPENDS art/png2bin.py art/${png}
        VERBATIM
    )
endfunction()

quarry_art(palettes.bin palette palettes.png)
quarry_art(brick.bin image brick.png)
quarry_art(break.bin image break.png --tile 24x16)
quarry_art(nugget.bin image nugget.png)
quarry_art(ball.bin image ball.png)
quarry_art(jet.bin image jet.png --tile 8x12)
quarry_art(smoke.bin image smoke.png --tile 8x8)
quarry_art(energy.bin image energy.png --tile 8x8)
quarry_art(logo.bin image logo.png --tile 64x64)
quarry_art(digits.bin image digits.png --tile 8x12)
quarry_art(machine.bin image machine.png)
quarry_art(coin.bin image coin.png)
quarry_art(cursor.bin image cursor.png)

# The textures behind a stage, one for each seed, as ROM:texture1 and on,
# and each curtain set of art/curtains/, as ROM:curtain1 and on.
set(QUARRY_TEXTURE_SEEDS 7 11 23 42)
set(QUARRY_TEXTURES)
foreach(seed IN LISTS QUARRY_TEXTURE_SEEDS)
    list(LENGTH QUARRY_TEXTURES n)
    math(EXPR n "${n} + 1")
    add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/texture${n}.bin
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/art/texture.py ${CMAKE_CURRENT_BINARY_DIR}/texture${n}.bin
            --seed ${seed} --preview ${CMAKE_CURRENT_BINARY_DIR}/texture${n}.png
        DEPENDS art/texture.py art/rd2png.py art/png2bin.py art/palettes.png
        VERBATIM
    )
    list(APPEND QUARRY_TEXTURES texture${n})
endforeach()
set(QUARRY_CURTAIN_SETS 4)
foreach(n RANGE 1 ${QUARRY_CURTAIN_SETS})
    add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/curtain${n}.bin
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/art/curtain.py ${CMAKE_CURRENT_SOURCE_DIR}/art/curtains/curtain-${n}.png
            ${CMAKE_CURRENT_BINARY_DIR}/curtain${n}.bin --preview ${CMAKE_CURRENT_BINARY_DIR}/curtain${n}.png
        DEPENDS art/curtain.py art/rd2png.py art/png2bin.py art/curtains/curtain-${n}.png
        VERBATIM
    )
endforeach()

# Each frame set of the playfield, cut by art/frames.py from art/frames/,
# as ROM:frame1 and on. art/frames.py also writes frame<n>.png to look at.
set(QUARRY_FRAME_SETS 2)
foreach(n RANGE 1 ${QUARRY_FRAME_SETS})
    add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/frame${n}.bin
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/art/frames.py ${n} ${CMAKE_CURRENT_BINARY_DIR}/frame${n}.bin
            --preview ${CMAKE_CURRENT_BINARY_DIR}/frame${n}.png
        DEPENDS art/frames.py art/curtain.py art/rd2png.py art/png2bin.py art/frames/frame-${n}.png
            art/machine.png art/palettes.png
        VERBATIM
    )
endforeach()

# The panels of the upgrade screen: their tiles, palette and frames, from
# art/panel-frame.png and art/panel-font.png, and panels.h, which gives the
# tile numbers. art/panels.py also writes panels.png to look at.
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/panels.bin ${CMAKE_CURRENT_BINARY_DIR}/panels.h
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/panels.py ${CMAKE_CURRENT_BINARY_DIR}/panels.bin
        ${CMAKE_CURRENT_BINARY_DIR}/panels.h --preview ${CMAKE_CURRENT_BINARY_DIR}/panels.png
    DEPENDS art/panels.py art/rd2png.py art/panel-frame.png art/panel-font.png
    VERBATIM
)

# The backdrop of the upgrade screen, from art/backdrop.png, in three bands,
# and backdrop.h, which gives their sizes. art/backdrop.py also writes
# backdrop.png to look at. It reads PANEL_Y in src/xram.h and the panels'
# heights in art/panels.py.
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/backdrop.bin ${CMAKE_CURRENT_BINARY_DIR}/backdrop.h
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/backdrop.py ${CMAKE_CURRENT_BINARY_DIR}/backdrop.bin
        ${CMAKE_CURRENT_BINARY_DIR}/backdrop.h --preview ${CMAKE_CURRENT_BINARY_DIR}/backdrop.png
    DEPENDS art/backdrop.py art/carts.py art/curtain.py art/panels.py art/rd2png.py art/backdrop.png src/xram.h
    VERBATIM
)

# The mine carts of the stage select and the padlock of a locked stage,
# from art/cart.png and art/padlock.png, and carts.h, which gives their tile
# numbers and the places on a cart.
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/carts.bin ${CMAKE_CURRENT_BINARY_DIR}/carts.h
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/carts.py ${CMAKE_CURRENT_BINARY_DIR}/carts.bin
        ${CMAKE_CURRENT_BINARY_DIR}/carts.h --preview ${CMAKE_CURRENT_BINARY_DIR}/carts.png
    DEPENDS art/carts.py art/cart.png art/padlock.png art/curtain.py art/panel_font.py art/panels.py art/rd2png.py
    VERBATIM
)

# The tiles of the menus: the panels' font and the frame of caution tape
# and steel, and menus.h, which gives their tile numbers.
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/menus.bin ${CMAKE_CURRENT_BINARY_DIR}/menus.h
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/menus.py ${CMAKE_CURRENT_BINARY_DIR}/menus.bin
        ${CMAKE_CURRENT_BINARY_DIR}/menus.h --preview ${CMAKE_CURRENT_BINARY_DIR}/menus.png
    DEPENDS art/menus.py art/panel_font.py art/panels.py art/rd2png.py
    VERBATIM
)

# What the dwarves say, from art/talk.py with the dwarves of art/dwarves/,
# each as ROM:talk1 and on, and talks.h, which numbers them. There are
# QUARRY_TALKS of them, as art/talk.py lists them, and talk.png is the
# first, to look at.
set(QUARRY_TALKS 4)
set(QUARRY_TALK_BINS)
foreach(n RANGE 1 ${QUARRY_TALKS})
    list(APPEND QUARRY_TALK_BINS ${CMAKE_CURRENT_BINARY_DIR}/talk${n}.bin)
endforeach()
add_custom_command(
    OUTPUT ${QUARRY_TALK_BINS} ${CMAKE_CURRENT_BINARY_DIR}/talks.h
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/talk.py ${CMAKE_CURRENT_BINARY_DIR}
        ${CMAKE_CURRENT_BINARY_DIR}/talks.h --count ${QUARRY_TALKS}
        --preview ${CMAKE_CURRENT_BINARY_DIR}/talk.png
    DEPENDS art/talk.py art/curtain.py art/panel_font.py art/panels.py art/rd2png.py art/dwarves/miner.png
    VERBATIM
)

# A sled for each width of src/tuning.h, drawn by art/sled.py, which also
# writes them to look at in sleds/ in the build folder.
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/sleds.bin
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/sled.py ${CMAKE_CURRENT_BINARY_DIR}/sleds.bin
    DEPENDS art/sled.py art/rd2png.py art/png2bin.py art/palettes.png src/tuning.h
    VERBATIM
)

add_executable(quarry)
rp6502_align(quarry "XRAM_.*")
rp6502_asset(quarry help src/help.txt)
rp6502_asset(quarry XRAM(XRAM_PALETTES) ${CMAKE_CURRENT_BINARY_DIR}/palettes.bin)
rp6502_asset(quarry XRAM(XRAM_BRICK_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/brick.bin)
rp6502_asset(quarry XRAM(XRAM_BREAK_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/break.bin)
rp6502_asset(quarry XRAM(XRAM_NUGGET_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/nugget.bin)
rp6502_asset(quarry XRAM(XRAM_BALL_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/ball.bin)
rp6502_asset(quarry XRAM(XRAM_JET_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/jet.bin)
rp6502_asset(quarry XRAM(XRAM_SMOKE_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/smoke.bin)
rp6502_asset(quarry XRAM(XRAM_ENERGY_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/energy.bin)
rp6502_asset(quarry XRAM(XRAM_DIGIT_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/digits.bin)
rp6502_asset(quarry XRAM(XRAM_MACHINE_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/machine.bin)
rp6502_asset(quarry XRAM(XRAM_COIN_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/coin.bin)
rp6502_asset(quarry XRAM(XRAM_CURSOR_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/cursor.bin)
# The art of each screen, which the screen loads when it starts.
rp6502_asset(quarry backdrop ${CMAKE_CURRENT_BINARY_DIR}/backdrop.bin)
rp6502_asset(quarry logo ${CMAKE_CURRENT_BINARY_DIR}/logo.bin)
rp6502_asset(quarry sleds ${CMAKE_CURRENT_BINARY_DIR}/sleds.bin)
rp6502_asset(quarry panels ${CMAKE_CURRENT_BINARY_DIR}/panels.bin)
rp6502_asset(quarry carts ${CMAKE_CURRENT_BINARY_DIR}/carts.bin)
rp6502_asset(quarry menus ${CMAKE_CURRENT_BINARY_DIR}/menus.bin)
foreach(n RANGE 1 ${QUARRY_TALKS})
    rp6502_asset(quarry talk${n} ${CMAKE_CURRENT_BINARY_DIR}/talk${n}.bin)
endforeach()
foreach(texture IN LISTS QUARRY_TEXTURES)
    rp6502_asset(quarry ${texture} ${CMAKE_CURRENT_BINARY_DIR}/${texture}.bin)
endforeach()
foreach(n RANGE 1 ${QUARRY_CURTAIN_SETS})
    rp6502_asset(quarry curtain${n} ${CMAKE_CURRENT_BINARY_DIR}/curtain${n}.bin)
endforeach()
foreach(n RANGE 1 ${QUARRY_FRAME_SETS})
    rp6502_asset(quarry frame${n} ${CMAKE_CURRENT_BINARY_DIR}/frame${n}.bin)
endforeach()
rp6502_executable(quarry DATA default RESET default)
rp6502_web(quarry CONFIG [[
    title: 'Quarry',
    db: 'rumbledethumps-quarry',
    footer: 'Arrows, WASD or the keypad to move. Space, Enter or Ctrl is the button, which launches. In menus, up and down to pick and the button to choose. Esc or P for the menu. Gamepads work too: A, B, X or Y is the button, and Start or Select the menu.',
]])
target_sources(quarry PRIVATE
    src/machines.c
    src/bricks.c
    src/cursor.c
    src/energy.c
    src/frame.c
    src/input.c
    src/main.c
    src/menu.c
    src/nuggets.c
    src/paddle.c
    src/play.c
    src/save.c
    src/scene.c
    src/sfx.c
    src/shop.c
    src/talk.c
    src/title.c
    src/upgrades.c
    src/video.c
    ${CMAKE_CURRENT_BINARY_DIR}/backdrop.h
    ${CMAKE_CURRENT_BINARY_DIR}/panels.h
    ${CMAKE_CURRENT_BINARY_DIR}/carts.h
    ${CMAKE_CURRENT_BINARY_DIR}/menus.h
    ${CMAKE_CURRENT_BINARY_DIR}/talks.h
)
target_include_directories(quarry PRIVATE ${CMAKE_CURRENT_BINARY_DIR})

# The tests, which ctest runs in the emulator. Each one plays the ROM from a
# Python script in tests/. Only autoplay runs on a Release ROM, because the
# others wait for the events that a Debug ROM logs.
set(QUARRY_ROM $<TARGET_PROPERTY:quarry,RP6502_ROM>)
rp6502_test(NAME autoplay COMMAND tests/autoplay.py ${QUARRY_ROM})
rp6502_test(NAME autoplay-miss COMMAND tests/autoplay.py --miss 5 ${QUARRY_ROM})
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    rp6502_test(NAME controls COMMAND tests/controls.py ${QUARRY_ROM})
    rp6502_test(NAME energy COMMAND tests/energy.py ${QUARRY_ROM})
    rp6502_test(NAME nuggets COMMAND tests/nuggets.py ${QUARRY_ROM})
    rp6502_test(NAME upgrades COMMAND tests/upgrades.py ${QUARRY_ROM})
    rp6502_test(NAME saves COMMAND tests/saves.py ${QUARRY_ROM})
    rp6502_test(NAME sound COMMAND tests/sound.py ${QUARRY_ROM})
    rp6502_test(NAME talk COMMAND tests/talk.py ${QUARRY_ROM})
endif()
