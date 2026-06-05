from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.seed_codec import seed_to_string, string_to_seed

EDEN_LOG = [
    ("BGDM 9DPK", 107593840, 107, (58, 531)),
    ("VVDX T9MP", 3509077760, 150, (719, 471)),
    ("A3BW PYXX", 162289967, None, (383, 257)),
    ("8CW2 V6TA", 4283101711, None, (130, 732)),
    ("4WNT QT20", 3681970362, 133, (136, 46)),
    ("YBDL FXSF", 2947145011, None, (484, 118)),
]


def main() -> None:
    print(f"{'seed':<12}{'u32':>12}{'trinket':>8}  items  decode")
    for seed_str, u32, trinket, items in EDEN_LOG:
        dec = string_to_seed(seed_str)
        tri = str(trinket) if trinket is not None else "-"
        enc = seed_to_string(u32)
        note = "" if enc == seed_str else f" enc={enc}"
        ok = "OK" if dec == u32 else "FAIL"
        print(f"{seed_str:<12}{u32:>12}{tri:>8}  {items[0]},{items[1]}  {ok}{note}")


if __name__ == "__main__":
    main()
