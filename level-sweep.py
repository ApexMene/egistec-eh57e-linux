#!/usr/bin/env python3
"""Sweep di guadagno e offset per portare il segnale a meta' scala.

Perche' serve: con `0x12 = 0x0a` l'immagine di fondo ha media 23 su 255, cioe'
sta appoggiata al fondo scala dell'ADC. Li' il dito modula qualcosa che finisce
sotto il rumore di quantizzazione, e infatti l'autocorrelazione della media di
120 frame col dito ha un picco solo a lag 1 (+0.29) e zero a lag 70: nessuna
struttura spaziale, solo rumore correlato fra campioni adiacenti.

Il driver non usa valori fissi: al reg 0x12 scrive 0x0a e poi *decrementa* il
reg 0x0f finche' il livello letto col burst 0x67 non scende sotto 0x80. Qui si
esplora la griglia (guadagno, offset) misurando dove il fondo si posiziona.

Non serve il dito: gira tutto a sensore libero.
"""

import importlib.util
import statistics

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

GAINS = [0x0A, 0x10, 0x18, 0x20, 0x30, 0x40, 0x60, 0x80]
OFFSETS = [0x00, 0x10, 0x20, 0x30, 0x40, 0x60, 0x80, 0xC0, 0xFF]


def frame_stats(dev):
    c2.wr(dev, 0x2C, 0x00)
    f = c2.get_frame(dev)
    if len(f) != c2.FRAME:
        return None
    return (statistics.mean(f), statistics.pstdev(f), len(set(f)),
            min(f), max(f))


def main():
    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    print(f"init {ok}/{tot}\n")
    print(f"{'gain':>5} {'off':>5} {'media':>7} {'sd':>6} {'liv':>4} "
          f"{'min':>4} {'max':>4}")

    best = []
    for g in GAINS:
        for o in OFFSETS:
            c2.wr(dev, c2.REG_GAIN, g)
            c2.wr(dev, c2.REG_OFFSET, o)
            s = frame_stats(dev)
            if s is None:
                print(f"{g:#05x} {o:#05x}   frame corto")
                continue
            mean, sd, lv, lo, hi = s
            print(f"{g:#05x} {o:#05x} {mean:7.1f} {sd:6.2f} {lv:4d} "
                  f"{lo:4d} {hi:4d}", flush=True)
            # si cerca il fondo piu' vicino a meta' scala, con piu' livelli
            best.append((abs(mean - 128), -lv, g, o, mean, sd, lv))

    best.sort()
    print("\n  migliori (fondo vicino a 128, molti livelli):")
    for _, nlv, g, o, mean, sd, lv in best[:8]:
        print(f"   gain={g:#04x} off={o:#04x}  media={mean:6.1f} "
              f"sd={sd:5.2f} livelli={lv}")

    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
