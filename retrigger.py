#!/usr/bin/env python3
"""Qual e' il comando che fa acquisire un frame NUOVO?

Fatto osservato: dopo una richiesta d'immagine il sensore continua a mandare
lo stesso buffer, identico byte per byte (76 ripetizioni, 0 byte diversi).
Riaprire il device (reset USB + init completo) produce invece frame nuovi, che
correlano fra loro a r = +0.95 — il fixed-pattern noise. Ma un reset costa un
paio di secondi: troppo per inseguire un dito appoggiato.

Qui si cerca la sequenza minima che ri-arma l'acquisizione senza reset.
Criterio: due frame consecutivi devono **differire** (acquisizione viva) pur
restando correlati (stesso sensore, stesso fixed-pattern). Se il frame non
cambia affatto, la sequenza non ri-arma nulla.
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


def apri(tent=8):
    ultimo = None
    for _ in range(tent):
        try:
            return c2.open_dev()
        except Exception as e:                      # noqa: BLE001
            ultimo = e
            time.sleep(1.2)
    raise RuntimeError(f"sensore non riapribile: {ultimo}")


def leggi(dev, quanti, quiet=0.8):
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


def frame(dev, riarma):
    riarma(dev)
    dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(BLOCCO)), timeout=1000)
    d = leggi(dev, BLOCCO)
    if len(d) < PIX:
        return None
    return np.frombuffer(d[:PIX], dtype=np.uint8).astype(np.int16)


def corr(a, b):
    a = a.astype(np.float64) - a.mean()
    b = b.astype(np.float64) - b.mean()
    den = (np.dot(a, a) * np.dot(b, b)) ** 0.5
    return float(np.dot(a, b) / den) if den else 0.0


VARIANTI = [
    ("init completo",
     lambda d: c2.init(d)),
    ("burst 0x2c=02 00 13",
     lambda d: c2.cmd(d, "45474953632c020013")),
    ("burst 0x2c=02 00 57",
     lambda d: c2.cmd(d, "45474953632c020057")),
    ("0x2c=00 poi 0x02: 0f,2f",
     lambda d: (c2.wr(d, 0x2C, 0x00), c2.wr(d, 0x02, 0x0F),
                c2.wr(d, 0x02, 0x2F))),
    ("0x2d=13 poi 0x2d=20",
     lambda d: (c2.wr(d, 0x2D, 0x13), c2.wr(d, 0x2D, 0x20))),
    ("0x0f=00 (chiusura init)",
     lambda d: c2.wr(d, 0x0F, 0x00)),
    ("0x67=03 (burst 0x62)",
     lambda d: c2.cmd(d, "45474953626703")),
    ("solo 0x02: 0f,2f",
     lambda d: (c2.wr(d, 0x02, 0x0F), c2.wr(d, 0x02, 0x2F))),
]


def prova(nome, riarma, n=4):
    dev = apri()
    try:
        c2.init(dev)
        c2.drain(dev)
        fs = []
        for _ in range(n):
            f = frame(dev, riarma)
            if f is None:
                print(f"  {nome:28s} frame corto", flush=True)
                return
            fs.append(f)
        diffs = [int(np.count_nonzero(fs[i] != fs[i + 1]))
                 for i in range(len(fs) - 1)]
        cs = [corr(fs[i], fs[i + 1]) for i in range(len(fs) - 1)]
        vivo = "VIVO" if min(diffs) > 50 else "fermo"
        print(f"  {nome:28s} sd={fs[0].std():5.2f} media={fs[0].mean():6.2f} "
              f"cambiati={diffs} r={np.mean(cs):+.3f}  {vivo}", flush=True)
    except usb.core.USBError as e:
        print(f"  {nome:28s} errore: {e}", flush=True)
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


def main():
    print("cerco la sequenza che ri-arma l'acquisizione senza reset USB")
    print("(cambiati = byte diversi fra frame consecutivi; serve > 0)\n")
    for nome, r in VARIANTI:
        prova(nome, r)


if __name__ == "__main__":
    main()
