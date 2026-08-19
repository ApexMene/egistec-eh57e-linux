#!/usr/bin/env python3
"""Does mosaicking beat keeping the placements as separate templates?

The literature on small-area sensors says the answer to too little contact area
is not a cleverer matcher but a bigger template: register the partial impressions
against each other and fuse them into one composite, then match once against
that. It is the standard recommendation, and a June 2026 report restates it for
phone-sized sensors as "accumulative fingerprint mapping".

That is worth testing here rather than believing, for two reasons specific to
this sensor.

The first is that classic mosaicking registers impressions by their minutiae,
and this sensor barely has any -- 8 bozorth3 points on the same finger, against
a threshold of 40. Registration has to go through correlation instead, which is
exactly the operation that has already been measured to align near-parallel
ridges with the wrong finger when given too much freedom.

The second is that a bigger template is also a bigger target: whatever extra
freedom helps the genuine finger find its place also helps an impostor. So the
comparison has to carry the impostors along, not just the genuine scores.

Protocol identical to matching_protocol.py, so the numbers can be put side by
side: enrol placements 1 and 2, verify with placement 3.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from matching_protocol import DATI, DITA, H, W, carica, filtra

# Il composito deve poter crescere in ogni direzione rispetto al primo appoggio.
MARGINE = 34
CH, CW = H + 2 * MARGINE, W + 2 * MARGINE

# Sotto questa sovrapposizione un confronto normalizzato non vuol dire niente:
# due ritagli piccoli di righe parallele somigliano sempre.
MIN_OVERLAP = 1500


def campione(finger, n, bg, media=120):
    f = carica(os.path.join(DATI, f"set-{finger}-{n}.bin"), bg)
    if len(f) < media:
        return None
    i = (len(f) - media) // 2
    return filtra(f[i:i + media].mean(axis=0))


def correla_su_tela(tela, peso, p, dy, dx):
    """Correlazione normalizzata fra il composito e p spostato di (dy, dx).

    Solo dove il composito ha davvero dei dati: le zone mai toccate non devono
    entrare nel conto, altrimenti si misura la forma della tela invece del dito.
    """
    y0, x0 = MARGINE + dy, MARGINE + dx
    if y0 < 0 or x0 < 0 or y0 + H > CH or x0 + W > CW:
        return None

    m = peso[y0:y0 + H, x0:x0 + W] > 0
    if m.sum() < MIN_OVERLAP:
        return None

    a = tela[y0:y0 + H, x0:x0 + W][m]
    b = p[m]
    a = a - a.mean()
    b = b - b.mean()
    d = a.std() * b.std()
    if d < 1e-6:
        return None

    return float((a * b).mean() / d)


def miglior_posizione(tela, peso, p, r):
    best = (-2.0, 0, 0)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            v = correla_su_tela(tela, peso, p, dy, dx)
            if v is not None and v > best[0]:
                best = (v, dy, dx)
    return best


def deposita(tela, peso, p, dy, dx):
    y0, x0 = MARGINE + dy, MARGINE + dx
    tela[y0:y0 + H, x0:x0 + W] += p
    peso[y0:y0 + H, x0:x0 + W] += 1.0


def costruisci(pezzi, soglia_aggancio, r=30):
    """Primo pezzo al centro, gli altri agganciati se il picco e' convincente.

    Un aggancio sbagliato e' peggio di un pezzo scartato: incolla pelle nel posto
    sbagliato e sporca il composito per sempre.
    """
    somma = np.zeros((CH, CW))
    peso = np.zeros((CH, CW))
    deposita(somma, peso, pezzi[0], 0, 0)
    agganciati = 1

    for p in pezzi[1:]:
        media = np.divide(somma, peso, out=np.zeros_like(somma), where=peso > 0)
        v, dy, dx = miglior_posizione(media, peso, p, r)
        if v >= soglia_aggancio and abs(dy) < r and abs(dx) < r:
            deposita(somma, peso, p, dy, dx)
            agganciati += 1

    media = np.divide(somma, peso, out=np.zeros_like(somma), where=peso > 0)
    return media, peso, agganciati


def punteggio(tela, peso, prova, r=30):
    return miglior_posizione(tela, peso, prova, r)[0]


def main():
    bg = np.fromfile(os.path.join(DATI, "set-fondo.bin"),
                     dtype=np.uint8).astype(np.float64).reshape(H, W)

    pezzi = {d: [campione(d, n, bg) for n in (1, 2)] for d in DITA}
    prove = {d: campione(d, 3, bg) for d in DITA}

    for soglia in (0.35, 0.50, 0.65):
        compositi = {}
        for d in DITA:
            compositi[d] = costruisci(pezzi[d], soglia)

        gen, imp = [], []
        for isc in DITA:
            tela, peso, _ = compositi[isc]
            for pres in DITA:
                s = punteggio(tela, peso, prove[pres])
                (gen if isc == pres else imp).append(s)

        gen = np.array(gen)
        imp = np.array(imp)
        tutte = np.sort(np.concatenate([gen, imp]))
        errori = min(int((gen < t).sum() + (imp >= t).sum()) for t in tutte)
        pezzi_usati = sum(compositi[d][2] for d in DITA)

        print(f"soglia di aggancio {soglia:.2f}: "
              f"pezzi agganciati {pezzi_usati}/10  "
              f"genuino peggiore {gen.min():.3f}  medio {gen.mean():.3f}  "
              f"impostore migliore {imp.max():.3f}  errori {errori}/25")

    print("\nriferimento, modelli separati (stesso protocollo):")
    print("  genuino peggiore 0.241  medio 0.565  "
          "impostore migliore 0.451  errori 1/25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
