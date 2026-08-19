#!/usr/bin/env python3
"""Cattura continua con rilevamento del dito secondo il criterio del driver.

Uso: python3 live.py [secondi] [gain]

Prende i primi frame come riferimento (sensore libero), poi per ogni frame
conta i pixel che si discostano dal riferimento di piu' di 0x20 -- e' la
stessa binarizzazione che fa EgisTouchFP057E.dll a 0x18009497:

    mov eax, r10d ; sub eax, ecx ; cdq ; xor eax,edx ; sub eax,edx
    cmp eax, 0x20 ; jle skip ; mov byte ptr [r8], 1

Salva in PNG i frame che superano la soglia.
"""

import importlib.util
import sys
import time

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

THRESH = 0x20
REF_FRAMES = 6
HIT_RATIO = 0.06          # frazione di pixel deviati per dichiarare "dito"


def deviation(frame, ref):
    return sum(1 for a, b in zip(frame, ref) if abs(a - b) > THRESH)


def main():
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
    gain = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x08

    dev = c2.open_dev()
    ok, tot = c2.init(dev)
    c2.wr(dev, c2.REG_GAIN, gain)
    print(f"init {ok}/{tot}, gain {gain:#04x}", flush=True)

    print("costruisco il riferimento, NON toccare il sensore...", flush=True)
    refs = []
    while len(refs) < REF_FRAMES:
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) == c2.FRAME:
            refs.append(f)
    ref = bytes(sum(v) // len(refs) for v in zip(*refs))
    print(f"riferimento pronto (media di {len(refs)} frame, "
          f"mean={sum(ref)/len(ref):.1f})", flush=True)

    print(f"\n>>> TOCCA IL SENSORE, per i prossimi {dur:.0f}s <<<\n", flush=True)

    best = (0, None)
    n = 0
    t0 = time.time()
    while time.time() - t0 < dur:
        c2.wr(dev, 0x2C, 0x00)
        f = c2.get_frame(dev)
        if len(f) != c2.FRAME:
            continue
        n += 1
        d = deviation(f, ref)
        pct = d * 100.0 / c2.FRAME
        deltas = [abs(a - b) for a, b in zip(f, ref)]
        dmax, davg = max(deltas), sum(deltas) / len(deltas)
        # il conteggio sopra 0x20 e' il criterio del driver, ma per capire se
        # il sensore reagisce affatto serve anche la deviazione grezza
        score = max(d, 0)
        if score > best[0]:
            best = (score, f)
        mark = "  <<< DITO" if pct >= HIT_RATIO * 100 or dmax > 24 else ""
        if n % 10 == 0 or mark:
            print(f"  t={time.time()-t0:5.1f}s frame {n:4d} dev>32={d:5d} "
                  f"({pct:4.1f}%) |Δ|max={dmax:3d} |Δ|medio={davg:5.2f} "
                  f"mean={sum(f)/len(f):6.1f}{mark}", flush=True)
        if mark:
            c2.png_gray(f"live-dito-{n:04d}.png", c2.stretch(f), c2.W, c2.H)
            open(f"live-dito-{n:04d}.bin", "wb").write(f)

    print(f"\n--- {n} frame, massima deviazione {best[0]} "
          f"({best[0]*100.0/c2.FRAME:.1f}%) ---", flush=True)
    if best[1]:
        c2.png_gray("live-best.png", c2.stretch(best[1]), c2.W, c2.H)
        open("live-best.bin", "wb").write(best[1])
        print("salvato live-best.png", flush=True)
    c2.png_gray("live-ref.png", c2.stretch(ref), c2.W, c2.H)

    c2.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
