#!/usr/bin/env python3
"""Quanti modelli iscritti separano meglio indice e medio?

Il punteggio di una verifica e' il massimo su tutti i modelli iscritti. Il
massimo di N estrazioni cresce con N anche quando non c'e' segnale: il dito
giusto non ha bisogno di N tentativi, gli basta quello buono, mentre il dito
sbagliato ne guadagna eccome.

Sul ferro il sospetto ha un riscontro netto: lo stesso medio ha fatto 0.303
contro due modelli iscritti e 0.734 contro trenta, entrando in un prompt di
polkit. Se la relazione regge, esiste un numero di modelli oltre il quale
iscrivere di piu' peggiora, e trenta e' oltre.

Qui si usano le catture etichettate g01-*.bin, registrate un dito alla volta con
l'etichetta fissata prima: la sessione precedente aveva prodotto una conclusione
sbagliata perche' cinque verifiche guidate da messaggi in un terminale non
guardato avevano scambiato un indice per un medio.

Protocollo: si iscrivono gli appoggi 1 e 2 dell'indice, si verifica con
l'appoggio 3 dell'indice (genuino) e con i tre appoggi del medio (impostore).
L'appoggio 3 non entra mai nell'iscrizione.
"""

import os
import sys

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
DATI = os.path.join(RADICE, "data")

W, H = 70, 57
PIX = W * H

_fy = np.fft.fftfreq(H)[:, None]
_fx = np.fft.fftfreq(W)[None, :]
_rad = np.sqrt(_fy ** 2 + _fx ** 2)
BANDA = np.exp(-((_rad - 0.125) ** 2) / (2 * 0.045 ** 2))
RIGHE_RUMORE = _rad > 0.30
RIGHE_CRESTE = (_rad > 0.08) & (_rad < 0.18)


def carica(nome):
    a = np.fromfile(os.path.join(DATI, nome), dtype=np.uint8)
    return a[:len(a) // PIX * PIX].reshape(-1, H, W).astype(np.float64)


def filtra(p):
    p = np.fft.ifft2(np.fft.fft2(p - p.mean()) * BANDA).real
    s = p.std()
    return p / s if s > 1e-6 else p


def modelli(frames, k, media=40):
    """k modelli distribuiti lungo l'appoggio."""
    if len(frames) < media:
        return []
    idx = np.linspace(0, len(frames) - media, k).astype(int)
    return [filtra(frames[i:i + media].mean(axis=0)) for i in idx]


def saturazione(frames):
    return 100.0 * float(((frames <= 1) | (frames >= 254)).mean())


def somiglianza(a, b, r=8):
    best = -1.0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            A = a[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)]
            B = b[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
            if A.size < 1500:
                continue
            A = A - A.mean()
            B = B - B.mean()
            d = A.std() * B.std()
            if d > 1e-6:
                best = max(best, float((A * B).mean() / d))
    return best


def main():
    bg = np.fromfile(os.path.join(DATI, "g01-fondo.bin"),
                     dtype=np.uint8).astype(np.float64).reshape(H, W)

    grezzi = {}
    for nome in ("indice", "medio"):
        for n in (1, 2, 3):
            f = f"g01-{nome}-{n}.bin"
            if not os.path.exists(os.path.join(DATI, f)):
                sys.exit(f"manca {f}: la cattura non e' completa")
            grezzi[(nome, n)] = carica(f)

    print("qualita' delle catture")
    print(f"{'appoggio':16s} {'satura%':>8s} {'SNR dB':>8s}")
    for k, v in grezzi.items():
        img = v.mean(axis=0)
        F = np.abs(np.fft.fft2(img - img.mean())) ** 2
        snr = 10 * np.log10(F[RIGHE_CRESTE].mean() / max(F[RIGHE_RUMORE].mean(), 1e-9))
        print(f"{k[0]}-{k[1]:<14d} {saturazione(v):8.1f} {snr:8.1f}")

    sotto = {k: v - bg for k, v in grezzi.items()}

    print("\nseparazione al variare del numero di modelli iscritti")
    print(f"{'modelli':>8s} {'genuino':>9s} {'imp.max':>9s} {'imp.medio':>10s}"
          f" {'margine':>9s}")

    for per_appoggio in (1, 2, 4, 8, 15, 30):
        isc = (modelli(sotto[("indice", 1)], per_appoggio)
               + modelli(sotto[("indice", 2)], per_appoggio))
        if not isc:
            continue

        prove_gen = modelli(sotto[("indice", 3)], 3)
        prove_imp = []
        for n in (1, 2, 3):
            prove_imp += modelli(sotto[("medio", n)], 2)

        gen = max(somiglianza(p, m) for p in prove_gen for m in isc)
        imp = [max(somiglianza(p, m) for m in isc) for p in prove_imp]
        imp = np.array(imp)

        print(f"{len(isc):8d} {gen:9.3f} {imp.max():9.3f} {imp.mean():10.3f}"
              f" {gen - imp.max():+9.3f}")

    print("\nIl margine e' genuino meno il miglior impostore: sopra zero le due"
          "\npopolazioni si separano, sotto zero no. Un margine che cala al"
          "\ncrescere dei modelli conferma che la galleria grande regala"
          "\noccasioni al dito sbagliato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
