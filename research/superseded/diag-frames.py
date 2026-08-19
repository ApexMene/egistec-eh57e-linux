#!/usr/bin/env python3
"""Diagnostica: il buffer immagine si aggiorna fra un fetch e l'altro?

Se due frame consecutivi sono identici byte per byte, non stiamo leggendo il
sensore ma un buffer statico, e la varianza non reagira' mai al dito.
"""

import statistics
import sys

sys.argv = [sys.argv[0]]  # evita che il modulo importato legga i nostri argomenti
import importlib.util

spec = importlib.util.spec_from_file_location("cap", "capture-057e.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

dev = cap.open_dev()
ok, tot = cap.init(dev)
print(f"init: {ok}/{tot}\n")

frames = []
for i in range(6):
    f = cap.grab(dev)
    frames.append(f)
    print(f"  frame {i}: len={len(f)} var={statistics.pvariance(f):7.2f} "
          f"media={statistics.fmean(f):6.1f} "
          f"min={min(f)} max={max(f)} sha={hash(f) & 0xffffff:06x}")

print("\n--- differenze fra frame consecutivi ---")
for i in range(1, len(frames)):
    a, b = frames[i - 1], frames[i]
    n = min(len(a), len(b))
    diff = sum(1 for j in range(n) if a[j] != b[j])
    print(f"  {i-1}->{i}: {diff}/{n} byte diversi ({100*diff/n:.1f}%)")

f = frames[-1]
print("\n--- prime 3 righe (114 byte ciascuna) ---")
for r in range(3):
    print("  " + f[r*114:(r+1)*114].hex(' '))

print("\n--- istogramma grezzo ---")
h = {}
for byte in f:
    h[byte] = h.get(byte, 0) + 1
top = sorted(h.items(), key=lambda kv: -kv[1])[:12]
print("  valore:conteggio  " + "  ".join(f"{v}:{c}" for v, c in top))
print(f"  valori distinti: {len(h)}")

cap.usb.util.release_interface(dev, 0)
