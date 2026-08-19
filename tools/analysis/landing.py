#!/usr/bin/env python3
"""L'inizio dell'appoggio vale quanto il resto?

Il driver, appena la distanza dal fondo supera la soglia, media i 40 fotogrammi
successivi e li usa come campione. Sono i primi quattro decimi di secondo di
contatto: il dito sta ancora scendendo, la pressione sale, la pelle si appiattisce.

Se quel momento fosse peggiore del resto dell'appoggio, spiegherebbe il rifiuto
su tre verifiche misurato il 19/08 (0.358 contro 0.625 e 0.595) senza tirare in
ballo la soglia.

Le catture di set-*.bin durano otto secondi ciascuna e contengono l'appoggio
intero, quindi la domanda si risponde con i dati che ci sono gia': si confronta
la finestra iniziale con finestre prese piu' avanti, contro modelli costruiti
dagli ALTRI appoggi dello stesso dito.
"""

import os
import sys

# Le catture stanno in data/, e questo file sta due livelli sotto la radice.
RADICE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATI = os.path.join(RADICE, "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from matching_protocol import DITA, H, PIX, W, campioni, carica, filtra, somiglianza

MEDIA = 40
SCORR = 8


def finestra(f, inizio):
    return filtra(f[inizio:inizio + MEDIA].mean(axis=0))


def main():
    bg = np.fromfile(os.path.join(DATI, "set-fondo.bin"), dtype=np.uint8).astype(np.float64)
    bg = bg.reshape(H, W)

    print(f"{'dito':12s} {'appoggio':>8s} {'inizio':>8s} {'meta':>8s} {'fine':>8s}")

    tutti = {"inizio": [], "meta": [], "fine": []}

    for d in DITA:
        f = {n: carica(os.path.join(DATI, f"set-{d}-{n}.bin"), bg) for n in (1, 2, 3)}

        for n in (1, 2, 3):
            # I modelli vengono dagli altri due appoggi: confrontare un appoggio
            # con se stesso direbbe solo che una cosa somiglia a se stessa.
            altri = []
            for m in (1, 2, 3):
                if m != n:
                    altri += campioni(f[m], 8, MEDIA)

            cur = f[n]
            if len(cur) < MEDIA * 3:
                continue

            punti = {}
            for nome, inizio in (("inizio", 0),
                                 ("meta", (len(cur) - MEDIA) // 2),
                                 ("fine", len(cur) - MEDIA)):
                w = finestra(cur, inizio)
                v = max(somiglianza(w, m, SCORR) for m in altri)
                punti[nome] = v
                tutti[nome].append(v)

            print(f"{d:12s} {n:>8d} {punti['inizio']:>8.3f} "
                  f"{punti['meta']:>8.3f} {punti['fine']:>8.3f}")

    print()
    for nome in ("inizio", "meta", "fine"):
        a = np.array(tutti[nome])
        print(f"{nome:8s} media {a.mean():.3f}  peggiore {a.min():.3f}")

    ini = np.array(tutti["inizio"])
    resto = np.concatenate([tutti["meta"], tutti["fine"]])
    print(f"\ndifferenza media inizio - resto: {ini.mean() - resto.mean():+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
