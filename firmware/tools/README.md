# padmap

A small Python app for viewing and changing the 2040pad's keymap over USB, without reflashing. It uses the same USB protocol as VIA, so the pad must run the VIA firmware (`firmware/qmk/2040pad_via.uf2`).

Changes are saved on the pad as soon as you send them, and survive unplugging.

## Setup

### 1. Install tkinter from your operating system

The window uses tkinter, which pip can't install. Python from python.org includes it on Windows and macOS. Otherwise, install it with your system package manager:

| System | Command |
|---|---|
| Debian, Ubuntu, Raspberry Pi OS | `sudo apt install python3-tk python3-venv` |
| Fedora | `sudo dnf install python3-tkinter` |
| Arch | `sudo pacman -S tk` |
| macOS with Homebrew Python | `brew install python-tk@3.X`, using your Python version for `3.X` |
| Windows | Rerun the python.org installer, choose Modify, and select **tcl/tk and IDLE** |

To check, run `python -c "import tkinter"`. It should print nothing. The command-line commands work without tkinter.

### 2. Create a virtual environment and install hidapi

These systems block `pip install` into the system Python, which shows up as an "externally-managed-environment" error. A virtual environment avoids that, and it still uses the system's tkinter.

Windows:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

macOS and Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Install tkinter before creating the virtual environment. If you add it later, delete `.venv` and create it again.

Linux also needs a udev rule to allow access to the pad's HID device.

## Window

```bash
.venv/Scripts/python padmap.py
```

1. Pick a layer.
2. Click a key or an encoder action.
3. Type a keycode and press Enter or **Send to pad**. As you type, matching keycodes are suggested and the value is previewed below the box.

**Save to file** and **Load file** save or restore all layers as JSON. **Reset keymap** returns every layer to the firmware's built-in keymap.

## Command line

| Command | Does |
|---|---|
| `padmap.py info` | Show the VIA protocol version and layer count |
| `padmap.py dump [file.json]` | Print or save every layer |
| `padmap.py load file.json` | Write a saved keymap to the pad |
| `padmap.py set 0 k1 KC_A` | Set layer 0, key 1 to A |

Keys are `k1`-`k12` (left to right, top to bottom), `enc` (encoder press), and `ccw` / `cw` (encoder turn).

## Keycodes

Use QMK keycode names. A few examples:

| You type | Result |
|---|---|
| `KC_A` or `A` | A |
| `LCTL(KC_C)` | Ctrl+C |
| `KC_VOLU` | Volume up |
| `MO(1)` | Layer 1 while held |
| `LT(1, KC_MUTE)` | Mute on tap, layer 1 while held |
| `LCTL_T(KC_A)` | A on tap, Ctrl while held |
| `RM_NEXT` | Next LED effect |
| `QK_BOOT` | Enter the bootloader |
| `_______` | Use the key from the layer below |

The keycode list in `keycodes.json` comes from the QMK version the firmware was built with. After updating QMK, regenerate it:

```bash
.venv/Scripts/python gen_keycodes.py C:/Users/Avery/qmk_firmware
```
