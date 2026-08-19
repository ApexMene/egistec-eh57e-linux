#!/usr/bin/env python3
"""Test A/B cronometrato: 8 s senza dito, 8 s con dito premuto.

Registra ogni frame e confronta le due finestre. Se il sensore sta davvero
leggendo il polpastrello, varianza e istogramma cambiano in modo netto.
"""

import importlib.util
import statistics
import sys
import time

spec = importlib.util.spec_from_file_location("cap", "capture-057e.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

PHASE = 8.0


def collect(dev, seconds, label):
    out = []
    end = time.time() + seconds
    while time.time() < end:
        f = cap.grab(dev)
        if len(f) == cap.IMG_SIZE:
            out.append(f)
        left = end - time.time()
        print(f"\r  [{label}] {left:4.1f}s  frame={len(out)}   ", end="", flush=True)
    print()
    return out


def summarize(frames, label):
    if not frames:
        print(f"  {label}: nessun frame")
        return None
    var = [statistics.pvariance(f) for f in frames]
    mean = [statistics.fmean(f) for f in frames]
    mn = [min(f) for f in frames]
    mx = [max(f) for f in frames]
    dist = [len(set(f)) for f in frames]
    print(f"  {label}: n={len(frames)}")
    print(f"     varianza  min={min(var):7.2f} med={statistics.median(var):7.2f} max={max(var):7.2f}")
    print(f"     media     min={min(mean):7.2f} med={statistics.median(mean):7.2f} max={max(mean):7.2f}")
    print(f"     range px  min={min(mn):3d}  max={max(mx):3d}   valori distinti med={statistics.median(dist):.0f}")
    return dict(var=var, mean=mean, frames=frames)


def main():
    dev = cap.open_dev()
    ok, tot = cap.init(dev)
    print(f"init: {ok}/{tot}\n")

    print(">>> FASE 1: NON toccare il sensore <<<")
    time.sleep(1.5)
    a = collect(dev, PHASE, "libero")

    print("\n>>> FASE 2: PREMI IL DITO ADESSO e tienilo fermo <<<")
    time.sleep(1.5)
    b = collect(dev, PHASE, "dito  ")

    print("\n--- risultati ---")
    sa = summarize(a, "senza dito")
    sb = summarize(b, "con dito  ")

    if sa and sb:
        va, vb = statistics.median(sa["var"]), statistics.median(sb["var"])
        ma, mb = statistics.median(sa["mean"]), statistics.median(sb["mean"])
        print(f"\n  delta varianza: {vb - va:+.2f}   delta media: {mb - ma:+.2f}")
        if vb > va * 2:
            print("  >> IL SENSORE VEDE IL DITO.")
        else:
            print("  >> nessuna reazione: il buffer letto non e' l'area del polpastrello,")
            print("     oppure manca un comando di esposizione/scan.")
        cap.save_pgm("ab-libero.pgm", sa["frames"][len(sa["frames"]) // 2])
        cap.save_pgm("ab-dito.pgm", sb["frames"][len(sb["frames"]) // 2])
        open("ab-dito.bin", "wb").write(sb["frames"][len(sb["frames"]) // 2])
        open("ab-libero.bin", "wb").write(sa["frames"][len(sa["frames"]) // 2])
        print("  salvati ab-libero.pgm / ab-dito.pgm (+ .bin)")

    cap.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
