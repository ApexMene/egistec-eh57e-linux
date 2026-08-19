#!/usr/bin/env python3
"""Sweep dei registri AFE 0x09-0x13 cercando chi elimina lo zero ogni 4 byte.

L'init che usiamo e' quello del 0576: il burst write
  63 09 0b 83 24 00 44 0f 08 20 20 00 00 52
carica i registri 0x09..0x13, e la rilettura conferma che si applicano.
Ma sul 057e il frame torna a gruppi di 4 byte con 3 dati e 1 zero: sembra
che un quarto dei canali di lettura resti spento. Qui cerchiamo il registro
che lo controlla.

Metrica: percentuale di zeri nel frame. Il baseline e' 25%.
"""

import importlib.util

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

REGS = list(range(0x09, 0x14))
VALUES = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xC0, 0xFF]

# valori che l'init del 0576 lascia nei registri, per il ripristino
BASE = {0x09: 0x83, 0x0A: 0x24, 0x0B: 0x00, 0x0C: 0x44, 0x0D: 0x0F,
        0x0E: 0x08, 0x0F: 0x20, 0x10: 0x20, 0x11: 0x00, 0x12: 0x00,
        0x13: 0x52}


def measure(dev):
    c2.wr(dev, 0x2C, 0x00)
    f = c2.get_frame(dev)
    if len(f) < c2.FRAME:
        return None
    z = sum(1 for b in f if b == 0) * 100.0 / len(f)
    nz = [b for b in f if b]
    return dict(zeros=z, distinct=len(set(f)),
                mean=sum(nz) / max(1, len(nz)),
                lo=min(nz) if nz else 0, hi=max(nz) if nz else 0)


def main():
    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    print(f"init: {ok}/{tot}")

    base = measure(dev)
    print(f"baseline: zeri={base['zeros']:.1f}% distinti={base['distinct']} "
          f"mean={base['mean']:.1f} range={base['lo']}-{base['hi']}\n")

    hits = []
    for reg in REGS:
        for val in VALUES:
            if val == BASE.get(reg):
                continue
            c2.wr(dev, reg, val)
            m = measure(dev)
            if m is None:
                c2.wr(dev, reg, BASE[reg])
                continue
            flag = ""
            # ci interessa chi si allontana dal 25% di zeri mantenendo
            # una scala di grigi vera (non 2-3 livelli di corruzione)
            if abs(m["zeros"] - 25.0) > 5 and m["distinct"] >= 8:
                flag = "  <<<"
                hits.append((reg, val, m))
            print(f"  reg {reg:#04x} = {val:#04x}: zeri={m['zeros']:5.1f}% "
                  f"distinti={m['distinct']:3d} mean={m['mean']:6.1f} "
                  f"range={m['lo']:3d}-{m['hi']:3d}{flag}")
            c2.wr(dev, reg, BASE[reg])
        c2.init(dev)

    print(f"\n--- {len(hits)} candidati ---")
    for reg, val, m in hits:
        print(f"  reg {reg:#04x} = {val:#04x}  zeri={m['zeros']:.1f}% "
              f"distinti={m['distinct']}")

    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
