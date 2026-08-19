#!/usr/bin/env python3
"""Cattura ad alto rapporto segnale/rumore, con tutti i frame grezzi su disco.

Cosa si e' imparato dal flat-field:

  - il pattern a diagonali e' un offset medio diverso fra i 3 canali ADC
    multiplexati; si toglie normalizzando la media di ciascun canale, non
    sottraendo un riferimento per pixel;
  - dopo quella correzione resta un rumore per pixel di sd ~7, dello stesso
    ordine del segnale: un singolo frame non basta.

Il dito pero' sta fermo, quindi le creste sono statiche e il rumore no:
mediare molti frame alza la SNR di sqrt(N). Qui si salvano tutti i frame
grezzi in hq-ref.raw / hq-dito.raw cosi' ogni elaborazione successiva si fa
offline, senza chiedere di nuovo il dito.
"""

import importlib.util
import statistics
import subprocess

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

GAIN = 0x0A
N_REF = 40
N_SHOT = 120


def ask(text):
    subprocess.run(["zenity", "--info", "--width=460",
                    "--title=Sensore impronte", "--text", text], check=False)


def grab(dev, n, label):
    out = []
    guard = 0
    while len(out) < n and guard < n * 4:
        guard += 1
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) == c2.FRAME:
            out.append(f)
            if len(out) % 20 == 0:
                print(f"  {label}: {len(out)}/{n}", flush=True)
    return out


def chan_norm(d):
    """Toglie l'offset medio di ciascuno dei 3 canali ADC."""
    m = [statistics.mean(d[k::3]) for k in range(3)]
    g = statistics.mean(m)
    return [d[i] + g - m[i % 3] for i in range(len(d))]


def pstretch(c, p=2.0):
    """Stretch sui percentili: gli outlier non schiacciano l'immagine."""
    s = sorted(c)
    n = len(s)
    lo, hi = s[int(n * p / 100)], s[int(n * (100 - p) / 100)]
    if hi <= lo:
        hi = lo + 1
    return bytes(max(0, min(255, int((x - lo) * 255 / (hi - lo)))) for x in c)


def main():
    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    c2.wr(dev, c2.REG_GAIN, GAIN)
    print(f"init {ok}/{tot}, gain {GAIN:#04x}", flush=True)

    ask("FASE 1 — fondo.\n\nNON toccare il sensore.\nClicca OK.")
    refs = grab(dev, N_REF, "fondo")
    open("hq-ref.raw", "wb").write(b"".join(refs))

    ask("FASE 2 — impronta.\n\n"
        "Appoggia il dito sul tasto di accensione (NON premere),\n"
        "clicca OK con l'altra mano e POI TIENILO FERMO\n"
        "finche' non compare la finestra di fine.\n\n"
        "Servono ~15 secondi. Premi bene ma senza spostarti.")
    shots = grab(dev, N_SHOT, "dito")
    open("hq-dito.raw", "wb").write(b"".join(shots))
    ask("Fatto — puoi togliere il dito.")

    print(f"\nsalvati {len(refs)} frame di fondo e {len(shots)} col dito",
          flush=True)

    ref = [sum(v) / len(v) for v in zip(*refs)]
    fin = [sum(v) / len(v) for v in zip(*shots)]
    print(f"  media fondo={statistics.mean(ref):6.2f}  "
          f"dito={statistics.mean(fin):6.2f}")

    for name, img in (("hq-ref", ref), ("hq-dito", fin)):
        c2.png_gray(f"{name}.png", pstretch(chan_norm(img)), c2.W, c2.H,
                    scale=6)

    diff = [a - b for a, b in zip(fin, ref)]
    dn = chan_norm(diff)
    print(f"  differenza: sd={statistics.pstdev(dn):.2f} "
          f"range={min(dn):.1f}..{max(dn):.1f}")
    c2.png_gray("hq-diff.png", pstretch(dn), c2.W, c2.H, scale=6)
    print("  salvati hq-ref.png hq-dito.png hq-diff.png "
          "(+ hq-ref.raw hq-dito.raw)", flush=True)

    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
