#!/usr/bin/env python3
"""Probe v9: init ET5XX + cattura immagine dal 1c7a:057e.

Sequenza di init presa dal lavoro su EH576 (1c7a:0576, stessa famiglia ET5XX) e
adattata. La dimensione immagine del 057e non e' nota a priori: il comando 0x64
porta la lunghezza richiesta nei due byte di parametro, quindi proviamo diverse
geometrie e teniamo quella che il sensore serve per intero.

Uso:
  python3 probe9-image.py            # scan dimensioni + 1 frame
  python3 probe9-image.py 0x1962     # forza una dimensione
"""

import statistics
import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN = 0x01, 0x82

INIT_SEQUENCE = [
    "45474953600000", "45474953600100", "454749536110fd", "45474953613502",
    "45474953618000", "45474953608000", "454749536110fc", "454749536301020f03",
    "45474953610c22", "45474953610983", "45474953632606066006052f06",
    "454749536110f4", "45474953610c44", "45474953615003", "45474953605000",
    "45474953604000", "4547495363090b832400440f082020000052",
    "45474953632606066006052f06", "45474953612300", "45474953612438",
    "45474953612000", "45474953612145", "45474953600000", "45474953600100",
    "45474953632c020057", "45474953602d00", "45474953626703",
    "45474953600f00", "45474953632c020013",
]

REPEAT_SEQUENCE = [
    "45474953632c020057", "45474953602d00", "45474953626703",
    "45474953600f00", "45474953632c020013",
]

# geometrie plausibili per la famiglia: (larghezza, altezza)
CANDIDATES = [(70, 57), (114, 57), (120, 56), (64, 80), (96, 96), (128, 56)]


def open_dev():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device 1c7a:057e non trovato")
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)
    return dev


def cmd(dev, hexs, read_len=64, timeout=1000):
    try:
        dev.write(EP_OUT, bytes.fromhex(hexs), timeout=timeout)
    except usb.core.USBError:
        return b""
    time.sleep(0.01)
    try:
        return dev.read(EP_IN, read_len, timeout=timeout).tobytes()
    except usb.core.USBError:
        return b""


def fetch_image(dev, nbytes, settle=0.4):
    """Chiede nbytes di immagine e legge finche' arrivano o scade il tempo."""
    for c in REPEAT_SEQUENCE:
        cmd(dev, c)
    cmd(dev, "45474953600000", timeout=500)

    req = f"45474953 64 {(nbytes >> 8) & 0xff:02x} {nbytes & 0xff:02x}".replace(" ", "")
    try:
        dev.write(EP_OUT, bytes.fromhex(req), timeout=1000)
    except usb.core.USBError as e:
        return b"", f"write fail: {e}"

    buf = bytearray()
    deadline = time.time() + settle
    while time.time() < deadline and len(buf) < nbytes:
        try:
            buf.extend(dev.read(EP_IN, 4096, timeout=150).tobytes())
        except usb.core.USBError:
            break
    return bytes(buf), None


def save_pgm(path, data, w, h):
    with open(path, "wb") as f:
        f.write(b"P5\n%d %d\n255\n" % (w, h))
        f.write(data[:w * h])


def main():
    dev = open_dev()

    print("=== init ET5XX ===")
    ok = 0
    for c in INIT_SEQUENCE:
        r = cmd(dev, c)
        if r[:4] == b"SIGE":
            ok += 1
    print(f"  {ok}/{len(INIT_SEQUENCE)} comandi con risposta SIGE valida")

    if len(sys.argv) > 1:
        n = int(sys.argv[1], 0)
        cands = [(n, 1)]
    else:
        cands = CANDIDATES

    print("\n=== scan geometrie (dito NON sul sensore) ===")
    best = None
    for w, h in cands:
        n = w * h
        data, err = fetch_image(dev, n)
        if err:
            print(f"  {w}x{h} ({n:5d} B): {err}")
            continue
        var = statistics.pvariance(data) if len(data) > 1 else 0.0
        full = "COMPLETO" if len(data) >= n else "parziale"
        print(f"  {w}x{h} ({n:5d} B): ricevuti {len(data):5d} B  {full:8s} var={var:8.2f}")
        if len(data) >= n and (best is None or n > best[0] * best[1]):
            best = (w, h)

    if best is None:
        print("\nNessuna geometria servita per intero. Il sensore risponde ai comandi ma")
        print("non consegna il buffer immagine: serve un passo di init aggiuntivo.")
        usb.util.release_interface(dev, 0)
        return

    w, h = best
    n = w * h
    print(f"\n=== cattura con {w}x{h} ===")
    base, _ = fetch_image(dev, n)
    vbase = statistics.pvariance(base)
    print(f"  baseline (nessun dito): var={vbase:.2f}")

    print("\n  >>> APPOGGIA IL DITO SUL SENSORE <<<")
    for i in range(4, 0, -1):
        print(f"      {i}...")
        time.sleep(1)

    frame, _ = fetch_image(dev, n)
    vf = statistics.pvariance(frame)
    print(f"  con dito: var={vf:.2f}   (delta {vf - vbase:+.2f})")

    save_pgm("frame-baseline.pgm", base, w, h)
    save_pgm("frame-finger.pgm", frame, w, h)
    open("frame-finger.bin", "wb").write(frame)
    print("\n  salvati: frame-baseline.pgm, frame-finger.pgm, frame-finger.bin")
    if vf > vbase * 3 and vf > 12:
        print("  >> VARIANZA ESPLOSA: e' un'impronta.")
    else:
        print("  >> varianza piatta: buffer non ancora valido o dito non rilevato.")

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
