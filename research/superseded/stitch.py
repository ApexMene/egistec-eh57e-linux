#!/usr/bin/env python3
"""Mosaico dei fotogrammi di una passata.

Ogni fotogramma copre 4.3 x 3.6 mm, che sono due o tre minuzie: troppo poche
perche' bozorth3 decida qualcosa. Se pero' il dito scorre, fotogrammi
successivi guardano parti diverse del polpastrello, e messi in fila coprono
un'area molto piu' grande.

Lo spostamento fra due fotogrammi si stima per correlazione di fase: la
trasformata del prodotto incrociato normalizzato ha un picco esattamente allo
scostamento fra le due immagini. E' robusta al cambio di contrasto, che qui
c'e' eccome, perche' la pressione del dito varia durante la passata.

Uso:
    ./stitch.py                 # legge sw-frames.bin e sw-fondo.bin
"""

import argparse

import numpy as np

W, H = 70, 57
PIX = W * H


def leggi(sorgente):
    bg = np.fromfile("sw-fondo.bin", dtype=np.uint8).astype(np.float64)
    a = np.fromfile(sorgente, dtype=np.uint8)
    n = len(a) // PIX
    return bg.reshape(H, W), a[:n * PIX].reshape(n, H, W).astype(np.float64)


def finestra(f):
    """Smorza i bordi: senza, la correlazione di fase vede il salto ai margini
    e ci mette un picco falso all'origine."""
    return f * np.hanning(H)[:, None] * np.hanning(W)[None, :]


def spostamento(a, b, max_dy=20, max_dx=20):
    """Scostamento (dy, dx) che porta b su a, per correlazione di fase."""
    A = np.fft.fft2(finestra(a - a.mean()))
    B = np.fft.fft2(finestra(b - b.mean()))
    R = A * np.conj(B)
    m = np.abs(R)
    R = np.divide(R, m, out=np.zeros_like(R), where=m > 1e-9)
    c = np.fft.ifft2(R).real

    # si guarda solo entro uno spostamento plausibile: fra due fotogrammi
    # consecutivi il dito non salta mezzo sensore
    masch = np.full(c.shape, -np.inf)
    for dy in range(-max_dy, max_dy + 1):
        for dx in range(-max_dx, max_dx + 1):
            masch[dy % H, dx % W] = c[dy % H, dx % W]

    iy, ix = np.unravel_index(np.argmax(masch), c.shape)
    dy = iy if iy <= H // 2 else iy - H
    dx = ix if ix <= W // 2 else ix - W
    return int(dy), int(dx), float(c[iy, ix])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="sorgente", default="sw-frames.bin")
    ap.add_argument("--out", dest="uscita", default="mosaico.pgm")
    ap.add_argument("--soglia", type=float, default=15.0,
                    help="distanza dal fondo sopra cui c'e' il dito")
    ap.add_argument("--passo", type=int, default=8,
                    help="scostamento dal riferimento oltre cui se ne prende uno nuovo")
    ap.add_argument("--qualita", type=float, default=0.05,
                    help="picco di correlazione minimo per fidarsi della stima")
    a = ap.parse_args()

    bg, frames = leggi(a.sorgente)
    print(f"{len(frames)} fotogrammi")

    dist = np.abs(frames - bg).mean(axis=(1, 2))
    vivi = np.where(dist > a.soglia)[0]
    if len(vivi) < 3:
        print(f"solo {len(vivi)} fotogrammi col dito, niente da unire")
        return 1
    i0, i1 = vivi[0], vivi[-1]
    print(f"dito presente dai fotogrammi {i0} a {i1} ({i1 - i0 + 1})")

    seq = [frames[i] - bg for i in range(i0, i1 + 1)]

    # Posizione cumulata, misurata contro un fotogramma di riferimento e non
    # contro il precedente.
    #
    # Perche': la correlazione di fase qui restituisce interi. A 55 fotogrammi
    # al secondo e 16 pixel per millimetro, un dito che scorre a un millimetro
    # al secondo si sposta 0.3 pixel fra un fotogramma e il successivo, che
    # arrotondato fa zero. Sommando mille zeri si ottiene zero, ed e' esatta-
    # mente quello che e' successo alla prima versione: "corsa totale 0 righe"
    # su una passata in cui il dito si era mosso eccome.
    #
    # Tenendo fermo un riferimento finche' lo scostamento non supera qualche
    # pixel, ogni misura e' molto sopra il passo di quantizzazione, e in piu'
    # non si accumula l'errore di mille stime consecutive.
    pos = [(0, 0)]
    scarti = []
    rif = seq[0]
    rif_pos = (0, 0)
    for i in range(1, len(seq)):
        dy, dx, q = spostamento(rif, seq[i], max_dy=25, max_dx=25)
        if q < a.qualita:
            scarti.append(i)
            pos.append(pos[-1])
            continue
        y = rif_pos[0] + dy
        x = rif_pos[1] + dx
        pos.append((y, x))
        # nuovo riferimento quando ci si e' allontanati abbastanza da avere
        # ancora sovrapposizione ma una misura ben sopra il rumore
        if abs(dy) >= a.passo or abs(dx) >= a.passo:
            rif = seq[i]
            rif_pos = (y, x)

    ys = [p[0] for p in pos]
    xs = [p[1] for p in pos]
    print(f"corsa totale: {max(ys) - min(ys)} righe, {max(xs) - min(xs)} colonne")
    print(f"stime scartate: {len(scarti)} su {len(seq) - 1}")

    oy, ox = -min(ys), -min(xs)
    CH = max(ys) - min(ys) + H
    CW = max(xs) - min(xs) + W
    somma = np.zeros((CH, CW))
    conta = np.zeros((CH, CW))

    for f, (y, x) in zip(seq, pos):
        somma[y + oy:y + oy + H, x + ox:x + ox + W] += f
        conta[y + oy:y + oy + H, x + ox:x + ox + W] += 1

    mos = np.divide(somma, conta, out=np.zeros_like(somma), where=conta > 0)
    print(f"mosaico {CW}x{CH}, coperto {int((conta > 0).sum())} pixel su "
          f"{CH * CW}")

    lo, hi = np.percentile(mos[conta > 0], [2, 98])
    out = np.clip((mos - lo) * 255 / max(hi - lo, 1), 0, 255).astype(np.uint8)
    out[conta == 0] = 128

    # larghezza multipla di 4: e' quello che vuole pixman piu' avanti
    out = out[:, :out.shape[1] // 4 * 4]

    with open(a.uscita, "wb") as f:
        f.write(f"P5\n{out.shape[1]} {out.shape[0]}\n255\n".encode())
        f.write(out.tobytes())
    print(f"salvato {a.uscita} ({out.shape[1]}x{out.shape[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
