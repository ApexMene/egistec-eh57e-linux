#!/usr/bin/env python3
"""Tre passate di fila: indice, indice, medio.

Serve per il primo test di confronto vero. Con due sole passate dello stesso
dito non si dimostra niente: un confronto che risponde sempre "si'" passerebbe.
La terza passata, con un dito diverso, e' il controllo negativo.

Il fondo si misura una volta sola all'inizio: fra una passata e l'altra il
sensore non cambia, e rimisurarlo ogni volta obbligherebbe a togliere il dito
per venti secondi in piu' ogni giro.

Uscita: sw-fondo.bin, sw-1.bin, sw-2.bin, sw-3.bin
"""

import importlib.util
import subprocess
import time

import numpy as np
import usb.core
import usb.util

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

W, H = 70, 57
PIX = W * H
BLOCCO = 5320
RIARMA = "45474953632c020013"
GAIN, OFFSET = 0x0A, 0x20
NFRAMES = 1400          # ~25 s a 55 fotogrammi al secondo

PASSATE = [
    (1, "INDICE destro", "e' il modello di riferimento"),
    (2, "INDICE destro (di nuovo)", "deve combaciare con la prima"),
    (3, "MEDIO destro", "controllo negativo: deve essere rifiutato"),
]


def chiedi(testo):
    subprocess.run(["zenity", "--info", "--width=520",
                    "--title=Sensore impronte", "--text", testo], check=False)


def apri(tent=8):
    ultimo = None
    for _ in range(tent):
        try:
            return c2.open_dev()
        except Exception as e:                      # noqa: BLE001
            ultimo = e
            time.sleep(1.2)
    raise RuntimeError(f"sensore non riapribile: {ultimo}")


def leggi(dev, quanti, quiet=1.0):
    buf = bytearray()
    last = time.time()
    while len(buf) < quanti and (time.time() - last) < quiet:
        try:
            chunk = dev.read(c2.EP_IN, min(16384, quanti - len(buf)),
                             timeout=200)
        except usb.core.USBError:
            continue
        if chunk:
            buf.extend(chunk)
            last = time.time()
    return bytes(buf)


def frame(dev):
    c2.cmd(dev, RIARMA)
    dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(BLOCCO)), timeout=1000)
    d = leggi(dev, BLOCCO)
    if len(d) < PIX:
        return None
    return np.frombuffer(d[:PIX], dtype=np.uint8)


def passata(dev, bg, n, dito, scopo):
    chiedi(f"PASSATA {n} di 3 — {dito}\n({scopo})\n\n"
           "Clicca OK col dito ANCORA STACCATO.\n"
           "Appoggia dopo un secondo, poi FAI SCORRERE il dito\n"
           "per TUTTA la lunghezza del polpastrello: dalla punta\n"
           "fino alla prima piega, circa 1,5 cm, in 20 secondi.\n\n"
           "Movimento continuo e ben visibile, non un tremolio:\n"
           "deve passare sopra il CENTRO dell'impronta, dove\n"
           "stanno le biforcazioni. Un millimetro al secondo.\n\n"
           "Appoggia soltanto, NON premere.\n\n"
           "Ti avviso io quando puoi togliere il dito.")

    t0 = time.time()
    frames = [f for f in (frame(dev) for _ in range(NFRAMES)) if f is not None]
    dt = time.time() - t0

    chiedi(f"Passata {n} finita — puoi TOGLIERE il dito.")

    a = np.stack(frames)
    a.tofile(f"sw-{n}.bin")
    dist = np.abs(a.astype(np.float64) - bg).mean(axis=1)
    print(f"passata {n} ({dito}): {len(frames)} frame in {dt:.1f}s, "
          f"{int((dist > 15).sum())} col dito, "
          f"distanza {dist.min():.1f}..{dist.max():.1f}")


def main():
    dev = apri()
    try:
        ok, tot = c2.init(dev)
        c2.wr(dev, c2.REG_GAIN, GAIN)
        c2.wr(dev, c2.REG_OFFSET, OFFSET)
        print(f"init {ok}/{tot}, gain {GAIN:#04x}")
        c2.drain(dev)

        chiedi("Prima il fondo.\n\nNON toccare il sensore. Clicca OK.")
        bg = np.median(np.stack([f.astype(np.float64)
                                 for f in (frame(dev) for _ in range(20))
                                 if f is not None]), axis=0)
        bg.astype(np.uint8).tofile("sw-fondo.bin")
        print("fondo salvato")

        for n, dito, scopo in PASSATE:
            passata(dev, bg, n, dito, scopo)

        chiedi("Tutte e tre fatte. Puoi lasciare stare il sensore.")
        print("salvati sw-fondo.bin, sw-1.bin, sw-2.bin, sw-3.bin")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
