#!/usr/bin/env python3
"""Salva un fondo e un dito grezzi, per poter provare l'elaborazione offline.

Serve a chiedere il dito una volta sola: da questi due file si possono provare
quante varianti si vuole (scala, inversione, sottrazione del fondo) senza
rimettere le mani sul sensore.

Salva byte grezzi, non PNG: l'immagine stirata butta via l'informazione che
serve per decidere come stirarla.
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


def chiedi(testo):
    subprocess.run(["zenity", "--info", "--width=460",
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
    return np.frombuffer(d[:PIX], dtype=np.uint8).astype(np.float64)


def serie(dev, n):
    return [f for f in (frame(dev) for _ in range(n)) if f is not None]


def main():
    dev = apri()
    try:
        ok, tot = c2.init(dev)
        c2.wr(dev, c2.REG_GAIN, GAIN)
        c2.wr(dev, c2.REG_OFFSET, OFFSET)
        print(f"init {ok}/{tot}, gain {GAIN:#04x}, offset {OFFSET:#04x}")
        c2.drain(dev)

        chiedi("FASE 1 di 2 — fondo.\n\nNON toccare il sensore.\n\nClicca OK.")
        bg = np.median(np.stack(serie(dev, 20)), axis=0)

        chiedi("FASE 2 di 2 — dito.\n\n"
               "Appoggia il dito sul tasto di accensione e TIENILO FERMO.\n"
               "Appoggia soltanto, NON premere.\n\n"
               "Poi clicca OK con l'altra mano, tenendo il dito giu'.")
        fingers = serie(dev, 40)

        # Ogni fase che chiede il dito deve dire anche quando smettere: senza
        # questa finestra si resta col dito appoggiato senza sapere se serve
        # ancora.
        chiedi("Fatto — puoi TOGLIERE il dito.\n\n"
               "Elaboro i dati, non serve piu' toccare il sensore.")

        # si tiene il frame piu' lontano dal fondo: e' quello col contatto
        # migliore, non necessariamente il primo
        dists = [float(np.abs(f - bg).mean()) for f in fingers]
        best = int(np.argmax(dists))
        print(f"{len(fingers)} frame col dito, distanza dal fondo "
              f"min={min(dists):.1f} max={max(dists):.1f}, scelto il {best}")

        bg.astype(np.uint8).tofile("raw-fondo.bin")
        fingers[best].astype(np.uint8).tofile("raw-dito.bin")
        # anche la mediana dei frame col dito: meno rumore temporale
        np.median(np.stack(fingers), axis=0).astype(np.uint8).tofile(
            "raw-dito-mediana.bin")
        print("salvati raw-fondo.bin, raw-dito.bin, raw-dito-mediana.bin")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
