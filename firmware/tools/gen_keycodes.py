"""Generate keycodes.json from a QMK checkout, so padmap.py matches the firmware's keycodes.

Usage:
    python gen_keycodes.py C:/Users/Avery/qmk_firmware

Rerun this after updating QMK, because keycode numbers can change between QMK versions.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import padmap  # noqa: E402

HEADERS = [
    "quantum/keycodes.h",
    "quantum/modifiers.h",
    "quantum/quantum_keycodes.h",
    "quantum/keymap_extras/keymap_us.h",
]

ENUM_ENTRY = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*,", re.M)
ENUM_ALIAS = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*([A-Z][A-Z0-9_]*)\s*,", re.M)
DEFINE = re.compile(r"^\s*#\s*define\s+([A-Z][A-Z0-9_]*)\s+([^\n]+?)\s*(?://.*)?$")
RANGES_ENUM = re.compile(r"enum\s+qk_keycode_ranges\s*\{(.*?)\};", re.S)

# Range markers and modifier masks, not keycodes in their own right.
NOT_KEYCODES = re.compile(r"^(MOD_|QK_[LR](CTL|SFT|ALT|GUI)$|QK_RMODS_MIN$|SAFE_RANGE$)|_MAX$|_MIN$")


def collect(qmk: Path):
    values, exprs, ranges = {}, {}, set()
    for rel in HEADERS:
        text = (qmk / rel).read_text(encoding="utf8")
        for name, number in ENUM_ENTRY.findall(text):
            values[name] = int(number, 0)
        for name, target in ENUM_ALIAS.findall(text):
            exprs.setdefault(name, target)
        m = RANGES_ENUM.search(text)
        if m:
            ranges.update(n for n, _ in ENUM_ENTRY.findall(m.group(1)))
        for line in text.splitlines():
            d = DEFINE.match(line)
            if d and "(" not in line.split(d.group(1), 1)[1][:1]:
                exprs.setdefault(d.group(1), d.group(2).strip())
    return values, exprs, ranges


def resolve(values, exprs):
    # Defines may refer to each other, so repeat until nothing new resolves.
    changed = True
    while changed:
        changed = False
        for name, expr in exprs.items():
            if name in values:
                continue
            try:
                values[name] = padmap.parse_keycode(expr, values, values)
                changed = True
            except ValueError:
                pass
    return values


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    qmk = Path(sys.argv[1])
    values, exprs, ranges = collect(qmk)
    values = resolve(values, exprs)
    mods = {n: v for n, v in values.items() if re.fullmatch(r"MOD_(L|R)(CTL|SFT|ALT|GUI)|MOD_(HYPR|MEH)", n)}
    keycodes = {
        n: v
        for n, v in values.items()
        if 0 <= v <= 0xFFFF and n not in ranges and not NOT_KEYCODES.search(n)
    }
    version = subprocess.run(
        ["git", "-C", str(qmk), "log", "-1", "--format=%h %cs"], capture_output=True, text=True
    ).stdout.strip() or "unknown"
    out = Path(__file__).with_name("keycodes.json")
    data = {"qmk_version": version, "mods": dict(sorted(mods.items())), "keycodes": dict(sorted(keycodes.items()))}
    out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf8")
    print(f"wrote {len(keycodes)} keycodes and {len(mods)} modifiers from QMK {version} to {out}")


if __name__ == "__main__":
    main()
