"""padmap: view and change the 2040pad's keymap over USB.

Talks to the VIA firmware (2040pad_via.uf2) using VIA's raw HID protocol. Changes
are saved on the pad immediately and survive unplugging.

    python padmap.py                       open the window
    python padmap.py web                   open it in your web browser instead (no tkinter needed)
    python padmap.py info                  show the pad's firmware details
    python padmap.py dump [file.json]      print or save every layer
    python padmap.py load file.json        write a saved keymap to the pad
    python padmap.py set LAYER KEY CODE    change one key, for example: set 0 k1 KC_A

KEY is k1-k12 (left to right, top to bottom), enc (encoder press), ccw or cw (encoder turn).
CODE is a QMK keycode such as KC_A, A, LCTL(KC_C), MO(1), LT(1, KC_MUTE) or 0x0004.
"""

import json
import re
import sys
from pathlib import Path

VENDOR_ID = 0xFEED
PRODUCT_ID = 0x2040
RAW_USAGE_PAGE = 0xFF60
RAW_USAGE = 0x61
REPORT_SIZE = 32

# VIA command IDs, from quantum/via.h.
CMD_PROTOCOL_VERSION = 0x01
CMD_GET_KEYCODE = 0x04
CMD_SET_KEYCODE = 0x05
CMD_RESET_KEYMAP = 0x06
CMD_LAYER_COUNT = 0x11
CMD_GET_ENCODER = 0x14
CMD_SET_ENCODER = 0x15
CMD_UNHANDLED = 0xFF

