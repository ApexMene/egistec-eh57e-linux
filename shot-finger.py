#!/usr/bin/env python3
"""Acquisizione di un'impronta con correzione di flat-field.

Due cose imparate dal test A/B:

  - il sensore reagisce davvero: varianza 44 a vuoto, 165 con il dito, e
    torna a 44 appena lo si toglie;
  - l'immagine grezza ha un pattern fisso a diagonali. Viene dai 3 canali
    ADC multiplexati (3 byte di payload per gruppo di 4): siccome la riga e'
    larga 70 e 70 non e' divisibile per 3, l'indice di canale slitta di uno
    a ogni riga. Si elimina sottraendo un riferimento per pixel.

Mediare molti frame col dito appiattisce le creste, quindi qui si salvano i
singoli frame corretti e si tengono quelli a varianza piu' alta.
"""

import importlib.util
import statistics
import subprocess

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

GAIN = 0x0A
N_REF = 30
N_SHOT = 60
KEEP = 5


def ask(text):
    subprocess.run(["zenity", "--info", "--width=420",
                    "--title=Sensore impronte", "--text", text], check=False)


def grab(dev, n):
    out = []
    guard = 0
    while len(out) < n and guard < n * 4:
        guard += 1
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) == c2.FRAME:
            out.append(f)
    return out


def flat(frame, ref):
    """frame - riferimento, ricentrato a 128 e saturato"""
    return bytes(max(0, min(255, 128 + int(a) - int(b)))
                 for a, b in zip(frame, ref))


def main():
    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    c2.wr(dev, c2.REG_GAIN, GAIN)
    print(f"init {ok}/{tot}, gain {GAIN:#04x}", flush=True)

    ask("FASE 1 — riferimento.\n\nNON toccare il sensore.\nClicca OK.")
    refs = grab(dev, N_REF)
    ref = [sum(v) / len(v) for v in zip(*refs)]
    print(f"riferimento su {len(refs)} frame, mean={sum(ref)/len(ref):.2f}",
          flush=True)
    c2.png_gray("ff-ref.png", c2.stretch(bytes(int(x) for x in ref)),
                c2.W, c2.H)

    ask("FASE 2 — impronta.\n\n"
        "Appoggia il dito sul tasto di accensione (NON premere)\n"
        "e, tenendolo fermo li', clicca OK con l'altra mano.\n\n"
        "Tienilo fermo per qualche secondo.")
    shots = grab(dev, N_SHOT)
    print(f"catturati {len(shots)} frame col dito", flush=True)

    scored = []
    for f in shots:
        c = flat(f, ref)
        scored.append((statistics.pvariance(c), c, f))
    scored.sort(key=lambda t: -t[0])

    print("\n  migliori frame per varianza dopo correzione:")
    for i, (v, corr, rawf) in enumerate(scored[:KEEP]):
        print(f"   {i}: var_corretta={v:8.2f}  var_grezza="
              f"{statistics.pvariance(rawf):8.2f}  "
              f"range={min(corr)}-{max(corr)}", flush=True)
        c2.png_gray(f"ff-dito-{i}.png", c2.stretch(corr), c2.W, c2.H)
        open(f"ff-dito-{i}.bin", "wb").write(corr)

    print("\n  salvati ff-dito-*.png", flush=True)
    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
