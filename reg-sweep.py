#!/usr/bin/env python3
"""Trova i registri che controllano guadagno/esposizione.

L'immagine esce con range dinamico ~18 livelli su 256: l'AFE non e' pilotato.
Per ogni registro candidato proviamo alcuni valori e misuriamo come cambiano
range e varianza del frame. Quello che muove le statistiche e' il guadagno.
"""

import importlib.util
import statistics
import sys

spec = importlib.util.spec_from_file_location("cap", "capture-057e.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

# l'immagine utile sono i primi 3990 byte (70x57), il resto e' padding 0x75
REAL = 70 * 57

CANDIDATES = [0x05, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
              0x10, 0x11, 0x12, 0x13, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25,
              0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b, 0x35, 0x50]
VALUES = [0x00, 0x20, 0x40, 0x80, 0xC0, 0xFF]


def stats(dev):
    f = cap.grab(dev)[:REAL]
    if len(f) < REAL:
        return None
    return statistics.pvariance(f), min(f), max(f), statistics.fmean(f)


def read_regs(dev, regs):
    out = {}
    for r in regs:
        resp = cap.cmd(dev, f"4547495360{r:02x}00")
        if len(resp) >= 7:
            out[r] = resp[5]
    return out


def main():
    dev = cap.open_dev()
    ok, tot = cap.init(dev)
    print(f"init: {ok}/{tot}")

    before = read_regs(dev, CANDIDATES)
    base = stats(dev)
    print(f"baseline: var={base[0]:.2f} min={base[1]} max={base[2]} "
          f"media={base[3]:.1f} range={base[2]-base[1]}\n")

    print(f"{'reg':>5s} {'orig':>5s}  " + "".join(f"{v:#04x}:range/var".rjust(18) for v in VALUES))
    hits = []
    for reg in CANDIDATES:
        orig = before.get(reg, 0)
        row = []
        for val in VALUES:
            cap.cmd(dev, f"4547495361{reg:02x}{val:02x}")
            s = stats(dev)
            row.append(s)
        # ripristina
        cap.cmd(dev, f"4547495361{reg:02x}{orig:02x}")

        cells = "".join(f"{(s[2]-s[1]) if s else -1:5d}/{(s[0] if s else 0):8.2f}".rjust(18)
                        for s in row)
        print(f"{reg:#05x} {orig:#05x}  {cells}")

        ranges = [s[2] - s[1] for s in row if s]
        if ranges and (max(ranges) - min(ranges)) > 20:
            hits.append((reg, min(ranges), max(ranges)))

    print("\n--- registri che muovono il range dinamico ---")
    if hits:
        for reg, lo, hi in sorted(hits, key=lambda h: h[1] - h[2]):
            print(f"  reg {reg:#04x}: range da {lo} a {hi}")
    else:
        print("  nessuno: il guadagno non e' su questi registri, oppure serve")
        print("  un comando di ricalibrazione dopo la scrittura.")

    cap.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
