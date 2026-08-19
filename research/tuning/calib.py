#!/usr/bin/env python3
"""Punto di lavoro dell'analogica: guadagno e offset.

Da sweep-gain.py:
  * reg 0x12 (guadagno) e' a 4 bit -> vale 0x00..0x0f, il resto rilegge
    troncato (0x20 -> 0x00, 0xff -> 0x0f);
  * reg 0x0f (offset) e' a 6 bit -> 0x00..0x3f (0xff -> 0x3f);
  * dopo l'init il guadagno resta a 0x00: sd 2.06, 18 livelli. E' per questo
    che nessun test col dito mostrava niente — leggevamo l'array a guadagno
    nullo, e le variazioni del dito finivano sotto il passo di quantizzazione.

Qui si cerca la coppia (guadagno, offset) che da' piu' contrasto senza
tosare: si scarta ogni punto con troppi pixel a 0 o a 255, perche' li'
l'informazione del dito e' gia' persa.
"""

import importlib.util
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
MAX_TOSATI = 0.02          # al massimo il 2% dei pixel puo' stare a fondo scala


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


def media_di(dev, n=3):
    fs = [f for f in (frame(dev) for _ in range(n)) if f is not None]
    return np.median(np.stack(fs), axis=0) if fs else None


def main():
    dev = apri()
    try:
        ok, tot = c2.init(dev)
        print(f"init {ok}/{tot}\n")
        c2.drain(dev)

        print(" gain off   media     sd   tosati%   livelli")
        buoni = []
        for g in range(0x00, 0x10):
            for off in (0x10, 0x18, 0x20, 0x28, 0x30):
                c2.wr(dev, c2.REG_GAIN, g)
                c2.wr(dev, c2.REG_OFFSET, off)
                m = media_di(dev)
                if m is None:
                    continue
                tos = float(((m <= 0) | (m >= 255)).mean())
                print(f"  {g:#04x} {off:#04x} {m.mean():7.2f} {m.std():6.2f} "
                      f"  {tos*100:6.2f}   {len(np.unique(m)):5d}", flush=True)
                if tos <= MAX_TOSATI:
                    buoni.append((m.std(), g, off, m))

        if not buoni:
            print("\nnessun punto senza tosatura")
            return 1
        buoni.sort(key=lambda t: -t[0])
        sd, g, off, m = buoni[0]
        print(f"\nmigliore: gain={g:#04x} offset={off:#04x} sd={sd:.2f} "
              f"media={m.mean():.1f}")
        c2.png_gray("calib-migliore.png",
                    c2.stretch(bytes(m.astype(np.uint8))), W, H, scale=6)
        print("salvato calib-migliore.png")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
