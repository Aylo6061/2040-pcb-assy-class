# 2040pad QMK firmware

QMK keyboard definition for the 2040pad: 12 choc keys, a PEC11R encoder with push switch, 12 SK6812MINI-E LEDs and a 128x32 SSD1306 OLED.

**Status: compiles against QMK `f5db962110` (2026-10-29). Tested on the first board (2026-11-05): the keys and encoder work, including the swapped encoder pins that reverse the volume direction.**

## Pins

Taken from the nets in `2040pad/2040pad.kicad_pcb`.

| Function | Pin |
|---|---|
| Keys 1-12 (`CH1`-`CH12`, active low) | GP1-GP12 |
| Encoder push | GP0 (also drives BOOTSEL through `CR1` and `R13`) |
| Encoder A / B | GP17 / GP18 |
| LED data, through `U5` level shifter | GP19 |
| I2C0 SDA / SCL (OLED `J3`, connector `J2`) | GP20 / GP21 |
| Status LED `D2` | GP13 |

## Build

Copy this folder into a QMK checkout as `keyboards/2040pad`, then run:

```bash
qmk compile -kb 2040pad -km default
```

## Flash

Enter the bootloader, then copy `2040pad_default.uf2` to the `RPI-RP2` drive that appears. Any of these will enter it:

- Double-tap the reset button (`SW1`).
- Hold the top-left key while plugging in USB (needs QMK already flashed).
- Hold the encoder down, then press the bottom-right key (`QK_BOOT` on the Fn layer; needs QMK already flashed).
- Hold the encoder down, tap `SW1`, then release the encoder. This is the hardware BOOTSEL route and works with any firmware. A board with blank flash also enters the bootloader by itself.

## Default keymap

| Control | Base layer | Fn layer (hold encoder) |
|---|---|---|
| Encoder turn | Volume | LED brightness |
| Encoder tap | Mute | |
| Top row | 7 8 9 | LED toggle, previous effect, next effect |
| Bottom row | Enter, 0, Backspace | Bottom-right enters the bootloader |

## Hardware note: `R7`

`R7` (10k) sits in series between the RP2040's `QSPI_SS` and the flash chip's `nCS`. Adafruit's design connects these directly and uses its 10k as a pull-up to 3.3V instead. The first board boots from flash with `R7` fitted, so it doesn't prevent booting, but this differs from the reference design and timing margin hasn't been measured.

## Changing the keymap with VIA

The `via` keymap stores the keymap in flash, so you can change it from [usevia.app](https://usevia.app) without reflashing. The board keeps working normally while you edit.

1. Build it with `qmk compile -kb 2040pad -km via`, or use the prebuilt `firmware/qmk/2040pad_via.uf2`, and flash it.
2. Open [usevia.app](https://usevia.app) in Chrome or Edge.
3. In Settings, turn on **Show Design tab**.
4. In the Design tab, load `firmware/qmk/2040pad_via.json`. Your board isn't in VIA's built-in list, so each browser needs this once.
5. In the Configure tab, authorize the 2040pad. You can then edit 4 layers of keys, encoder actions, macros and lighting.

As an alternative to the VIA website, `firmware/tools/padmap.py` is a small Python app that does the same keymap editing. See `firmware/tools/README.md`.

**Notes:**
- The keymap in `keymaps/via/keymap.c` is only the starting point. VIA saves its own copy to flash.
- VIA's built-in lighting menu assumes every effect is compiled in, so `2040pad_via.json` lists this board's 14 effects. If you change the animations in `keyboard.json`, the build fails until you update both that file and the checks in `keymaps/via/keymap.c`.
- OLED text is set in firmware, so VIA can't change it.
- To reset VIA's changes, hold the top-left key while plugging in. This erases the saved settings and enters the bootloader.

## Status LED

`D2` blinks once per second while the firmware's main loop is running. It may be dim because `R14` is 5.1k. If it stops during normal use, the firmware has hung. It may also stop while the PC is asleep.

## LED positions

The LED positions in `keyboard.json` use the real key spacing (18.0 mm columns, 17.1 mm rows), scaled so the farthest pair of keys is 224 units apart, with the center at (64, 92). QMK's usual formula stretches every board to 224 × 64, which made effects like Splash spread about 5× faster vertically than horizontally on this tall board.

- **Splash, Spiral, Chevron and Up/Down:** spread evenly in both directions.
- **Typing Heatmap:** its spread is raised to 132 in `config.h`, so pressing a key still warms its neighbors.
- **Limit:** keep any two LEDs less than 256 units apart, because some effects store distances in one byte.

`qmk lint` reports that a `via` keymap shouldn't exist. That's QMK's policy for its own repository and doesn't affect building.

## Check on first power-up

- **Encoder direction:** if it's reversed, swap `pin_a` and `pin_b` in `keyboard.json`.
- **OLED orientation:** if it's upside down, change the rotation in `keymaps/default/keymap.c`.
- **LED brightness:** `max_brightness` is capped at 120 of 255 to stay within USB power limits. This is a conservative estimate, not a measured figure.
- **USB ID:** `0xFEED:0x2040` is an unregistered placeholder, fine for personal use only.
