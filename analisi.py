#!/usr/bin/env python3
"""Falsi accessi e falsi rifiuti misurati, non stimati a occhio.

Protocollo: si iscrivono gli appoggi 1 e 2 di ogni dito, si verifica con il 3.
Il terzo appoggio non entra mai nell'iscrizione, altrimenti si misurerebbe
quanto il confronto sa riconoscere se stesso, che e' sempre benissimo.

Punteggio di un confronto: massima correlazione normalizzata fra il campione da
verificare e uno qualsiasi dei modelli iscritti, provando tutti gli scorrimenti
entro qualche pixel. E' il massimo perche' cosi' funziona una verifica vera:
basta che combaci con uno dei modelli.

Prima del confronto ogni fotogramma passa per un passabanda attorno al periodo
delle creste (8 pixel, cioe' 0.125 cicli/pixel, misurato il 18/08). Sotto quella
banda c'e' la pressione del dito, che cambia a ogni appoggio e non dice niente
sull'identita'; sopra c'e' il rumore termico. Senza il filtro il margine fra
stesso dito e dita diverse si chiude quasi del tutto.
"""

import argparse
import itertools

import numpy as np

W, H = 70, 57
PIX = W * H
DITA = ["indice-dx", "medio-dx", "anulare-dx", "pollice-dx", "indice-sx"]

_fy = np.fft.fftfreq(H)[:, None]
_fx = np.fft.fftfreq(W)[None, :]
_rad = np.sqrt(_fy ** 2 + _fx ** 2)
BANDA = np.exp(-((_rad - 0.125) ** 2) / (2 * 0.045 ** 2))


def carica(nome, bg, soglia=25.0):
    a = np.fromfile(nome, dtype=np.uint8)
    f = a[:len(a) // PIX * PIX].reshape(-1, H, W).astype(np.float64) - bg
    return f[np.abs(f).mean(axis=(1, 2)) > soglia]


def filtra(p):
    p = np.fft.ifft2(np.fft.fft2(p - p.mean()) * BANDA).real
    s = p.std()
    return p / s if s > 1e-6 else p


def campioni(f, k, media):
    """k campioni presi lungo l'appoggio, ognuno media di `media` fotogrammi.

    Mediare abbatte il rumore termico senza spostare niente, visto che il dito
    sta fermo. Prenderne piu' d'uno serve perche' durante gli otto secondi la
    pressione cambia, e un modello solo non copre quella variabilita'."""
    if len(f) < media:
        return []
    idx = np.linspace(0, len(f) - media, k).astype(int)
    return [filtra(f[i:i + media].mean(axis=0)) for i in idx]


def somiglianza(a, b, r):
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
                v = float((A * B).mean() / d)
                if v > best:
                    best = v
    return best


def punteggio(prova, modelli, r):
    return max(somiglianza(p, m, r) for p in prova for m in modelli)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelli", type=int, default=8,
                    help="campioni per appoggio iscritto")
    ap.add_argument("--prove", type=int, default=3,
                    help="campioni per appoggio di verifica")
    ap.add_argument("--media", type=int, default=40,
                    help="fotogrammi mediati per campione")
    ap.add_argument("--scorrimento", type=int, default=8,
                    help="scorrimento massimo in pixel")
    a = ap.parse_args()

    bg = np.fromfile("set-fondo.bin", dtype=np.uint8).astype(np.float64)
    bg = bg.reshape(H, W)

    iscritti, prove = {}, {}
    for d in DITA:
        m = []
        for n in (1, 2):
            m += campioni(carica(f"set-{d}-{n}.bin", bg), a.modelli, a.media)
        iscritti[d] = m
        prove[d] = campioni(carica(f"set-{d}-3.bin", bg), a.prove, a.media)
        print(f"{d:12s} modelli {len(m):3d}   prove {len(prove[d])}")

    print("\npunteggi (riga = dito iscritto, colonna = dito presentato)\n")
    print(f"{'':14s}" + "".join(f"{d[:9]:>11s}" for d in DITA))

    genuini, impostori = [], []
    for isc in DITA:
        riga = f"{isc:14s}"
        for pres in DITA:
            s = punteggio(prove[pres], iscritti[isc], a.scorrimento)
            riga += f"{s:11.3f}"
            (genuini if isc == pres else impostori).append(s)
        print(riga)

    g = np.array(genuini)
    i = np.array(impostori)
    print(f"\ngenuini   n={len(g):2d}  min {g.min():.3f}  media {g.mean():.3f}"
          f"  max {g.max():.3f}")
    print(f"impostori n={len(i):2d}  min {i.min():.3f}  media {i.mean():.3f}"
          f"  max {i.max():.3f}")

    if g.min() > i.max():
        s = (g.min() + i.max()) / 2
        print(f"\nSEPARANO. Nessuna sovrapposizione, soglia {s:.3f} "
              f"(margine {g.min() - i.max():.3f})")
    else:
        print(f"\nNON separano: il peggior genuino ({g.min():.3f}) sta sotto "
              f"il miglior impostore ({i.max():.3f}).")

    print("\nsoglia   falsi rifiuti   falsi accessi")
    for s in np.arange(0.30, 0.85, 0.05):
        fr = int((g < s).sum())
        fa = int((i >= s).sum())
        print(f" {s:.2f}      {fr:2d}/{len(g):<2d}          {fa:2d}/{len(i)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
