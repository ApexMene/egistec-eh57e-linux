#!/usr/bin/env python3
"""Cattura frame con i setting che aprono il range dinamico e li salva in PNG.

Uso: python3 shoot.py <etichetta>
Tenere il dito premuto (o no, a seconda della prova) per tutta la durata.
"""

import importlib.util
import statistics
import struct
import sys
import zlib

spec = importlib.util.spec_from_file_location("cap", "capture-057e.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

W, H = 70, 57
REAL = W * H
SCALE = 6

# (registro, valore) che nello sweep hanno alzato varianza e range
SETTINGS = [
    ("base", []),
    ("r21ff", [(0x21, 0xFF)]),
    ("r2520", [(0x25, 0x20)]),
    ("r2220", [(0x22, 0x20)]),
    ("r12ff", [(0x12, 0xFF)]),
    ("r2a80", [(0x2A, 0x80)]),
    ("r2820", [(0x28, 0x20)]),
    ("r07ff", [(0x07, 0xFF)]),
]


def png_gray(path, data, w, h, scale=1):
    """PNG 8-bit in scala di grigi, senza dipendenze esterne."""
    rows = []
    for y in range(h):
        line = data[y * w:(y + 1) * w]
        if scale > 1:
            line = bytes(b for px in line for _ in range(scale) for b in (px,))
        for _ in range(scale):
            rows.append(b"\x00" + line)
    raw = b"".join(rows)

    def chunk(tag, payload):
        c = struct.pack(">I", len(payload)) + tag + payload
        return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w * scale, h * scale, 8, 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def stretch(data):
    """Normalizza sul range presente: senza questo un'impronta a basso
    contrasto resta invisibile."""
    lo, hi = min(data), max(data)
    if hi == lo:
        return data
    return bytes((b - lo) * 255 // (hi - lo) for b in data)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    dev = cap.open_dev()
    ok, tot = cap.init(dev)
    print(f"init: {ok}/{tot}\n")

    for name, writes in SETTINGS:
        for reg, val in writes:
            cap.cmd(dev, f"4547495361{reg:02x}{val:02x}")
        cap.grab(dev)              # frame di assestamento
        f = cap.grab(dev)[:REAL]
        if len(f) < REAL:
            print(f"  {name}: frame corto ({len(f)})")
            continue
        var = statistics.pvariance(f)
        print(f"  {name}: var={var:9.2f} min={min(f):3d} max={max(f):3d} "
              f"distinti={len(set(f)):3d}")
        png_gray(f"shot-{label}-{name}.png", stretch(f), W, H, SCALE)
        open(f"shot-{label}-{name}.bin", "wb").write(f)
        # ripristina rileggendo l'init completo, cosi' ogni setting parte pulito
        if writes:
            cap.init(dev)

    print(f"\nsalvati shot-{label}-*.png")
    cap.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
