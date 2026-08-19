#!/usr/bin/env python3
"""Test A/B del dito con finestre modali: e' l'utente a dettare i tempi.

Le notifiche notify-send non funzionavano: GNOME non le aggiornava a schermo
e le tre fasi passavano mentre l'utente vedeva ancora la prima. Qui ogni fase
e' preceduta da una finestra zenity che blocca finche' non si clicca OK,
quindi si sa con certezza che il dito era appoggiato durante la fase 2.
"""

import importlib.util
import statistics
import subprocess
import sys

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

GAIN = 0x0A
NFRAMES = 40


def ask(text):
    subprocess.run(["zenity", "--info", "--width=420",
                    "--title=Sensore impronte", "--text", text], check=False)


def collect(dev, n=NFRAMES):
    out = []
    guard = 0
    while len(out) < n and guard < n * 4:
        guard += 1
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) == c2.FRAME:
            out.append(f)
    return out


def summarize(name, frames):
    means = [sum(f) / len(f) for f in frames]
    varis = [statistics.pvariance(f) for f in frames]
    print(f"  {name:10s} n={len(frames):3d}  mean={statistics.mean(means):7.2f} "
          f"var={statistics.mean(varis):8.2f}", flush=True)
    return dict(means=means, varis=varis, frames=frames)


def main():
    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    c2.wr(dev, c2.REG_GAIN, GAIN)
    print(f"init {ok}/{tot}, gain {GAIN:#04x}", flush=True)

    ask("FASE 1 di 3 — fondo.\n\nNON toccare il sensore.\n\n"
        "Clicca OK e non toccare nulla per qualche secondo.")
    a = summarize("libero-1", collect(dev))

    ask("FASE 2 di 3 — dito.\n\n"
        "Appoggia ORA il dito sul tasto di accensione.\n"
        "Appoggia soltanto, NON premere.\n\n"
        "Tenendolo appoggiato, clicca OK con l'altra mano\n"
        "e tienilo li' per qualche secondo.")
    b = summarize("dito", collect(dev))

    ask("FASE 3 di 3 — controllo.\n\nTogli il dito, poi clicca OK.")
    c = summarize("libero-2", collect(dev))

    base = statistics.mean(a["means"] + c["means"])
    dito = statistics.mean(b["means"])
    bvar = statistics.mean(a["varis"] + c["varis"])
    dvar = statistics.mean(b["varis"])
    print(f"\n  media  libero={base:7.2f}  dito={dito:7.2f}  "
          f"delta={dito-base:+7.2f}")
    print(f"  var    libero={bvar:8.2f}  dito={dvar:8.2f}  "
          f"delta={dvar-bvar:+8.2f}")

    ref = [sum(v) / len(v) for v in zip(*(a["frames"] + c["frames"]))]
    fin = [sum(v) / len(v) for v in zip(*b["frames"])]
    d = [abs(x - y) for x, y in zip(ref, fin)]
    print(f"  |Δ| per pixel: medio={statistics.mean(d):.2f} max={max(d):.1f} "
          f" oltre 0x20 = {sum(1 for x in d if x > 32)}")

    c2.png_gray("abz-ref.png", c2.stretch(bytes(int(x) for x in ref)), c2.W, c2.H)
    c2.png_gray("abz-dito.png", c2.stretch(bytes(int(x) for x in fin)), c2.W, c2.H)
    lo, hi = min(d), max(d)
    c2.png_gray("abz-delta.png",
                bytes(int((x - lo) * 255 / (hi - lo)) if hi > lo else 0
                      for x in d), c2.W, c2.H)
    print("  salvati abz-ref.png abz-dito.png abz-delta.png", flush=True)

    verdict = "REAGISCE" if max(d) > 8 else "nessuna reazione"
    print(f"\n  verdetto: {verdict}")
    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
