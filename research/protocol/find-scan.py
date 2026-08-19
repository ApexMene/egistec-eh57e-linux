#!/usr/bin/env python3
"""Cerca il registro che accende davvero la scansione dell'array.

Il criterio e' oggettivo e non richiede il dito: **la correlazione fra due
frame consecutivi a sensore libero**. Ogni sensore d'immagine reale ha un
fixed-pattern noise, cioe' una firma per pixel che si ripete identica frame
dopo frame, quindi due frame a vuoto devono correlare forte.

Con la configurazione attuale correlano r = 0.02, cioe' per niente: quello che
leggiamo e' rumore casuale dell'AFE, non l'array. Se un registro accende la
scansione, la correlazione deve salire di colpo.

Prova un valore per volta, ripristinando l'init fra un test e l'altro.
"""

import importlib.util
import statistics
import sys

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

REGS = list(range(0x28, 0x3A))
VALS = [0x01, 0x02, 0x04, 0x10, 0x40, 0x80, 0xFF]
NF = 3

# Senza questa scrittura il sensore resta nel livello DC piatto (media 112.4,
# 5 livelli): l'init da solo non produce un'immagine. Una prima versione di
# questo script la ometteva e ha misurato la modalita' di test per tutte e 140
# le configurazioni, baseline compresa. Va rimessa dopo ogni init.
REG_ARM, VAL_ARM = 0x12, 0x0A


def arm(dev):
    c2.init(dev)
    c2.wr(dev, REG_ARM, VAL_ARM)


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    den = (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** 0.5
    return num / den if den else 0.0


def probe(dev):
    """Correlazione media fra frame consecutivi + statistiche del primo."""
    fs = []
    for _ in range(NF):
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) != c2.FRAME:
            return None
        fs.append(list(f))
    cs = [corr(fs[i], fs[i + 1]) for i in range(len(fs) - 1)]
    return (statistics.mean(cs), statistics.mean(fs[0]),
            statistics.pstdev(fs[0]), len(set(fs[0])))


def main():
    dev = c2.open_dev()
    arm(dev)
    base = probe(dev)
    print(f"base: corr={base[0]:+.3f} media={base[1]:.1f} sd={base[2]:.2f} "
          f"livelli={base[3]}\n", flush=True)

    hits = []
    for reg in REGS:
        for val in VALS:
            arm(dev)
            c2.wr(dev, reg, val)
            r = probe(dev)
            if r is None:
                continue
            c, mean, sd, lv = r
            flag = "  <<<" if c > 0.25 else ""
            if c > 0.15 or flag:
                hits.append((c, reg, val, mean, sd, lv))
            print(f"  reg {reg:#04x} = {val:#04x}  corr={c:+.3f} "
                  f"media={mean:6.1f} sd={sd:5.2f} liv={lv:3d}{flag}",
                  flush=True)

    print("\n  candidati (correlazione fra frame piu' alta):")
    for c, reg, val, mean, sd, lv in sorted(hits, reverse=True)[:10]:
        print(f"   reg {reg:#04x} = {val:#04x}  corr={c:+.3f} "
              f"media={mean:6.1f} sd={sd:5.2f} livelli={lv}")

    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
