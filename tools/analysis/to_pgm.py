#!/usr/bin/env python3
"""Genera le varianti di elaborazione da raw-fondo.bin / raw-dito*.bin.

L'idea e' separare due domande che finora si sono mescolate:
  1. come si costruisce l'immagine (fondo sottratto? come si normalizza?);
  2. a che scala e con quale polarita' NBIS ci trova le minuzie.

Qui si risponde alla prima e si scrivono dei PGM; a rispondere alla seconda ci
pensa mintest, che le prova tutte senza rimettere il dito sul sensore.
"""

import numpy as np

W, H = 70, 57
CROP = 1                       # pixman vuole il passo di riga multiplo di 4
OUTW = 68


def leggi(nome):
    return np.fromfile(nome, dtype=np.uint8).astype(np.float64).reshape(H, W)


def taglia(a):
    return a[:, CROP:CROP + OUTW]


def stira_percentili(a, lo_p=2, hi_p=98):
    lo, hi = np.percentile(a, [lo_p, hi_p])
    if hi <= lo:
        return np.zeros_like(a, dtype=np.uint8)
    return np.clip((a - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)


def equalizza(a):
    """Equalizzazione dell'istogramma: usa tutti i livelli in modo uniforme,
    utile quando il contrasto e' molto disomogeneo fra centro e bordi."""
    h, _ = np.histogram(a.ravel(), bins=256, range=(0, 256))
    cdf = h.cumsum().astype(np.float64)
    cdf = (cdf - cdf.min()) / max(cdf[-1] - cdf.min(), 1) * 255
    return cdf[a.astype(np.uint8)].astype(np.uint8)


def salva(nome, a):
    a = np.asarray(a, dtype=np.uint8)
    with open(nome, "wb") as f:
        f.write(f"P5\n{a.shape[1]} {a.shape[0]}\n255\n".encode())
        f.write(a.tobytes())
    print(f"  {nome}  {a.shape[1]}x{a.shape[0]}  "
          f"media={a.mean():.1f} sd={a.std():.1f}")


def main():
    bg = leggi("raw-fondo.bin")
    dito = leggi("raw-dito.bin")
    med = leggi("raw-dito-mediana.bin")

    print("varianti:")

    # 1. il frame grezzo, solo stirato. E' quello che si vedeva in dz-dito.png
    salva("v1-grezza.pgm", stira_percentili(taglia(dito)))

    # 2. mediana dei frame col dito: meno rumore temporale (sd ~3.4 per frame)
    salva("v2-mediana.pgm", stira_percentili(taglia(med)))

    # 3. fondo sottratto: toglie il pattern fisso dell'array, che da solo vale
    #    36 di deviazione spaziale su 255
    salva("v3-menofondo.pgm", stira_percentili(taglia(med - bg)))

    # 4. fondo sottratto ed equalizzato
    salva("v4-equalizzata.pgm", equalizza(stira_percentili(taglia(med - bg))))

    # 5. fondo sottratto, stirato piu' aggressivamente: se le creste occupano
    #    poco dell'istogramma, i percentili larghi le comprimono
    salva("v5-menofondo-10-90.pgm",
          stira_percentili(taglia(med - bg), 10, 90))


if __name__ == "__main__":
    main()
