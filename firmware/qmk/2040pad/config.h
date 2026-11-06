// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright 2022 Jose Pablo Ramirez <jp.ramangulo@gmail.com>
// Based on QMK's keyboards/adafruit/macropad definition.

#pragma once

/* SSD1306 128x32 OLED on J3, also shared with the J2 Qwiic-style connector.
 * GP20/GP21 belong to the RP2040's I2C0 peripheral, so the driver is I2CD0.
 * QMK uses the I2C1_* pin names whichever peripheral is selected. */
#define I2C_DRIVER I2CD0
#define I2C1_SDA_PIN GP20
#define I2C1_SCL_PIN GP21

#define OLED_DISPLAY_128X32

/* Double-tap the reset button (SW1) to enter the UF2 bootloader. */
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_LED GP13
