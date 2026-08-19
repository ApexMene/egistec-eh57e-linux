#!/usr/bin/env python3
"""Test A/B del dito, con notifiche desktop per sincronizzare l'utente.

Il problema delle run precedenti era che non c'era modo di sapere se il
sensore fosse davvero toccato durante la finestra di cattura. Qui il momento
di toccare viene annunciato con notify-send, quindi il confronto fra le fasi
e' affidabile.

Fasi: libero -> dito -> libero. Se il sensore reagisce, la fase centrale
deve staccarsi dalle altre due.
"""

import importlib.util
import statistics
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

GAIN = 0x0A


def notify(title, body, urgency="critical"):
    subprocess.run(["notify-send", "-u", urgency, "-t", "6000", title, body],
                   check=False)


def collect(dev, seconds):
    frames = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) == c2.FRAME:
            frames.append(f)
    return frames


def summarize(name, frames):
    if not frames:
        return None
    means = [sum(f) / len(f) for f in frames]
    varis = [statistics.pvariance(f) for f in frames]
    print(f"  {name:10s} n={len(frames):4d}  mean={statistics.mean(means):7.2f} "
          f"(sd {statistics.pstdev(means):5.2f})  var={statistics.mean(varis):8.2f} "
          f"(sd {statistics.pstdev(varis):6.2f})", flush=True)
    return dict(means=means, varis=varis, frames=frames)


def main():
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0

    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    c2.wr(dev, c2.REG_GAIN, GAIN)
    print(f"init {ok}/{tot}, gain {GAIN:#04x}", flush=True)

    notify("Sensore impronte", "NON toccare — sto misurando il fondo")
    print(f"\nfase 1: libero ({dur:.0f}s)", flush=True)
    a = summarize("libero-1", collect(dev, dur))

    notify("Sensore impronte — TOCCA ORA",
           "Appoggia il dito sul tasto di accensione. NON premere.")
    print(f"fase 2: DITO ({dur:.0f}s)", flush=True)
    b = summarize("dito", collect(dev, dur))

    notify("Sensore impronte", "Togli il dito")
    print(f"fase 3: libero ({dur:.0f}s)", flush=True)
    c = summarize("libero-2", collect(dev, dur))

    if not (a and b and c):
        print("\nfasi incomplete")
        return

    base = statistics.mean(a["means"] + c["means"])
    dito = statistics.mean(b["means"])
    bvar = statistics.mean(a["varis"] + c["varis"])
    dvar = statistics.mean(b["varis"])
    print(f"\n  media  libero={base:7.2f}  dito={dito:7.2f}  "
          f"delta={dito-base:+7.2f}")
    print(f"  var    libero={bvar:8.2f}  dito={dvar:8.2f}  "
          f"delta={dvar-bvar:+8.2f}")

    # confronto pixel a pixel fra le medie delle fasi
    ref = [sum(v) / len(v) for v in zip(*(a["frames"] + c["frames"]))]
    fin = [sum(v) / len(v) for v in zip(*b["frames"])]
    d = [abs(x - y) for x, y in zip(ref, fin)]
    print(f"  |Δ| per pixel: medio={statistics.mean(d):.2f} "
          f"max={max(d):.1f}  pixel oltre 0x20 = {sum(1 for x in d if x > 32)}")

    c2.png_gray("ab-ref.png", c2.stretch(bytes(int(x) for x in ref)),
                c2.W, c2.H)
    c2.png_gray("ab-dito.png", c2.stretch(bytes(int(x) for x in fin)),
                c2.W, c2.H)
    lo, hi = min(d), max(d)
    scale = bytes(int((x - lo) * 255 / (hi - lo)) if hi > lo else 0 for x in d)
    c2.png_gray("ab-delta.png", scale, c2.W, c2.H)
    print("  salvati ab-ref.png ab-dito.png ab-delta.png")

    notify("Sensore impronte", "Test finito")
    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
