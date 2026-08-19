#!/usr/bin/env python3
"""Cattura N frame grezzi interi (6498 byte) e li salva senza interpretarli.

Uso: python3 frames.py <etichetta> [n]

Il buffer del sensore e' 114x57 = 6498 byte. Gli script precedenti lo
troncavano a 3990 assumendo 70x57 (la geometria del 0576) e finivano ad
analizzare una fetta disallineata: da qui la conclusione sbagliata che
l'immagine fosse rumore.
"""

import importlib.util
import sys
import time

spec = importlib.util.spec_from_file_location("cap", "capture-057e.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

IMG_SIZE = 114 * 57


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12

    dev = cap.open_dev()
    ok, tot = cap.init(dev)
    print(f"init: {ok}/{tot}")

    kept = 0
    for i in range(n * 3):
        f = bytes(cap.grab(dev))
        if len(f) != IMG_SIZE:
            print(f"  scarto frame len={len(f)}")
            continue
        nz = sum(1 for b in f if b)
        if nz < IMG_SIZE // 4:          # buffer non ancora riempito
            print(f"  scarto frame vuoto (nonzero={nz})")
            continue
        path = f"raw-{label}-{kept:02d}.bin"
        open(path, "wb").write(f)
        print(f"  {path}  nonzero={nz}  min={min(f)} max={max(f)}")
        kept += 1
        if kept >= n:
            break
        time.sleep(0.05)

    print(f"\nsalvati {kept} frame raw-{label}-*.bin")
    cap.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
