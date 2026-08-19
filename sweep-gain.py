#!/usr/bin/env python3
"""L'immagine che leggiamo dipende davvero dall'analogica del sensore?

Controllo che non richiede il dito. Si spazzano guadagno (0x12) e offset (0x0f)
e si guarda se media e deviazione dell'immagine si muovono. Se non si muove
nulla, quello che leggiamo non passa dalla catena ADC dell'array e nessun dito
potra' mai comparirci: sarebbe un buffer costante, e andrebbe cercato altrove
il comando che avvia la scansione vera.

Se invece la media segue l'offset e la deviazione segue il guadagno, la catena
di lettura e' quella giusta e il problema del dito e' altrove (esposizione,
polarizzazione del drive capacitivo, o semplicemente guadagno troppo basso).
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


def media_di(dev, n=5):
    fs = [f for f in (frame(dev) for _ in range(n)) if f is not None]
    if not fs:
        return None
    return np.median(np.stack(fs), axis=0)


def sweep(dev, reg, valori, etichetta):
    print(f"\n=== {etichetta} (registro {reg:#04x}) ===")
    print("  valore   media    sd    min  max  livelli   letto")
    prima = None
    for v in valori:
        c2.wr(dev, reg, v)
        # rileggo il registro: se il sensore non lo accetta e' inutile
        # interpretare l'immagine che ne esce
        try:
            back = c2.rd(dev, reg)
        except Exception:                           # noqa: BLE001
            back = None
        m = media_di(dev)
        if m is None:
            print(f"  {v:#04x}     nessun frame")
            continue
        b = f"{back:#04x}" if isinstance(back, int) else str(back)
        print(f"  {v:#04x}   {m.mean():7.2f} {m.std():6.2f} "
              f"{int(m.min()):4d} {int(m.max()):4d}  {len(np.unique(m)):5d}"
              f"   {b}", flush=True)
        if prima is not None:
            d = float(np.abs(m - prima).mean())
            if d > 0.5:
                print(f"           -> cambiata rispetto al valore prima "
                      f"(|delta| medio {d:.2f})")
        prima = m


def main():
    dev = apri()
    try:
        ok, tot = c2.init(dev)
        print(f"init {ok}/{tot}")
        c2.drain(dev)
        sweep(dev, c2.REG_GAIN, [0x00, 0x02, 0x05, 0x0A, 0x20, 0x40, 0x7F, 0xFF],
              "guadagno")
        sweep(dev, c2.REG_OFFSET, [0x00, 0x10, 0x20, 0x40, 0x80, 0xC0, 0xFF],
              "offset")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
