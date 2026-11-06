// SPDX-License-Identifier: GPL-2.0-or-later
//
// Bring-up test for the rotary encoder. Reads the A and B pins directly, as well
// as through QMK's encoder decoder, so it shows where a fault sits.
//
// Typed text:   a / A  pin A went low / high
//               b / B  pin B went low / high
//               > / <  QMK decoded a clockwise / counterclockwise click
// Key LEDs:     left column follows pin A, right column follows pin B
//               green = high, red = low
// OLED:         live pin levels, edge counts and decoded clicks

#include QMK_KEYBOARD_H

enum layers { _BASE, _FN };

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [_BASE] = LAYOUT(
                              LT(_FN, KC_MUTE),
        KC_7,    KC_8,    KC_9,
        KC_4,    KC_5,    KC_6,
        KC_1,    KC_2,    KC_3,
        KC_ENT,  KC_0,    KC_BSPC
    ),
    [_FN] = LAYOUT(
                              _______,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, QK_BOOT
    ),
};

// Named after the schematic nets, so "A" here is IC1 pin A (ROTA).
#define ENCODER_PIN_A GP17
#define ENCODER_PIN_B GP18
#define SETTLE_MS 2

typedef struct {
    pin_t    pin;
    uint16_t low_key;
    bool     stable;
    bool     candidate;
    uint16_t changed_at;
    uint16_t edges;
} channel_t;

static channel_t channels[] = {
    {.pin = ENCODER_PIN_A, .low_key = KC_A},
    {.pin = ENCODER_PIN_B, .low_key = KC_B},
};

static uint16_t clicks_cw  = 0;
static uint16_t clicks_ccw = 0;

void keyboard_post_init_user(void) {
    for (uint8_t i = 0; i < ARRAY_SIZE(channels); i++) {
        gpio_set_pin_input_high(channels[i].pin);
    }
    wait_ms(1);
    for (uint8_t i = 0; i < ARRAY_SIZE(channels); i++) {
        channels[i].stable     = gpio_read_pin(channels[i].pin);
        channels[i].candidate  = channels[i].stable;
        channels[i].changed_at = timer_read();
    }
    rgb_matrix_enable_noeeprom();
}

void housekeeping_task_user(void) {
    for (uint8_t i = 0; i < ARRAY_SIZE(channels); i++) {
        channel_t *ch  = &channels[i];
        bool       now = gpio_read_pin(ch->pin);

        if (now != ch->candidate) {
            ch->candidate  = now;
            ch->changed_at = timer_read();
        } else if (now != ch->stable && timer_elapsed(ch->changed_at) >= SETTLE_MS) {
            ch->stable = now;
            ch->edges++;
            if (now) {
                tap_code16(S(ch->low_key));
            } else {
                tap_code(ch->low_key);
            }
        }
    }
}

// Returning false stops QMK's default volume action.
bool encoder_update_user(uint8_t index, bool clockwise) {
    if (clockwise) {
        clicks_cw++;
        tap_code16(S(KC_DOT));
    } else {
        clicks_ccw++;
        tap_code16(S(KC_COMMA));
    }
    return false;
}

// Colors are set directly, so keep them dim to stay within USB power limits.
bool rgb_matrix_indicators_user(void) {
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        uint8_t column = i % 3;
        if (column == 1) {
            rgb_matrix_set_color(i, 0, 0, 0);
        } else {
            bool high = channels[column == 0 ? 0 : 1].stable;
            rgb_matrix_set_color(i, high ? 0 : 40, high ? 40 : 0, 0);
        }
    }
    return false;
}

#ifdef OLED_ENABLE
static void write_channel(const char *label, const channel_t *ch) {
    oled_write(label, false);
    oled_write(ch->stable ? "1" : "0", false);
    oled_write_P(PSTR(" edges:"), false);
    oled_write_ln(get_u16_str(ch->edges, ' '), false);
}

bool oled_task_user(void) {
    oled_set_cursor(0, 0);
    oled_write_ln_P(PSTR("ENCODER TEST"), false);
    write_channel("A:", &channels[0]);
    write_channel("B:", &channels[1]);
    oled_write_P(PSTR("cw:"), false);
    oled_write(get_u16_str(clicks_cw, ' '), false);
    oled_write_P(PSTR(" ccw:"), false);
    oled_write_ln(get_u16_str(clicks_ccw, ' '), false);
    return false;
}
#endif
