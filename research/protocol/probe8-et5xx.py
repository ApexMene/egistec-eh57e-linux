#!/usr/bin/env python3
"""Probe v8: set di comandi ET5XX reale (0x60/0x61/0x62/0x63/0x64).

I driver upstream (egis0570 / egismoc) usano type 0x00/0x01: il firmware non li
riconosce e si limita a rimandare indietro i byte (vedi probe6). Il driver
Windows EgisTouchFP057E.dll e il lavoro su EH576 mostrano che la famiglia ET5XX
usa comandi 0x6X.

Fase A: verifica che 0x60 NON sia un eco (risposta indipendente dal byte dummy).
Fase B: burst-read registri per identificare il sensore.
"""

import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN = 0x01, 0x82


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


def cmd(dev, hexs, read_len=64, timeout=1000, quiet=False):
    pkt = bytes.fromhex(hexs)
    try:
        dev.write(EP_OUT, pkt, timeout=timeout)
    except usb.core.USBError as e:
        if not quiet:
            print(f"  TX {hexs:<24s} -> WRITE FAIL: {e}")
        return b""
    time.sleep(0.01)
    try:
        resp = dev.read(EP_IN, read_len, timeout=timeout).tobytes()
    except usb.core.USBError:
        resp = b""
    if not quiet:
        shown = resp[:16].hex(' ') + (" ..." if len(resp) > 16 else "")
        print(f"  TX {hexs:<24s} -> RX[{len(resp):5d}] {shown}")
    return resp


def main():
    dev = open_dev()

    print("=== FASE A: 0x60 e' un comando vero o un eco? ===")
    print("(se la risposta segue il byte dummy => eco; se e' stabile => comando eseguito)")
    a = cmd(dev, "45474953600000")   # read reg 0x00
    b = cmd(dev, "454749536000aa")   # stesso reg, dummy diverso
    c = cmd(dev, "454749536001aa")   # reg 0x01
    d = cmd(dev, "45474953600100")   # reg 0x01, dummy 0

    echo = (len(a) >= 6 and len(b) >= 6 and a[4:6] != b[4:6])
    print()
    if echo:
        print("  >> ancora ECO: la risposta segue il dummy.")
    else:
        print("  >> NON e' un eco: 0x60 e' interpretato come comando.")
        print(f"     reg0x00 = {a[4:7].hex(' ') if len(a) >= 7 else '?'}")
        print(f"     reg0x01 = {d[4:7].hex(' ') if len(d) >= 7 else '?'}")

    print("\n=== FASE B: burst-read registri (0x62) ===")
    for start, n in ((0x00, 0x20), (0x20, 0x20)):
        cmd(dev, f"45474953 62 {start:02x} {n:02x}".replace(" ", ""), read_len=256)

    print("\n=== FASE C: scan registri singoli 0x00-0x2f (0x60) ===")
    vals = {}
    for reg in range(0x30):
        r = cmd(dev, f"4547495360{reg:02x}00", quiet=True)
        if len(r) >= 7:
            vals[reg] = r[4:7]
    for reg, v in vals.items():
        print(f"  reg {reg:#04x} = {v.hex(' ')}")
    distinct = len({v.hex() for v in vals.values()})
    print(f"\n  valori distinti: {distinct}/{len(vals)}"
          f"  ({'PROMETTENTE' if distinct > 3 else 'sospetto: troppo uniforme'})")

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
