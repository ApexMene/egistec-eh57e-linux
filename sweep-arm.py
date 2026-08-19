#!/usr/bin/env python3
"""Sweep completo del registro 0x12, l'unico che cambia modo di acquisizione.

Dopo il solo init il frame e' un DC piatto (media 112.4, 5 livelli). Scrivendo
`0x12 = 0x0a` diventa variabile (media 26, ~49 livelli). Quindi 0x12 non e' un
guadagno ma seleziona la modalita': 0x0a e' *una* modalita', non per forza
quella giusta.

Criterio, come in find-scan.py: la correlazione fra due frame consecutivi a
sensore libero. Se un valore accende davvero l'array, compare il fixed-pattern
noise e la correlazione salta da ~0.05 a valori alti.

I registri 0x28-0x39 sono gia' stati esclusi: 126 configurazioni tutte fra
0.02 e 0.065, indistinguibili dalla baseline.
"""

import importlib.util
import statistics

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

NF = 3


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    den = (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** 0.5
    return num / den if den else 0.0


def probe(dev):
    fs = []
    for _ in range(NF):
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) != c2.FRAME:
            return None
        fs.append(list(f))
    cs = [corr(fs[i], fs[i + 1]) for i in range(len(fs) - 1)]
    return (statistics.mean(cs), statistics.mean(fs[0]),
            statistics.pstdev(fs[0]), len(set(fs[0])), fs[0])


def main():
    dev = c2.open_dev()
    rows = []
    for val in range(256):
        c2.init(dev)
        c2.wr(dev, 0x12, val)
        r = probe(dev)
        if r is None:
            print(f"  0x12 = {val:#04x}  frame corto", flush=True)
            continue
        c, mean, sd, lv, f0 = r
        mark = "  <<<" if c > 0.20 else ""
        print(f"  0x12 = {val:#04x}  corr={c:+.3f} media={mean:6.1f} "
              f"sd={sd:5.2f} liv={lv:3d}{mark}", flush=True)
        rows.append((c, val, mean, sd, lv, f0))

    rows.sort(reverse=True)
    print("\n  migliori per correlazione fra frame:")
    for c, val, mean, sd, lv, f0 in rows[:10]:
        print(f"   0x12 = {val:#04x}  corr={c:+.3f} media={mean:6.1f} "
              f"sd={sd:5.2f} livelli={lv}")
        c2.png_gray(f"arm-{val:02x}.png", c2.stretch(bytes(f0)),
                    c2.W, c2.H, scale=4)

    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
