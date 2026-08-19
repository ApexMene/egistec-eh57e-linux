#!/usr/bin/env python3
"""Bisezione fra l'init 0576 (che produce un'immagine) e quello ricostruito
per il 057e (che produce un frame nero). Cambia una cosa per volta.

Serve a capire quale delle differenze estratte dal driver rompe la lettura:
la sostituzione 0x10 -> 0x0a, il reg 0x50, oppure i burst 0x11 / 0x34.
"""

import importlib.util
import statistics

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

BASE = list(c2.INIT_SEQUENCE)          # init 0576, funzionante


def swap(seq, old, new):
    return [new if c == old else c for c in seq]


def with_0a(seq):
    """rampa di bias sul registro 0x0a invece che sul 0x10"""
    s = swap(seq, "454749536110fd", "45474953610afd")
    s = swap(s, "454749536110fc", "45474953610afc")
    return swap(s, "454749536110f4", "45474953610af4")


def with_50_44(seq):
    return swap(seq, "45474953615003", "45474953615044")


def with_bursts(seq):
    out = []
    for c in seq:
        out.append(c)
        if c == "45474953632606066006052f06" and \
                "45474953631103010072" not in out:
            out.append("45474953631103010072")   # burst 0x11 = 01 00 72
            out.append("454749536334020701")     # burst 0x34 = 07 01
    return out


VARIANTS = [
    ("A  0576 puro", BASE),
    ("B  0x10 -> 0x0a", with_0a(BASE)),
    ("C  B + reg 0x50 = 0x44", with_50_44(with_0a(BASE))),
    ("D  B + burst 0x11/0x34", with_bursts(with_0a(BASE))),
    ("E  0576 + reg 0x50 = 0x44", with_50_44(BASE)),
    ("F  0576 + burst 0x11/0x34", with_bursts(BASE)),
]


def run(dev, seq, gain=0x0A):
    ok = 0
    for c in seq:
        if c == "FLUSH":
            c2.cmd(dev, c2.img_req(c2.WIRE), read_len=c2.WIRE, timeout=1500)
            c2.drain(dev)
            ok += 1
            continue
        if c2.cmd(dev, c)[:4] == b"SIGE":
            ok += 1
    c2.wr(dev, 0x12, gain)
    c2.wr(dev, 0x2C, 0x00)
    f = c2.get_frame(dev)
    return ok, len(seq), f


def main():
    dev = c2.open_dev()
    for name, seq in VARIANTS:
        # reset pulito fra una variante e l'altra
        c2.init(dev)
        ok, tot, f = run(dev, seq)
        if len(f) != c2.FRAME:
            print(f"  {name:28s} init {ok}/{tot}  frame corto ({len(f)})")
            continue
        print(f"  {name:28s} init {ok}/{tot}  var={statistics.pvariance(f):8.2f} "
              f"mean={sum(f)/len(f):6.1f} min={min(f):3d} max={max(f):3d} "
              f"distinti={len(set(f)):3d}")
        c2.png_gray(f"bis-{name.split()[0]}.png", c2.stretch(f), c2.W, c2.H)
    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
