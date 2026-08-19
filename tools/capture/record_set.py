#!/usr/bin/env python3
"""Raccolta per stimare la soglia: piu' dita, piu' appoggi ciascuna.

Niente passate. Misurato il 19/08: il dito non trasla sul sensore, il picco di
correlazione fra fotogrammi lontani nel tempo resta a (0,0). Chiedere di
scorrere non aggiungeva area, aggiungeva solo deformazione. Qui si appoggia e
basta, otto secondi.

Ogni appoggio e' una sessione a se': fra uno e l'altro il dito si stacca e si
riappoggia, che e' la variabilita' vera contro cui il confronto deve reggere.
Tre appoggi per dito servono perche' con due non si distingue "sono simili" da
"sono capitati uguali".

Uscita: set-fondo.bin, set-<dito>-<n>.bin
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
NFRAMES = 440           # ~8 s a 55 fotogrammi al secondo

DITA = ["indice-dx", "medio-dx", "anulare-dx", "pollice-dx", "indice-sx"]
APPOGGI = 3


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


def appoggio(dev, bg, dito, n, quanti, fatti):
    chiedi(f"{fatti + 1} di {quanti} — {dito.upper()}, appoggio {n} di "
           f"{APPOGGI}\n\n"
           "Clicca OK, poi appoggia il dito e TIENILO FERMO 8 secondi.\n\n"
           "Appoggia soltanto, NON premere.\n\n"
           "Ti avviso io quando toglierlo.")

    frames = [f for f in (frame(dev) for _ in range(NFRAMES)) if f is not None]
    a = np.stack(frames)
    a.tofile(f"set-{dito}-{n}.bin")

    dist = np.abs(a.astype(np.float64) - bg).mean(axis=1)
    buoni = int((dist > 25).sum())
    print(f"{dito} #{n}: {len(frames)} frame, {buoni} col dito, "
          f"distanza {dist.min():.1f}..{dist.max():.1f}"
          f"{'   <-- POCHI, da rifare' if buoni < 150 else ''}")

    chiedi(f"{dito.upper()} #{n} fatto — puoi TOGLIERE il dito.")


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
        bg.astype(np.uint8).tofile("set-fondo.bin")
        print("fondo salvato")

        quanti = len(DITA) * APPOGGI
        fatti = 0
        # dito esterno, appoggio interno: cosi' i tre appoggi dello stesso dito
        # sono separati da pochi secondi, non da minuti, e la variabilita' che
        # si misura e' quella del riappoggio e non della giornata
        for dito in DITA:
            for n in range(1, APPOGGI + 1):
                appoggio(dev, bg, dito, n, quanti, fatti)
                fatti += 1

        chiedi("Finito. Puoi lasciare stare il sensore.")
        print(f"salvati set-fondo.bin e {quanti} appoggi")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
