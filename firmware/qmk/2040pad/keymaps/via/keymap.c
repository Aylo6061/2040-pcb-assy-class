// SPDX-License-Identifier: GPL-2.0-or-later
//
// VIA-enabled keymap. These layers are only the starting point: VIA saves its
// own copy to flash, and edits made in VIA replace them.

#include QMK_KEYBOARD_H

// VIA's default of 4 dynamic layers.
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    // Encoder press: tap to mute, hold for layer 1.
    [0] = LAYOUT(
                              LT(1, KC_MUTE),
        KC_7,    KC_8,    KC_9,
        KC_4,    KC_5,    KC_6,
        KC_1,    KC_2,    KC_3,
        KC_ENT,  KC_0,    KC_BSPC
    ),
    [1] = LAYOUT(
                              _______,
        RM_TOGG, RM_PREV, RM_NEXT,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, QK_BOOT
    ),
    [2] = LAYOUT(
                              _______,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, _______
    ),
    [3] = LAYOUT(
                              _______,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, _______
    ),
};

const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    [0] = { ENCODER_CCW_CW(KC_VOLD, KC_VOLU) },
    [1] = { ENCODER_CCW_CW(RM_VALD, RM_VALU) },
    [2] = { ENCODER_CCW_CW(_______, _______) },
    [3] = { ENCODER_CCW_CW(_______, _______) },
};

// The effect list in firmware/qmk/2040pad_via.json uses these mode numbers.
// If the animations in keyboard.json change, update that file to match.
#ifdef RGB_MATRIX_ENABLE
_Static_assert(RGB_MATRIX_SOLID_COLOR == 1, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_BREATHING == 2, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_CYCLE_ALL == 3, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_CYCLE_LEFT_RIGHT == 4, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_CYCLE_UP_DOWN == 5, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_RAINBOW_MOVING_CHEVRON == 6, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_CYCLE_SPIRAL == 7, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_RAINDROPS == 8, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_HUE_WAVE == 9, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_PIXEL_RAIN == 10, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_TYPING_HEATMAP == 11, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_SOLID_REACTIVE_SIMPLE == 12, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_SOLID_REACTIVE == 13, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_SPLASH == 14, "Update the effect list in 2040pad_via.json");
_Static_assert(RGB_MATRIX_EFFECT_MAX == 15, "Update the effect list in 2040pad_via.json");
#endif

#ifdef OLED_ENABLE
bool oled_task_user(void) {
    oled_set_cursor(0, 0);
    oled_write_ln_P(PSTR("2040pad VIA"), false);

    oled_write_P(PSTR("Layer: "), false);
    oled_write_ln(get_u8_str(get_highest_layer(layer_state), ' '), false);

    oled_write_P(PSTR("RGB: "), false);
    if (rgb_matrix_is_enabled()) {
        const char *name = rgb_matrix_effect_name(rgb_matrix_get_mode());
        oled_write_ln(name ? name : get_u8_str(rgb_matrix_get_mode(), ' '), false);
    } else {
        oled_write_ln_P(PSTR("off"), false);
    }
    return false;
}
#endif
