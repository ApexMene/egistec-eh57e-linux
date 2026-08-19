#!/usr/bin/env python3
"""Geometria del frame, ricavata dai dati invece che dal disassemblato.

Da stream-period.py sappiamo che lo stream si ripete esattamente ogni 5320
byte e che **non c'e' byte di padding** (zeri per residuo mod 4 = [0,0,0,0]).
Quindi il frame e' di 5320 campioni, non di 3990: l'ipotesi "3 byte utili su 4"
valeva per la lettura a richieste singole, non per lo stream.

Qui si cerca:
  1. se i blocchi da 5320 sono davvero identici byte per byte (frame fermo)
     oppure differiscono (scansione viva);
  2. la larghezza di riga, dal primo picco di autocorrelazione dentro un frame:
     le righe di un sensore d'immagine si somigliano fra loro, quindi il passo
     di riga si vede come picco a ritardo piccolo.
"""

import sys

import numpy as np


def autocorr(x):
    x = x.astype(np.float64)
    x -= x.mean()
    n = 1 << int(np.ceil(np.log2(len(x) * 2)))
    f = np.fft.rfft(x, n)
    ac = np.fft.irfft(f * np.conj(f), n)[:len(x)]
    ac = ac / np.arange(len(x), 0, -1)
    return ac / ac[0] if ac[0] else ac


def analizza(path, periodo=5320):
    d = np.fromfile(path, dtype=np.uint8)
    print(f"\n===== {path}: {len(d)} byte =====")
    nfr = len(d) // periodo
    fr = d[:nfr * periodo].reshape(nfr, periodo)

    # 1. i frame sono identici?
    diff = [(int(np.count_nonzero(fr[i] != fr[i + 1])),
             float(np.abs(fr[i].astype(int) - fr[i + 1].astype(int)).max()))
            for i in range(min(6, nfr - 1))]
    print(f"  {nfr} frame da {periodo}")
    for i, (n, m) in enumerate(diff):
        print(f"    frame {i} vs {i+1}: {n} byte diversi, delta max {m:.0f}")
    tutti = np.count_nonzero(fr[:-1] != fr[1:])
    print(f"    in totale {tutti} byte diversi su {(nfr-1)*periodo}")

    # 2. struttura interna: larghezza di riga
    f0 = fr[0]
    print(f"  frame 0: media={f0.mean():.2f} sd={f0.std():.2f} "
          f"min={f0.min()} max={f0.max()} livelli={len(np.unique(f0))}")
    ac = autocorr(f0)
    lo, hi = 8, min(1200, len(ac) - 1)
    seg = ac[lo:hi]
    ordine = np.argsort(seg)[::-1]
    visti = []
    print("  picchi interni (candidati passo di riga):")
    for i in ordine:
        lag = int(i) + lo
        if any(abs(lag - v) < 4 for v in visti):
            continue
        visti.append(lag)
        div = "" if periodo % lag else f"  -> {periodo // lag} righe"
        print(f"    lag={lag:5d}  corr={seg[i]:+.4f}{div}")
        if len(visti) >= 8:
            break

    # 3. divisori plausibili di 5320
    print(f"  divisori di {periodo}:")
    dd = [w for w in range(32, 401) if periodo % w == 0]
    print("    " + ", ".join(f"{w}x{periodo // w}" for w in dd))


def main():
    for p in sys.argv[1:] or ["stream-reg0x02.bin"]:
        try:
            analizza(p)
        except FileNotFoundError:
            print(f"manca {p}")


if __name__ == "__main__":
    main()
