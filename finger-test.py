#!/usr/bin/env python3
"""Prova del dito: sfondo, poi acquisizione continua, poi differenza.

Geometria e trasporto vengono da capture3.py: blocco di 5320 byte sul filo,
di cui i primi 3990 sono i pixel (70x57) e il resto e' coda costante 117.

Attenzione a una cosa vista nei dati: se si fa **una sola** richiesta e si
continua a leggere, il sensore ripete lo stesso buffer identico byte per byte
(76 frame, 0 byte diversi). Per avere frame nuovi bisogna ri-armare e
ri-chiedere ogni volta. Qui il ciclo fa proprio questo, senza riaprire il
device: riaprirlo costa un reset USB e un paio di secondi.

Uso:
    ./finger-test.py --sfondo 8 --dito 40
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


def avvisa(titolo, testo, urgenza="normal", suono=True):
    """Notifica sul desktop: il terminale non si guarda mentre si tiene il
    dito appoggiato sul tasto di accensione."""
    try:
        subprocess.run(["notify-send", "-u", urgenza, "-t", "4000",
                        titolo, testo], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    if suono:
        for p in ("/usr/share/sounds/freedesktop/stereo/message.oga",
                  "/usr/share/sounds/freedesktop/stereo/bell.oga"):
            try:
                subprocess.Popen(["paplay", p], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                break
            except FileNotFoundError:
                pass


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


# Il comando che ri-arma davvero l'acquisizione, trovato con retrigger.py:
# burst write (cmd 0x63) del registro 0x2c con 02 00 13. E' l'ultima riga
# dell'INIT_SEQUENCE, e da sola basta: sd=2.08, ~1380 byte che cambiano a ogni
# frame, r=+0.96. Tutte le altre candidate lasciano il sensore congelato sullo
# stesso buffer (0 byte diversi).
RIARMA = "45474953632c020013"


def frame(dev):
    """Un frame nuovo. Senza ri-armare, il sensore ripete lo stesso buffer
    identico byte per byte."""
    c2.cmd(dev, RIARMA)
    dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(BLOCCO)), timeout=1000)
    d = leggi(dev, BLOCCO)
    if len(d) < PIX:
        return None
    return np.frombuffer(d[:PIX], dtype=np.uint8).astype(np.int16)


def serie(dev, n, etichetta):
    out = []
    for i in range(n):
        f = frame(dev)
        if f is None:
            print(f"  {etichetta} {i}: frame corto", flush=True)
            continue
        out.append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sfondo", type=int, default=8)
    ap.add_argument("--dito", type=int, default=40)
    ap.add_argument("--attesa", type=float, default=6.0,
                    help="secondi di pausa prima di iniziare a cercare il dito")
    a = ap.parse_args()

    dev = apri()
    try:
        c2.init(dev)
        c2.drain(dev)

        avvisa("Impronte — preparazione",
               "NON toccare il sensore. Sto misurando lo sfondo.",
               "critical")
        print("== sfondo, sensore libero ==", flush=True)
        bg = serie(dev, a.sfondo, "sfondo")
        if not bg:
            print("nessun frame di sfondo")
            return 1
        rif = np.median(np.stack(bg), axis=0)
        rumore = float(np.median([np.abs(f - rif).mean() for f in bg]))
        print(f"  {len(bg)} frame, riferimento media={rif.mean():.2f}, "
              f"scarto tipico a vuoto={rumore:.3f}", flush=True)
        c2.png_gray("dito-sfondo.png", c2.stretch(bytes(rif.astype(np.uint8))),
                    W, H, scale=6)

        print("\n== APPOGGIA IL DITO SUL TASTO DI ACCENSIONE ==", flush=True)
        print(f"   appoggia, non premere. hai {a.attesa:.0f} secondi",
              flush=True)
        for rimasti in range(int(a.attesa), 0, -1):
            if rimasti in (int(a.attesa), 3, 2, 1):
                avvisa("Impronte — preparati",
                       f"Fra {rimasti}s appoggia il dito sul tasto di "
                       f"accensione. Appoggia, non premere.", "critical",
                       suono=(rimasti <= 3))
            time.sleep(1)

        avvisa("Impronte — DITO ORA",
               "Appoggia il dito adesso e tienilo fermo.", "critical")
        print("== acquisizione ==", flush=True)
        best, bestf, bi = 0.0, None, -1
        for i in range(a.dito):
            f = frame(dev)
            if f is None:
                continue
            d = np.abs(f - rif)
            sc = float(d.mean())
            if sc > best:
                best, bestf, bi = sc, f, i
            barra = "#" * min(60, int(sc * 4))
            print(f"  {i:3d}: scarto={sc:7.3f}  {barra}", flush=True)

        avvisa("Impronte — TOGLI IL DITO",
               f"Acquisizione finita. Scarto massimo {best:.2f} "
               f"({best / max(rumore, 1e-9):.1f}x il rumore).", "critical")
        print(f"\nmassimo scarto = {best:.3f} al frame {bi} "
              f"(rumore a vuoto {rumore:.3f}, rapporto {best / max(rumore, 1e-9):.1f}x)")
        if bestf is not None:
            c2.png_gray("dito-grezzo.png",
                        c2.stretch(bytes(bestf.astype(np.uint8))),
                        W, H, scale=6)
            diff = np.abs(bestf - rif)
            dd = (diff / max(diff.max(), 1) * 255).astype(np.uint8)
            c2.png_gray("dito-differenza.png", bytes(dd), W, H, scale=6)
            print("salvati dito-sfondo.png, dito-grezzo.png, dito-differenza.png")
        return 0
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
