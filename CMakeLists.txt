cmake_minimum_required(VERSION 3.21)

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
quarry_art(tiles.bin image tiles.png --tile 16x16)
quarry_art(brick.bin image brick.png)
quarry_art(ball.bin image ball.png)
quarry_art(paddle.bin image paddle.png --tile 8x8)
quarry_art(flame.bin image flame.png --tile 8x8)
quarry_art(smoke.bin image smoke.png --tile 8x8)
quarry_art(energy.bin image energy.png --tile 28x4)

add_executable(quarry)
rp6502_map(quarry src/xram.h "XRAM_.*")
rp6502_asset(quarry help src/help.txt)
rp6502_asset(quarry XRAM(XRAM_PALETTES) ${CMAKE_CURRENT_BINARY_DIR}/palettes.bin)
rp6502_asset(quarry XRAM(XRAM_TILES) ${CMAKE_CURRENT_BINARY_DIR}/tiles.bin)
rp6502_asset(quarry XRAM(XRAM_BRICK_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/brick.bin)
rp6502_asset(quarry XRAM(XRAM_BALL_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/ball.bin)
rp6502_asset(quarry XRAM(XRAM_PADDLE_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/paddle.bin)
rp6502_asset(quarry XRAM(XRAM_FLAME_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/flame.bin)
rp6502_asset(quarry XRAM(XRAM_SMOKE_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/smoke.bin)
rp6502_asset(quarry XRAM(XRAM_ENERGY_IMAGES) ${CMAKE_CURRENT_BINARY_DIR}/energy.bin)
rp6502_executable(quarry DATA default RESET default)
rp6502_web(quarry CONFIG [[
    title: 'Quarry',
    footer: 'A, D, arrows or keypad 4 and 6 to move. Space, Enter, keypad 0 or keypad Enter to launch. Gamepads work too.',
]])
target_sources(quarry PRIVATE
    src/bricks.c
    src/energy.c
    src/input.c
    src/main.c
    src/paddle.c
    src/play.c
    src/video.c
)
