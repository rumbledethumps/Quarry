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
quarry_art(tiles.bin image tiles.png --tile 16x16)
quarry_art(brick.bin image brick.png)
quarry_art(break.bin image break.png --tile 24x16)
quarry_art(nugget.bin image nugget.png)
quarry_art(ball.bin image ball.png)
quarry_art(jet.bin image jet.png --tile 8x12)
quarry_art(smoke.bin image smoke.png --tile 8x8)
quarry_art(energy.bin image energy.png --tile 8x8)
quarry_art(logo.bin image logo.png --tile 64x64)
quarry_art(digits.bin image digits.png --tile 8x12)
quarry_art(post.bin image post.png)
quarry_art(beam.bin image beam.png)
quarry_art(cap.bin image cap.png)
quarry_art(brace.bin image brace.png)
quarry_art(machine.bin image machine.png)

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
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/curtain1.bin
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/art/curtain.py ${CMAKE_CURRENT_SOURCE_DIR}/art/curtains/curtain-1.png
        ${CMAKE_CURRENT_BINARY_DIR}/curtain1.bin --preview ${CMAKE_CURRENT_BINARY_DIR}/curtain1.png
    DEPENDS art/curtain.py art/rd2png.py art/png2bin.py art/curtains/curtain-1.png
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
rp6502_asset(quarry XRAM(XRAM_POST_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/post.bin)
rp6502_asset(quarry XRAM(XRAM_BEAM_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/beam.bin)
rp6502_asset(quarry XRAM(XRAM_CAP_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/cap.bin)
rp6502_asset(quarry XRAM(XRAM_BRACE_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/brace.bin)
rp6502_asset(quarry XRAM(XRAM_MACHINE_IMAGE) ${CMAKE_CURRENT_BINARY_DIR}/machine.bin)
# The art of each screen, which the screen loads when it starts.
rp6502_asset(quarry tiles ${CMAKE_CURRENT_BINARY_DIR}/tiles.bin)
rp6502_asset(quarry logo ${CMAKE_CURRENT_BINARY_DIR}/logo.bin)
rp6502_asset(quarry sleds ${CMAKE_CURRENT_BINARY_DIR}/sleds.bin)
foreach(texture IN LISTS QUARRY_TEXTURES)
    rp6502_asset(quarry ${texture} ${CMAKE_CURRENT_BINARY_DIR}/${texture}.bin)
endforeach()
rp6502_asset(quarry curtain1 ${CMAKE_CURRENT_BINARY_DIR}/curtain1.bin)
rp6502_executable(quarry DATA default RESET default)
rp6502_web(quarry CONFIG [[
    title: 'Quarry',
    db: 'rumbledethumps-quarry',
    footer: 'Left and right to move, up or Space to launch, with arrows, WASD or the keypad. In menus, up and down to pick and Space or Enter to choose. Esc to pause. Gamepads work too.',
]])
target_sources(quarry PRIVATE
    src/bricks.c
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
    src/title.c
    src/upgrades.c
    src/video.c
)

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
endif()