# Physical layout: (name, matrix row, matrix column), matching keyboard.json.
KEYS = [(f"k{i + 1}", 1 + i // 3, i % 3) for i in range(12)]
ENCODER_PRESS = ("enc", 0, 2)
ENCODER_INDEX = 0

# ---------------------------------------------------------------------------
# Keycodes


def _load_keycodes():
    path = Path(__file__).with_name("keycodes.json")
    if not path.exists():
        return {}, {}, "missing"
    data = json.loads(path.read_text(encoding="utf8"))
    return data["keycodes"], data["mods"], data.get("qmk_version", "unknown")


KEYCODES, MODS, KEYCODES_QMK_VERSION = _load_keycodes()

# Modifier bits used inside 16-bit keycodes (QK_MODS range): Ctrl, Shift, Alt, GUI, right-hand flag.
MOD_BITS = {"CTL": 0x01, "SFT": 0x02, "ALT": 0x04, "GUI": 0x08}
RIGHT = 0x10

MOD_WRAPPERS = {
    "LCTL": 0x01, "LSFT": 0x02, "LALT": 0x04, "LGUI": 0x08,
    "RCTL": 0x11, "RSFT": 0x12, "RALT": 0x14, "RGUI": 0x18,
    "C": 0x01, "S": 0x02, "A": 0x04, "G": 0x08,
    "LOPT": 0x04, "LCMD": 0x08, "LWIN": 0x08, "ROPT": 0x14, "RCMD": 0x18, "RWIN": 0x18, "ALGR": 0x14,
    "LCS": 0x03, "LCA": 0x05, "LCG": 0x09, "LSA": 0x06, "LSG": 0x0A, "LAG": 0x0C,
    "MEH": 0x07, "HYPR": 0x0F,
}
MOD_TAP_ALIASES = {
    "LCTL_T": 0x01, "LSFT_T": 0x02, "LALT_T": 0x04, "LGUI_T": 0x08,
    "RCTL_T": 0x11, "RSFT_T": 0x12, "RALT_T": 0x14, "RGUI_T": 0x18,
    "MEH_T": 0x07, "HYPR_T": 0x0F, "ALL_T": 0x0F,
}
LAYER_FUNCTIONS = {"TO": 0x5200, "MO": 0x5220, "DF": 0x5240, "TG": 0x5260, "OSL": 0x5280, "TT": 0x52C0}

_TOKEN = re.compile(r"\s*(?:(0[xX][0-9A-Fa-f]+|\d+)|([A-Za-z_][A-Za-z0-9_]*)|(.))")


def _tokens(text):
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        number, name, other = m.groups()
        if number:
            out.append(("num", int(number, 0)))
        elif name:
            out.append(("name", name.upper()))
        elif other.strip():
            out.append(("op", other))
        pos = m.end()
    return out


def parse_keycode(text, keycodes=None, mods=None):
    """Turn text such as 'LT(1, KC_MUTE)' into a 16-bit keycode. Raises ValueError."""
    keycodes = KEYCODES if keycodes is None else keycodes
    mods = MODS if mods is None else mods
    tokens = _tokens(text)
    if not tokens:
        raise ValueError("enter a keycode")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else (None, None)

    def take(kind=None, value=None):
        nonlocal pos
        tok = peek()
        if tok[0] is None or (kind and tok[0] != kind) or (value and tok[1] != value):
            raise ValueError(f"unexpected {tok[1] if tok[1] is not None else 'end'} in {text!r}")
        pos += 1
        return tok

    def lookup(name):
        name = {"_______": "KC_TRNS", "XXXXXXX": "KC_NO"}.get(name, name)
        for candidate in (name, "KC_" + name):
            if candidate in keycodes:
                return keycodes[candidate]
            if candidate in mods:
                return mods[candidate]
        raise ValueError(f"unknown keycode {name}")

    def term():
        kind, value = take()
        if kind == "num":
            return value
        if kind == "op" and value == "(":
            v = expr()
            take("op", ")")
            return v
        if kind != "name":
            raise ValueError(f"unexpected {value} in {text!r}")
        if peek() != ("op", "("):
            return lookup(value)
        take("op", "(")
        args = [expr()]
        while peek() == ("op", ","):
            take("op", ",")
            args.append(expr())
        take("op", ")")
        return call(value, args)

    def expr():
        v = term()
        while peek() == ("op", "|"):
            take("op", "|")
            v |= term()
        return v

    def need(name, args, count):
        if len(args) != count:
            raise ValueError(f"{name} takes {count} argument{'s' if count > 1 else ''}")

    def call(name, args):
        if name in MOD_WRAPPERS:
            need(name, args, 1)
            return (MOD_WRAPPERS[name] << 8) | args[0]
        if name in MOD_TAP_ALIASES:
            need(name, args, 1)
            return 0x2000 | (MOD_TAP_ALIASES[name] << 8) | (args[0] & 0xFF)
        if name in LAYER_FUNCTIONS:
            need(name, args, 1)
            return LAYER_FUNCTIONS[name] | (args[0] & 0x1F)
        if name == "LT":
            need(name, args, 2)
            return 0x4000 | ((args[0] & 0xF) << 8) | (args[1] & 0xFF)
        if name == "MT":
            need(name, args, 2)
            return 0x2000 | ((args[0] & 0x1F) << 8) | (args[1] & 0xFF)
        if name == "LM":
            need(name, args, 2)
            return 0x5000 | ((args[0] & 0xF) << 5) | (args[1] & 0x1F)
        if name == "OSM":
            need(name, args, 1)
            return 0x52A0 | (args[0] & 0x1F)
        raise ValueError(f"unknown function {name}")

    value = expr()
    if pos != len(tokens):
        raise ValueError(f"unexpected {tokens[pos][1]} in {text!r}")
    if not 0 <= value <= 0xFFFF:
        raise ValueError("keycode out of range")
    return value


def _preferred_names():
    best = {}
    for name, value in KEYCODES.items():
        if not name[0].isalpha():
            continue
        rank = (not name.startswith("KC_"), len(name), name)
        if value not in best or rank < best[value][0]:
            best[value] = (rank, name)
    return {v: n for v, (_, n) in best.items()}


_NAMES = _preferred_names()


def _mod_names(mods):
    side = "R" if mods & RIGHT else "L"
    parts = [f"MOD_{side}{n}" for n, bit in MOD_BITS.items() if mods & bit]
    return "|".join(parts) or "0"


def format_keycode(value):
    """Turn a 16-bit keycode into readable text that parse_keycode accepts."""
    if value in _NAMES:
        return _NAMES[value]
    if 0x0100 <= value <= 0x1FFF:
        mods, inner = (value >> 8) & 0x1F, format_keycode(value & 0xFF)
        side = "R" if mods & RIGHT else "L"
        for n, bit in MOD_BITS.items():
            if mods & bit:
                inner = f"{side}{n}({inner})"
        return inner
    if 0x2000 <= value <= 0x3FFF:
        mods, kc = (value >> 8) & 0x1F, format_keycode(value & 0xFF)
        alias = next((a for a, m in MOD_TAP_ALIASES.items() if m == mods and a != "ALL_T"), None)
        return f"{alias}({kc})" if alias else f"MT({_mod_names(mods)}, {kc})"
    if 0x4000 <= value <= 0x4FFF:
        return f"LT({(value >> 8) & 0xF}, {format_keycode(value & 0xFF)})"
    if 0x5000 <= value <= 0x51FF:
        return f"LM({(value >> 5) & 0xF}, {_mod_names(value & 0x1F)})"
    if 0x52A0 <= value <= 0x52BF:
        return f"OSM({_mod_names(value & 0x1F)})"
    for name, base in LAYER_FUNCTIONS.items():
        if base <= value <= base + 0x1F:
            return f"{name}({value - base})"
    return f"0x{value:04X}"


# ---------------------------------------------------------------------------
# USB connection


class PadError(Exception):
    pass


class Pad:
    def __init__(self):
        try:
            import hid
        except ImportError as e:
            raise PadError("The hidapi package isn't installed. Run: pip install -r requirements.txt") from e
        paths = [
            d["path"]
            for d in hid.enumerate(VENDOR_ID, PRODUCT_ID)
            if d["usage_page"] == RAW_USAGE_PAGE and d["usage"] == RAW_USAGE
        ]
        if not paths:
            if hid.enumerate(VENDOR_ID, PRODUCT_ID):
                raise PadError("Found the 2040pad, but it isn't running the VIA firmware. Flash 2040pad_via.uf2.")
            raise PadError("2040pad not found. Check that it's plugged in.")
        self.dev = hid.device()
        self.dev.open_path(paths[0])
        self.protocol = self._command(CMD_PROTOCOL_VERSION)
        self.protocol = (self.protocol[1] << 8) | self.protocol[2]
        self.layers = self._command(CMD_LAYER_COUNT)[1]

    def close(self):
        self.dev.close()

    def _command(self, *payload):
        msg = bytes(payload).ljust(REPORT_SIZE, b"\0")
        # The leading 0 is the HID report ID.
        if self.dev.write(b"\0" + msg) < 0:
            raise PadError("Couldn't send to the pad. Was it unplugged?")
        reply = bytes(self.dev.read(REPORT_SIZE, 1000))
        if len(reply) < 5:
            raise PadError("The pad didn't reply.")
        if reply[0] == CMD_UNHANDLED:
            raise PadError(f"The firmware doesn't support VIA command 0x{payload[0]:02X}.")
        if reply[0] != payload[0]:
            raise PadError("Got an unexpected reply from the pad.")
        return reply

    def get_key(self, layer, row, col):
        r = self._command(CMD_GET_KEYCODE, layer, row, col)
        return (r[4] << 8) | r[5]

    def set_key(self, layer, row, col, keycode):
        self._command(CMD_SET_KEYCODE, layer, row, col, keycode >> 8, keycode & 0xFF)

    def get_encoder(self, layer, clockwise):
        r = self._command(CMD_GET_ENCODER, layer, ENCODER_INDEX, int(clockwise))
        return (r[4] << 8) | r[5]

    def set_encoder(self, layer, clockwise, keycode):
        self._command(CMD_SET_ENCODER, layer, ENCODER_INDEX, int(clockwise), keycode >> 8, keycode & 0xFF)

    def reset_keymap(self):
        self._command(CMD_RESET_KEYMAP)

    # Uniform access by key name: k1-k12, enc, ccw, cw.
    def get(self, layer, key):
        if key in ("ccw", "cw"):
            return self.get_encoder(layer, key == "cw")
        _, row, col = _position(key)
        return self.get_key(layer, row, col)

    def set(self, layer, key, keycode):
        if key in ("ccw", "cw"):
            self.set_encoder(layer, key == "cw", keycode)
        else:
            _, row, col = _position(key)
            self.set_key(layer, row, col, keycode)

    def dump(self):
        return {
            "layers": [{key: format_keycode(self.get(layer, key)) for key in ALL_KEYS} for layer in range(self.layers)]
        }

    def load(self, data):
        layers = data["layers"]
        if len(layers) > self.layers:
            raise PadError(f"The file has {len(layers)} layers, but the pad has {self.layers}.")
        # Parse everything first, so a typo doesn't leave the pad half-written.
        parsed = [{k: parse_keycode(v) for k, v in layer.items() if k in ALL_KEYS} for layer in layers]
        for layer, keys in enumerate(parsed):
            for key, code in keys.items():
                self.set(layer, key, code)


ALL_KEYS = [k[0] for k in KEYS] + ["enc", "ccw", "cw"]


def _position(key):
    for entry in KEYS + [ENCODER_PRESS]:
        if entry[0] == key:
            return entry
    raise PadError(f"Unknown key {key!r}. Use k1-k12, enc, ccw or cw.")


# ---------------------------------------------------------------------------
# Window


TKINTER_HELP = """The window needs tkinter, which isn't installed for this Python.
tkinter comes from your operating system, not pip. Install it, then recreate the venv:

    Debian / Ubuntu / Raspberry Pi OS:  sudo apt install python3-tk python3-venv
    Fedora:                             sudo dnf install python3-tkinter
    Arch:                               sudo pacman -S tk
    macOS with Homebrew:                brew install python-tk@3.X  (3.X = your Python version)
    Windows:                            rerun the python.org installer and select "tcl/tk and IDLE"

Or skip tkinter and use the browser version: python padmap.py web
The command-line commands also work without it. Run: python padmap.py --help"""


def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print(TKINTER_HELP, file=sys.stderr)
        return 1

    root = tk.Tk()
    root.title("2040pad keymap")
    root.resizable(False, False)

    state = {"pad": None, "layer": 0, "selected": None}
    buttons = {}
    status = tk.StringVar(value="Not connected")
    layer_var = tk.StringVar(value="0")
    selected_var = tk.StringVar(value="Click a key to change it")
    code_var = tk.StringVar()
    preview_var = tk.StringVar()
    names = sorted(KEYCODES)

    top = ttk.Frame(root, padding=8)
    top.grid(row=0, column=0, sticky="ew")
    ttk.Label(top, textvariable=status).grid(row=0, column=0, columnspan=4, sticky="w")
    ttk.Label(top, text="Layer").grid(row=1, column=0, sticky="w", pady=(6, 0))
    layer_box = ttk.Combobox(top, textvariable=layer_var, width=4, state="readonly", values=["0"])
    layer_box.grid(row=1, column=1, sticky="w", pady=(6, 0))

    grid = ttk.Frame(root, padding=(8, 0))
    grid.grid(row=1, column=0)
    labels = {"enc": "Encoder press", "ccw": "Turn left", "cw": "Turn right"}
    for col, key in enumerate(["ccw", "enc", "cw"]):
        ttk.Label(grid, text=labels[key]).grid(row=0, column=col, pady=(4, 0))
    for name, row, col in KEYS:
        ttk.Label(grid, text=name).grid(row=row * 2, column=col, pady=(4, 0))

    def make_button(key, row, col):
        b = tk.Button(grid, width=16, height=2, wraplength=120, relief="groove", command=lambda: select(key))
        b.grid(row=row, column=col, padx=3, pady=1)
        buttons[key] = b

    for col, key in enumerate(["ccw", "enc", "cw"]):
        make_button(key, 1, col)
    for name, row, col in KEYS:
        make_button(name, row * 2 + 1, col)

    edit = ttk.Frame(root, padding=8)
    edit.grid(row=2, column=0, sticky="ew")
    ttk.Label(edit, textvariable=selected_var).grid(row=0, column=0, columnspan=3, sticky="w")
    entry = ttk.Combobox(edit, textvariable=code_var, width=32, values=names)
    entry.grid(row=1, column=0, sticky="w")
    assign = ttk.Button(edit, text="Send to pad")
    assign.grid(row=1, column=1, padx=6)
    ttk.Label(edit, textvariable=preview_var, foreground="#555").grid(row=2, column=0, columnspan=3, sticky="w")

    bottom = ttk.Frame(root, padding=8)
    bottom.grid(row=3, column=0, sticky="ew")

    def pad():
        if state["pad"] is None:
            raise PadError("Not connected. Click Connect.")
        return state["pad"]

    def report(err):
        status.set(str(err))
        messagebox.showerror("2040pad", str(err))

    def refresh():
        try:
            p = pad()
            for key in ALL_KEYS:
                buttons[key].config(text=format_keycode(p.get(state["layer"], key)))
        except (PadError, OSError) as e:
            disconnect()
            report(e)

    def connect(quiet=False):
        disconnect()
        try:
            p = Pad()
        except (PadError, OSError) as e:
            if quiet:
                status.set(str(e))
            else:
                report(e)
            return
        state["pad"] = p
        layer_box.config(values=[str(i) for i in range(p.layers)])
        status.set(f"Connected: VIA protocol 0x{p.protocol:04X}, {p.layers} layers. Changes save instantly.")
        refresh()

    def disconnect():
        if state["pad"] is not None:
            try:
                state["pad"].close()
            except OSError:
                pass
        state["pad"] = None
        for b in buttons.values():
            b.config(text="")
        status.set("Not connected")

    def select(key):
        if state["selected"]:
            buttons[state["selected"]].config(relief="groove")
        state["selected"] = key
        buttons[key].config(relief="sunken")
        where = labels.get(key, key)
        selected_var.set(f"Layer {state['layer']}, {where}: type a keycode, then Send")
        code_var.set(buttons[key].cget("text"))
        entry.focus_set()
        entry.select_range(0, "end")

    def on_type(_event=None):
        text = code_var.get().strip()
        upper = text.upper()
        entry.config(values=[n for n in names if upper in n][:200] if text else names)
        try:
            value = parse_keycode(text)
            preview_var.set(f"= 0x{value:04X}  {format_keycode(value)}")
        except ValueError as e:
            preview_var.set(str(e) if text else "")

    def send(_event=None):
        key = state["selected"]
        if not key:
            report("Click a key first.")
            return
        try:
            value = parse_keycode(code_var.get())
        except ValueError as e:
            report(e)
            return
        try:
            p = pad()
            p.set(state["layer"], key, value)
            readback = p.get(state["layer"], key)
        except (PadError, OSError) as e:
            disconnect()
            report(e)
            return
        buttons[key].config(text=format_keycode(readback))
        ok = readback == value
        status.set(f"Saved {format_keycode(readback)} to layer {state['layer']}, {labels.get(key, key)}" if ok
                   else "The pad stored a different value than sent.")

    def change_layer(_event=None):
        state["layer"] = int(layer_var.get())
        if state["selected"]:
            select(state["selected"])
        refresh()

    def export():
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Keymap", "*.json")])
        if path:
            try:
                Path(path).write_text(json.dumps(pad().dump(), indent=2) + "\n", encoding="utf8")
                status.set(f"Saved keymap to {path}")
            except (PadError, OSError) as e:
                report(e)

    def import_():
        path = filedialog.askopenfilename(filetypes=[("Keymap", "*.json")])
        if not path or not messagebox.askyesno("2040pad", "Write this keymap to the pad, replacing the current one?"):
            return
        try:
            pad().load(json.loads(Path(path).read_text(encoding="utf8")))
            status.set(f"Loaded {path} onto the pad")
        except (PadError, OSError, ValueError, KeyError) as e:
            report(e)
        refresh()

    def reset():
        if messagebox.askyesno("2040pad", "Reset every layer to the keymap built into the firmware?"):
            try:
                pad().reset_keymap()
                status.set("Keymap reset to the firmware default")
            except (PadError, OSError) as e:
                report(e)
            refresh()

    for i, (text, fn) in enumerate(
        [("Connect", connect), ("Reload", refresh), ("Save to file", export), ("Load file", import_), ("Reset keymap", reset)]
    ):
        ttk.Button(bottom, text=text, command=fn).grid(row=0, column=i, padx=2)

    assign.config(command=send)
    entry.bind("<Return>", send)
    entry.bind("<KeyRelease>", on_type)
    entry.bind("<<ComboboxSelected>>", on_type)
    layer_box.bind("<<ComboboxSelected>>", change_layer)
    if not KEYCODES:
        status.set("keycodes.json is missing. Run gen_keycodes.py.")
    root.after(100, lambda: connect(quiet=True))
    root.mainloop()
    return 0


# ---------------------------------------------------------------------------
# Browser page, served from this computer only


def run_web(port=0, open_browser=True):
    """Serve padmap_web.html and a small JSON API on 127.0.0.1 until Ctrl+C."""
    import http.server
    import secrets
    import urllib.parse
    import webbrowser

    page = Path(__file__).with_name("padmap_web.html").read_text(encoding="utf8")
    # Every request must carry this token, so other websites open in the
    # browser can't change the keymap through this server.
    token = secrets.token_urlsafe(24)
    session = {"pad": None, "hosts": set()}

    def get_pad():
        if session["pad"] is None:
            session["pad"] = Pad()
        return session["pad"]

    def drop_pad():
        if session["pad"] is not None:
            try:
                session["pad"].close()
            except OSError:
                pass
        session["pad"] = None

    def state(layer):
        try:
            p = get_pad()
            layer = min(max(layer, 0), p.layers - 1)
            keys = {k: format_keycode(p.get(layer, k)) for k in ALL_KEYS}
        except (PadError, OSError) as e:
            drop_pad()
            return {"connected": False, "error": str(e)}
        return {"connected": True, "protocol": f"0x{p.protocol:04X}", "layers": p.layers, "layer": layer, "keys": keys}

    def check_key(key):
        if key not in ALL_KEYS:
            raise ValueError(f"Unknown key {key!r}")
        return key

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _reply(self, status, body, content_type="application/json"):
            data = body.encode("utf8") if isinstance(body, str) else json.dumps(body).encode("utf8")
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if content_type == "text/html":
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'",
                )
            self.end_headers()
            self.wfile.write(data)

        def _allowed(self, need_token):
            # The Host check blocks DNS rebinding; the token blocks requests from other sites.
            if self.headers.get("Host", "") not in session["hosts"]:
                self._reply(403, {"error": "Requests must come from this computer."})
                return False
            if need_token and not secrets.compare_digest(self.headers.get("X-Padmap-Token", ""), token):
                self._reply(403, {"error": "Missing or wrong token. Reload the page."})
                return False
            return True

        def _run(self, action):
            try:
                self._reply(200, action())
            except ValueError as e:
                self._reply(400, {"error": str(e)})
            except (PadError, OSError) as e:
                drop_pad()
                self._reply(503, {"error": str(e)})

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            arg = lambda name, default="": query.get(name, [default])[0]  # noqa: E731
            if url.path == "/":
                if self._allowed(need_token=False):
                    self._reply(200, page.replace("{{TOKEN}}", token), "text/html")
                return
            if not self._allowed(need_token=True):
                return
            if url.path == "/api/state":
                self._run(lambda: state(int(arg("layer", "0") or 0)))
            elif url.path == "/api/keycodes":
                self._run(lambda: sorted(KEYCODES))
            elif url.path == "/api/parse":
                def parse():
                    try:
                        value = parse_keycode(arg("code"))
                    except ValueError as e:
                        return {"ok": False, "error": str(e)}
                    return {"ok": True, "value": f"0x{value:04X}", "name": format_keycode(value)}
                self._run(parse)
            elif url.path == "/api/dump":
                self._run(lambda: get_pad().dump())
            else:
                self._reply(404, {"error": "Not found"})

        def do_POST(self):
            if not self._allowed(need_token=True):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1_000_000:
                    raise ValueError("Request too large")
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object")
            except ValueError as e:
                self._reply(400, {"error": f"Bad request: {e}"})
                return
            path = urllib.parse.urlsplit(self.path).path

            def set_key():
                layer, key = int(body.get("layer", 0)), check_key(body.get("key", ""))
                value = parse_keycode(str(body.get("code", "")))
                p = get_pad()
                if not 0 <= layer < p.layers:
                    raise ValueError(f"Layer must be 0-{p.layers - 1}")
                p.set(layer, key, value)
                readback = p.get(layer, key)
                return {"name": format_keycode(readback), "matches": readback == value}

            def load():
                data = body.get("data")
                try:
                    get_pad().load(data)
                except (KeyError, TypeError, AttributeError) as e:
                    raise ValueError("That file isn't a padmap keymap.") from e
                return {"ok": True}

            def reset():
                get_pad().reset_keymap()
                return {"ok": True}

            def connect():
                drop_pad()
                return state(int(body.get("layer", 0)))

            routes = {"/api/set": set_key, "/api/load": load, "/api/reset": reset, "/api/connect": connect}
            if path in routes:
                self._run(routes[path])
            else:
                self._reply(404, {"error": "Not found"})

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    port = server.server_address[1]
    session["hosts"] = {f"127.0.0.1:{port}", f"localhost:{port}"}
    url = f"http://127.0.0.1:{port}/"
    print(f"padmap is running at {url}", flush=True)
    print("Keep this window open while you use the page. Press Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        drop_pad()
        server.server_close()
    return 0


# ---------------------------------------------------------------------------
# Command line


def main(argv):
    if not argv:
        return run_gui()
    cmd, args = argv[0], argv[1:]
    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if cmd == "web":
        port, open_browser = 0, True
        rest = list(args)
        while rest:
            opt = rest.pop(0)
            if opt == "--no-browser":
                open_browser = False
            elif opt == "--port" and rest and rest[0].isdigit():
                port = int(rest.pop(0))
            else:
                print("Usage: padmap.py web [--port N] [--no-browser]", file=sys.stderr)
                return 2
        return run_web(port, open_browser)
    try:
        pad = Pad()
        if cmd == "info":
            print(f"VIA protocol 0x{pad.protocol:04X}, {pad.layers} layers, keycodes from QMK {KEYCODES_QMK_VERSION}")
        elif cmd == "dump":
            text = json.dumps(pad.dump(), indent=2)
            if args:
                Path(args[0]).write_text(text + "\n", encoding="utf8")
            else:
                print(text)
        elif cmd == "load" and len(args) == 1:
            pad.load(json.loads(Path(args[0]).read_text(encoding="utf8")))
            print("Loaded.")
        elif cmd == "set" and len(args) >= 3:
            layer, key, code = int(args[0]), args[1].lower(), parse_keycode(" ".join(args[2:]))
            pad.set(layer, key, code)
            print(f"Layer {layer} {key} = {format_keycode(pad.get(layer, key))}")
        else:
            print(__doc__)
            return 2
    except (PadError, ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
