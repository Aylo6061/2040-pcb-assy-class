// SPDX-License-Identifier: GPL-2.0-or-later

#include "quantum.h"

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
