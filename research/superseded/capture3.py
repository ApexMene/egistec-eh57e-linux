#!/usr/bin/env python3
"""Cattura corretta: geometria e trasporto ricavati dai dati, non dal binario.

Cosa era sbagliato prima (capture2.py):

  * si assumeva un frame di 70x57 = 3990 pixel trasportati in 5320 byte, con
    3 byte utili ogni 4 e un byte di padding da scartare (`depad`);
  * in realta' nello stream **non c'e' padding**: gli zeri per residuo mod 4
    sono [0,0,0,0]. `depad` sceglieva un residuo a caso, buttava via un quarto
    dei campioni e sfasava tutto il resto.

Da qui l'errore che ci ha bloccati: due frame consecutivi, entrambi mutilati e
sfasati in modo diverso, non correlavano (r ~ 0.02) e si concludeva che
l'array non venisse scandito.

Cosa dicono i dati (stream-period.py, frame-geom.py):

  * lo stream si ripete esattamente ogni **5320 byte**;
  * dentro il frame l'autocorrelazione ha picchi a 70, 140, 210, 280...:
    il passo di riga e' **70**;
  * le righe 0..56 hanno segnale (sd 1.5-2.4, 7-13 livelli), le righe 57..75
    valgono tutte **117 esatto** (sd 0.00, un livello solo).

Quindi: **70 x 57 = 3990 pixel**, piu' 1330 byte di coda costante = 5320.
Le costanti prese dal disassemblato del driver Windows erano giuste; era
sbagliato il modello di trasporto. Con la lettura corretta due catture
indipendenti correlano a **r = +0.95** invece di +0.02: il fixed-pattern
noise c'e', l'array viene scandito.

Uso:
    ./capture3.py                 # due catture consecutive + correlazione
    ./capture3.py --frames 6      # piu' frame
    ./capture3.py --stream        # un'unica richiesta, frame consecutivi
"""

import argparse
import importlib.util
import time

import numpy as np
import usb.core
import usb.util

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

# Il blocco che arriva e' di 5320 byte, ma solo i primi 3990 sono pixel:
# le righe 57..75 valgono tutte 117 esatto (sd = 0.00, un solo livello).
# Il padding esiste, ma sta **in coda**, non intercalato ogni 4 byte come
# assumeva depad() in capture2.py.
W, H = 70, 57
PIX = W * H            # 3990 pixel veri
BLOCCO = 5320          # byte per frame sul filo, coda compresa


def apri(tent=8):
    ultimo = None
    for _ in range(tent):
        try:
            return c2.open_dev()
        except Exception as e:                      # noqa: BLE001
            ultimo = e
            time.sleep(1.2)
    raise RuntimeError(f"sensore non riapribile: {ultimo}")


def arma(dev):
    c2.wr(dev, 0x02, 0x0F)
    c2.wr(dev, 0x02, 0x2F)


def leggi(dev, quanti):
    """Legge quanti byte grezzi dallo stream, senza togliere nulla."""
    buf = bytearray()
    last = time.time()
    while len(buf) < quanti and (time.time() - last) < 2.0:
        try:
            chunk = dev.read(c2.EP_IN, min(16384, quanti - len(buf)),
                             timeout=300)
        except usb.core.USBError:
            continue
        if chunk:
            buf.extend(chunk)
            last = time.time()
    return bytes(buf)


def una_richiesta(dev, nframes=1):
    """Arma, chiede l'immagine, legge nframes frame consecutivi."""
    c2.drain(dev)
    arma(dev)
    dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(BLOCCO)), timeout=1000)
    d = leggi(dev, BLOCCO * nframes)
    n = len(d) // BLOCCO
    if n == 0:
        return []
    # si tiene solo la parte con i pixel, la coda costante si butta
    return [np.frombuffer(d[i * BLOCCO:i * BLOCCO + PIX], dtype=np.uint8)
            for i in range(n)]


def corr(a, b):
    a = a.astype(np.float64) - a.mean()
    b = b.astype(np.float64) - b.mean()
    den = (np.dot(a, a) * np.dot(b, b)) ** 0.5
    return float(np.dot(a, b) / den) if den else 0.0


def salva(nome, f):
    c2.png_gray(nome, c2.stretch(bytes(f)), W, H, scale=6)


def descrivi(i, f):
    print(f"  frame {i}: media={f.mean():6.2f} sd={f.std():5.2f} "
          f"min={f.min():3d} max={f.max():3d} livelli={len(np.unique(f))}",
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=4)
    ap.add_argument("--prefisso", default="c3")
    ap.add_argument("--stream", action="store_true",
                    help="tutti i frame da una sola richiesta")
    a = ap.parse_args()

    frames = []
    if a.stream:
        dev = apri()
        try:
            c2.init(dev)
            frames = una_richiesta(dev, a.frames)
        finally:
            usb.util.release_interface(dev, 0)
    else:
        # ogni frame da una richiesta separata, con re-arming: e' il caso in
        # cui prima misuravamo r ~ 0.02 per colpa di depad
        for _ in range(a.frames):
            dev = apri()
            try:
                c2.init(dev)
                got = una_richiesta(dev, 1)
                if got:
                    frames.append(got[0])
            finally:
                try:
                    usb.util.release_interface(dev, 0)
                except Exception:                   # noqa: BLE001
                    pass

    if not frames:
        print("nessun frame letto")
        return 1

    print(f"{len(frames)} frame da {PIX} pixel ({W}x{H}), blocco sul filo {BLOCCO}")
    for i, f in enumerate(frames):
        descrivi(i, f)
        salva(f"{a.prefisso}-{i}.png", f)

    print("\ncorrelazione fra frame consecutivi:")
    for i in range(len(frames) - 1):
        n = int(np.count_nonzero(frames[i] != frames[i + 1]))
        print(f"  {i} vs {i+1}: r={corr(frames[i], frames[i+1]):+.4f}  "
              f"({n} byte diversi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
