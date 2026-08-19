#!/usr/bin/env python3
"""A/B del dito con finestre modali zenity + lettura corretta (capture3).

Perche' zenity e non notify-send: le notifiche GNOME restano a schermo, non si
cancellano comodamente e soprattutto non danno nessuna garanzia che il dito
fosse appoggiato durante la fase giusta. La finestra modale blocca lo script
finche' non si clicca OK: i tempi li detta l'utente, non il timer.

Rispetto ad ab-zenity.py cambia la lettura: niente depad(), blocco di 5320 byte
di cui i primi 3990 sono i pixel 70x57, e re-arming esplicito a ogni frame
(45474953632c020013), altrimenti il sensore ripete lo stesso buffer identico.

Struttura: libero -> dito -> libero. Il secondo "libero" serve da controllo:
se la differenza libero-1 vs libero-2 e' grande quanto quella libero vs dito,
non stiamo misurando il dito ma la deriva del sensore.
"""

import argparse
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


def chiedi(testo, titolo="Sensore impronte"):
    subprocess.run(["zenity", "--info", "--width=460",
                    f"--title={titolo}", "--text", testo], check=False)


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


def fase(dev, nome, n):
    fs = []
    for _ in range(n):
        f = frame(dev)
        if f is not None:
            fs.append(f)
    if not fs:
        print(f"  {nome}: nessun frame")
        return None
    a = np.stack(fs)
    med = np.median(a, axis=0)
    print(f"  {nome:10s} n={len(fs):3d} media={med.mean():7.3f} "
          f"sd_spaziale={med.std():6.3f} "
          f"sd_temporale={a.std(axis=0).mean():6.3f}", flush=True)
    return med


def confronta(nome, a, b):
    d = np.abs(a - b)
    print(f"  {nome:22s} |delta| medio={d.mean():6.3f} max={d.max():6.1f} "
          f"pixel oltre 8 = {int((d > 8).sum())}")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=30)
    # Punto di lavoro da calib.py: il guadagno e' a 4 bit e dopo l'init resta a
    # 0x00, cioe' sd 2.06 su 18 livelli — a quel guadagno il dito sta sotto il
    # passo di quantizzazione, ed e' il motivo per cui i test precedenti non
    # vedevano niente. A 0x0a si hanno 201 livelli con l'1.8% di pixel tosati.
    # L'offset invece ha una sola posizione utile: fuori da 0x20 l'immagine va
    # tutta a 0 o tutta a 255.
    ap.add_argument("--gain", type=lambda s: int(s, 0), default=0x0A)
    ap.add_argument("--offset", type=lambda s: int(s, 0), default=0x20)
    a = ap.parse_args()

    dev = apri()
    try:
        ok, tot = c2.init(dev)
        c2.wr(dev, c2.REG_GAIN, a.gain)
        c2.wr(dev, c2.REG_OFFSET, a.offset)
        print(f"init {ok}/{tot}, gain {a.gain:#04x}, offset {a.offset:#04x}",
              flush=True)
        c2.drain(dev)

        chiedi("FASE 1 di 3 — fondo.\n\n"
               "NON toccare il sensore.\n\n"
               "Clicca OK e lascia stare tutto per qualche secondo.")
        l1 = fase(dev, "libero-1", a.frames)

        chiedi("FASE 2 di 3 — dito.\n\n"
               "Appoggia ORA il dito sul tasto di accensione.\n"
               "Appoggia soltanto, NON premere.\n\n"
               "Tenendolo appoggiato, clicca OK con l'altra mano\n"
               "e tienilo fermo li' per qualche secondo.")
        dt = fase(dev, "dito", a.frames)

        chiedi("FASE 3 di 3 — controllo.\n\n"
               "Togli il dito, poi clicca OK.")
        l2 = fase(dev, "libero-2", a.frames)

        if l1 is None or dt is None or l2 is None:
            return 1

        print("\nconfronti:")
        # controllo: quanto deriva il sensore da solo, senza nessun dito
        base = confronta("libero-1 vs libero-2", l1, l2)
        rif = (l1 + l2) / 2
        seg = confronta("dito vs fondo", dt, rif)

        rapp = seg.mean() / max(base.mean(), 1e-9)
        print(f"\n  rapporto segnale/deriva = {rapp:.2f}x")
        print("  verdetto:", "REAGISCE" if rapp > 2.0 and seg.max() > 8
              else "nessuna reazione distinguibile dalla deriva")

        c2.png_gray("dz-fondo.png", c2.stretch(bytes(rif.astype(np.uint8))),
                    W, H, scale=6)
        c2.png_gray("dz-dito.png", c2.stretch(bytes(dt.astype(np.uint8))),
                    W, H, scale=6)
        sc = seg / max(seg.max(), 1) * 255
        c2.png_gray("dz-delta.png", bytes(sc.astype(np.uint8)), W, H, scale=6)
        print("  salvati dz-fondo.png dz-dito.png dz-delta.png")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
