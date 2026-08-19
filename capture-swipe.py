#!/usr/bin/env python3
"""Cattura una sequenza mentre il dito scorre, per poterne fare un mosaico.

Perche': un fotogramma solo copre 4.3 x 3.6 mm, e in quell'area ci sono
fisicamente due o tre minuzie. NBIS ne trova tre, il che e' corretto e
insufficiente: bozorth3 non puo' decidere niente con tre punti. L'unica
strada per avere piu' area e' unire fotogrammi presi mentre il dito si
muove, che e' quello che fanno tutti i sensori piccoli.

Qui si salva soltanto: il mosaico si costruisce dopo, offline, con stitch.py.
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
# A 55 fotogrammi al secondo, 1400 fanno circa 25 secondi: una passata lenta
# ci sta comoda, e restare fermi qualche secondo in piu' non fa danno.
NFRAMES = 1400


def chiedi(testo):
    subprocess.run(["zenity", "--info", "--width=480",
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


def main():
    dev = apri()
    try:
        ok, tot = c2.init(dev)
        c2.wr(dev, c2.REG_GAIN, GAIN)
        c2.wr(dev, c2.REG_OFFSET, OFFSET)
        print(f"init {ok}/{tot}, gain {GAIN:#04x}")
        c2.drain(dev)

        chiedi("FASE 1 di 2 — fondo.\n\nNON toccare il sensore. Clicca OK.")
        bg = np.median(np.stack([f.astype(np.float64)
                                 for f in (frame(dev) for _ in range(20))
                                 if f is not None]), axis=0)
        bg.astype(np.uint8).tofile("sw-fondo.bin")

        chiedi("FASE 2 di 2 — passata lenta.\n\n"
               "Clicca OK, poi appoggia il dito sul tasto di accensione e "
               "fallo scorrere MOLTO LENTAMENTE\n"
               "dalla punta verso la prima piega, come se lo strisciassi.\n\n"
               "Appoggia soltanto, NON premere.\n\n"
               "Hai 25 secondi: parti SUBITO dopo aver cliccato, e vai\n"
               "piano — la lentezza aiuta. Ti avviso io quando smettere.")

        t0 = time.time()
        frames = []
        for _ in range(NFRAMES):
            f = frame(dev)
            if f is not None:
                frames.append(f)
        dt = time.time() - t0

        chiedi("Fatto — puoi TOGLIERE il dito.\n\nElaboro.")

        a = np.stack(frames)
        a.tofile("sw-frames.bin")
        dist = np.abs(a.astype(np.float64) - bg).mean(axis=1)
        conDito = int((dist > 15).sum())
        print(f"{len(frames)} frame in {dt:.1f}s "
              f"({len(frames)/dt:.0f}/s), {conDito} col dito")
        print(f"distanza dal fondo: min={dist.min():.1f} max={dist.max():.1f}")
        print("salvati sw-fondo.bin, sw-frames.bin")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
