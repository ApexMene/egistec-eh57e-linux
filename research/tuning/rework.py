#!/usr/bin/env python3
"""Rielaborazione offline dei frame grezzi salvati da capture-hq.py.

Non tocca il sensore: legge hq-ref.raw e hq-dito.raw e prova piu' catene di
correzione, cosi' si puo' iterare senza chiedere di nuovo il dito.

Catene provate:
  medio      media dei frame, normalizzazione canali
  diff       media dito - media fondo, normalizzazione canali
  mediana    mediana per pixel invece della media (piu' robusta agli scatti)
  hp         differenza meno la sua versione sfocata (passa-alto): le creste
             sono ad alta frequenza spaziale, l'illuminazione no
"""

import importlib.util
import statistics
import sys

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

W, H, FRAME = c2.W, c2.H, c2.FRAME


def load(path):
    d = open(path, "rb").read()
    return [list(d[i:i + FRAME]) for i in range(0, len(d) - FRAME + 1, FRAME)]


def chan_norm(d):
    m = [statistics.mean(d[k::3]) for k in range(3)]
    g = statistics.mean(m)
    return [d[i] + g - m[i % 3] for i in range(len(d))]


def pstretch(c, p=2.0):
    s = sorted(c)
    n = len(s)
    lo, hi = s[int(n * p / 100)], s[int(n * (100 - p) / 100)]
    if hi <= lo:
        hi = lo + 1
    return bytes(max(0, min(255, int((x - lo) * 255 / (hi - lo)))) for x in c)


def blur(img, r=2):
    """media su una finestra (2r+1)^2, bordi replicati"""
    out = [0.0] * len(img)
    for y in range(H):
        for x in range(W):
            acc = n = 0
            for dy in range(-r, r + 1):
                yy = min(H - 1, max(0, y + dy))
                for dx in range(-r, r + 1):
                    xx = min(W - 1, max(0, x + dx))
                    acc += img[yy * W + xx]
                    n += 1
            out[y * W + x] = acc / n
    return out


def highpass(img, r=2):
    b = blur(img, r)
    return [a - c for a, c in zip(img, b)]


def stat(name, img):
    print(f"  {name:12s} sd={statistics.pstdev(img):7.3f}  "
          f"range={min(img):8.2f}..{max(img):8.2f}")


def save(name, img, scale=6):
    c2.png_gray(f"rw-{name}.png", pstretch(img), W, H, scale=scale)


def main():
    refs = load(sys.argv[1] if len(sys.argv) > 1 else "hq-ref.raw")
    shots = load(sys.argv[2] if len(sys.argv) > 2 else "hq-dito.raw")
    print(f"{len(refs)} frame di fondo, {len(shots)} col dito")

    ref = [statistics.mean(v) for v in zip(*refs)]
    fin = [statistics.mean(v) for v in zip(*shots)]
    med = [statistics.median(v) for v in zip(*shots)]

    for name, img in (("fondo", chan_norm(ref)),
                      ("medio", chan_norm(fin)),
                      ("mediana", chan_norm(med)),
                      ("diff", chan_norm([a - b for a, b in zip(fin, ref)]))):
        stat(name, img)
        save(name, img)

    d = chan_norm([a - b for a, b in zip(fin, ref)])
    for r in (1, 2, 3):
        hp = highpass(d, r)
        stat(f"hp r={r}", hp)
        save(f"hp{r}", hp)

    hp = highpass(chan_norm(fin), 2)
    stat("hp diretto", hp)
    save("hpdir", hp)

    print("  salvati rw-*.png")


if __name__ == "__main__":
    main()
