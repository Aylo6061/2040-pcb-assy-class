// SPDX-License-Identifier: GPL-2.0-or-later

#include QMK_KEYBOARD_H

enum layers { _BASE, _FN };

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    // Encoder press: tap to mute, hold for the Fn layer.
    [_BASE] = LAYOUT(
                              LT(_FN, KC_MUTE),
        KC_7,    KC_8,    KC_9,
        KC_4,    KC_5,    KC_6,
        KC_1,    KC_2,    KC_3,
        KC_ENT,  KC_0,    KC_BSPC
    ),
    [_FN] = LAYOUT(
                              _______,
        RM_TOGG, RM_PREV, RM_NEXT,
        _______, _______, _______,
        _______, _______, _______,
        _______, _______, QK_BOOT
    ),
};

#ifdef ENCODER_MAP_ENABLE
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {
    [_BASE] = { ENCODER_CCW_CW(KC_VOLD, KC_VOLU) },
    [_FN]   = { ENCODER_CCW_CW(RM_VALD, RM_VALU) },
};
#endif

#ifdef OLED_ENABLE
// If the display is upside down on your board, return OLED_ROTATION_180.
oled_rotation_t oled_init_user(oled_rotation_t rotation) {
    return OLED_ROTATION_0;
}

bool oled_task_user(void) {
    oled_set_cursor(0, 0);
    oled_write_ln_P(PSTR("2040pad"), false);

    oled_write_P(PSTR("Layer: "), false);
    switch (get_highest_layer(layer_state)) {
        case _FN:
            oled_write_ln_P(PSTR("Fn"), false);
            break;
        default:
            oled_write_ln_P(PSTR("Base"), false);
            break;
    }

    oled_write_P(PSTR("RGB: "), false);
    if (rgb_matrix_is_enabled()) {
        oled_write_P(PSTR("mode "), false);
        oled_write_ln(get_u8_str(rgb_matrix_get_mode(), ' '), false);
    } else {
        oled_write_ln_P(PSTR("off"), false);
    }
    return false;
}
#endif
