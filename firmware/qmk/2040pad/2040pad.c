// SPDX-License-Identifier: GPL-2.0-or-later

#include "2040pad.h"

#ifdef RGB_MATRIX_ENABLE
// Each name is at most 16 characters so "RGB: " plus the name fits one
// 21-character OLED line.
const char *rgb_matrix_effect_name(uint8_t mode) {
    switch (mode) {
        case RGB_MATRIX_SOLID_COLOR:
            return "Solid Color";
#    ifdef ENABLE_RGB_MATRIX_BREATHING
        case RGB_MATRIX_BREATHING:
            return "Breathing";
#    endif
#    ifdef ENABLE_RGB_MATRIX_CYCLE_ALL
        case RGB_MATRIX_CYCLE_ALL:
            return "Cycle All";
#    endif
#    ifdef ENABLE_RGB_MATRIX_CYCLE_LEFT_RIGHT
        case RGB_MATRIX_CYCLE_LEFT_RIGHT:
            return "Cycle Left/Right";
#    endif
#    ifdef ENABLE_RGB_MATRIX_CYCLE_UP_DOWN
        case RGB_MATRIX_CYCLE_UP_DOWN:
            return "Cycle Up/Down";
#    endif
#    ifdef ENABLE_RGB_MATRIX_RAINBOW_MOVING_CHEVRON
        case RGB_MATRIX_RAINBOW_MOVING_CHEVRON:
            return "Chevron";
#    endif
#    ifdef ENABLE_RGB_MATRIX_CYCLE_SPIRAL
        case RGB_MATRIX_CYCLE_SPIRAL:
            return "Cycle Spiral";
#    endif
#    ifdef ENABLE_RGB_MATRIX_RAINDROPS
        case RGB_MATRIX_RAINDROPS:
            return "Raindrops";
#    endif
#    ifdef ENABLE_RGB_MATRIX_HUE_WAVE
        case RGB_MATRIX_HUE_WAVE:
            return "Hue Wave";
#    endif
#    ifdef ENABLE_RGB_MATRIX_PIXEL_RAIN
        case RGB_MATRIX_PIXEL_RAIN:
            return "Pixel Rain";
#    endif
#    ifdef ENABLE_RGB_MATRIX_TYPING_HEATMAP
        case RGB_MATRIX_TYPING_HEATMAP:
            return "Typing Heatmap";
#    endif
#    ifdef ENABLE_RGB_MATRIX_SOLID_REACTIVE_SIMPLE
        case RGB_MATRIX_SOLID_REACTIVE_SIMPLE:
            return "Reactive Simple";
#    endif
#    ifdef ENABLE_RGB_MATRIX_SOLID_REACTIVE
        case RGB_MATRIX_SOLID_REACTIVE:
            return "Solid Reactive";
#    endif
#    ifdef ENABLE_RGB_MATRIX_SPLASH
        case RGB_MATRIX_SPLASH:
            return "Splash";
#    endif
        default:
            return NULL;
    }
}
#endif

// Blink the status LED (D2) from the main loop to show the firmware is running.
#define HEARTBEAT_LED_PIN GP13
#define HEARTBEAT_TOGGLE_MS 500

static uint32_t heartbeat_timer = 0;

void keyboard_post_init_kb(void) {
    gpio_set_pin_output(HEARTBEAT_LED_PIN);
    gpio_write_pin_high(HEARTBEAT_LED_PIN);
    heartbeat_timer = timer_read32();

    keyboard_post_init_user();
}

void housekeeping_task_kb(void) {
    if (timer_elapsed32(heartbeat_timer) >= HEARTBEAT_TOGGLE_MS) {
        heartbeat_timer = timer_read32();
        gpio_toggle_pin(HEARTBEAT_LED_PIN);
    }
}
