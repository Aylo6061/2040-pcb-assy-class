// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include "quantum.h"

#ifdef RGB_MATRIX_ENABLE
// Short name of an RGB Matrix effect, sized to fit the OLED after "RGB: ".
// Returns NULL for an effect without a name here.
const char *rgb_matrix_effect_name(uint8_t mode);
#endif
