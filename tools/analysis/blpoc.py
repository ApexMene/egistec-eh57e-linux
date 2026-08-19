#!/usr/bin/env python3
"""BLPOC contro la correlazione incrociata: quale separa meglio?

BLPOC (band-limited phase-only correlation) e' il metodo classico di riferimento
per i sensori di piccola area, che e' esattamente il caso nostro. L'idea: invece
di moltiplicare i due segnali, si prende lo spettro incrociato e se ne butta via
il modulo, tenendo solo la fase.

    R(u,v) = F(u,v) * conj(G(u,v)) / |F(u,v) * conj(G(u,v))|

Cosi' due immagini della stessa zona di pelle danno, antitrasformando, un picco
stretto nel punto che dice di quanto sono spostate, e l'altezza del picco non
dipende da quanto forte hai premuto: il modulo, cioe' il contrasto, e' stato
buttato via. Con la correlazione normale invece la pressione entra nel conto.

"Band-limited" perche' si tengono solo le frequenze basse: sopra c'e' rumore, e
la fase del rumore e' rumore puro, che abbassa il picco senza aggiungere niente.

Due vantaggi pratici oltre alla robustezza: il picco si trova in un colpo solo
su TUTTI gli scorrimenti, senza il ciclo annidato che fa la correlazione attuale,
e l'ampiezza di ricerca non e' piu' un parametro da tarare.

Il confronto e' a parita' di protocollo con analisi.py: si iscrivono gli appoggi
1 e 2 di ogni dito, si verifica con il 3, e il punteggio e' il massimo fra tutte
le coppie campione-modello.
"""

import os
import sys

# Le catture stanno in data/, e questo file sta due livelli sotto la radice.
RADICE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATI = os.path.join(RADICE, "data")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse

import numpy as np

from matching_protocol import DITA, H, W, carica

# Finestra di Hann separabile. Senza, i bordi dell'immagine si comportano come
# un gradino: la trasformata di un gradino ha energia a tutte le frequenze e
# sporca la fase proprio dove ci serve pulita.
_FIN = np.outer(np.hanning(H), np.hanning(W))


def prepara(p):
    p = p - p.mean()
    s = p.std()
    if s > 1e-6:
        p = p / s
    return p * _FIN


def maschera(ku, kv):
    """Tiene le frequenze entro +-ku in orizzontale e +-kv in verticale.

    Il periodo delle creste misurato e' 8 pixel, cioe' 0.125 cicli/pixel: su 70
    colonne fanno 8.75 cicli. La banda deve comprendere quella riga, quindi ku
    sotto 9 taglia via proprio il segnale che identifica il dito.
    """
    u = np.fft.fftfreq(W) * W
    v = np.fft.fftfreq(H) * H
    return (np.abs(v)[:, None] <= kv) & (np.abs(u)[None, :] <= ku)


def punteggio_coppia(F, G, m, n_tenute):
    R = F * np.conj(G)
    a = np.abs(R)
    R = np.where(a > 1e-12, R / (a + 1e-12), 0.0)
    R = R * m
    r = np.fft.ifft2(R).real
    # Normalizzato sul numero di coefficienti tenuti: cosi' il picco vale 1 per
    # due immagini identiche, indipendentemente da quanto stretta e' la banda.
    return float(r.max()) * H * W / n_tenute


def matrice(iscritti, prove, ku, kv, silenzioso=False):
    m = maschera(ku, kv)
    n = int(m.sum())

    F = {d: [np.fft.fft2(prepara(x)) for x in prove[d]] for d in DITA}
    Gm = {d: [np.fft.fft2(prepara(x)) for x in iscritti[d]] for d in DITA}

    genuini, impostori = [], []
    righe = []
    for isc in DITA:
        riga = []
        for pres in DITA:
            s = max(punteggio_coppia(f, g, m, n)
                    for f in F[pres] for g in Gm[isc])
            riga.append(s)
            (genuini if isc == pres else impostori).append(s)
        righe.append(riga)

    if not silenzioso:
        print(f"{'':14s}" + "".join(f"{d[:9]:>11s}" for d in DITA))
        for d, riga in zip(DITA, righe):
            print(f"{d:14s}" + "".join(f"{v:11.3f}" for v in riga))

    return np.array(genuini), np.array(impostori)


def campiona(f, k, media):
    if len(f) < media:
        return []
    idx = np.linspace(0, len(f) - media, k).astype(int)
    return [f[i:i + media].mean(axis=0) for i in idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelli", type=int, default=8)
    ap.add_argument("--prove", type=int, default=3)
    ap.add_argument("--media", type=int, default=40)
    a = ap.parse_args()

    bg = np.fromfile(os.path.join(DATI, "set-fondo.bin"), dtype=np.uint8).astype(np.float64)
    bg = bg.reshape(H, W)

    iscritti, prove = {}, {}
    for d in DITA:
        m = []
        for n in (1, 2):
            m += campiona(carica(os.path.join(DATI, f"set-{d}-{n}.bin"), bg), a.modelli, a.media)
        iscritti[d] = m
        prove[d] = campiona(carica(f"set-{d}-3.bin", bg), a.prove, a.media)

    print("banda    genuino peggiore   genuino medio   impostore migliore"
          "   margine")
    migliore = None
    for ku, kv in ((6, 5), (9, 7), (12, 10), (16, 13), (20, 16), (34, 28)):
        g, i = matrice(iscritti, prove, ku, kv, silenzioso=True)
        margine = g.min() - i.max()
        print(f"{ku:2d}x{kv:<2d}    {g.min():14.3f}  {g.mean():14.3f}"
              f"  {i.max():19.3f}  {margine:+8.3f}")
        if migliore is None or margine > migliore[0]:
            migliore = (margine, ku, kv)

    _, ku, kv = migliore
    print(f"\nmatrice alla banda migliore ({ku}x{kv}):\n")
    g, i = matrice(iscritti, prove, ku, kv)

    print(f"\ngenuini   min {g.min():.3f}  media {g.mean():.3f}")
    print(f"impostori max {i.max():.3f}")
    print("\nper confronto, la correlazione incrociata attuale:")
    print("genuini   min 0.230  media 0.573")
    print("impostori max 0.454")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
