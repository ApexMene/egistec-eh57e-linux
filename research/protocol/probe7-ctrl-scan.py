#!/usr/bin/env python3
"""Probe v7: scan dei vendor control request in LETTURA.

Il device echeggia i comandi bulk => non inizializzato. L'init passa dai control
transfer (bReq 32 e 82 vanno in timeout su questo firmware).
Solo richieste device-to-host (lettura), nessuna scrittura: non modifica stato.
"""

import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device non trovato")

    dev.reset()
    time.sleep(0.5)
    dev.set_configuration(1)

    hits = []
    for bm in (0xC0, 0xC1):  # vendor: device, interface — sempre IN
        label = "device" if bm == 0xC0 else "interface"
        print(f"--- bmRequestType {bm:#04x} ({label}, device-to-host) ---")
        found = 0
        for breq in range(256):
            for windex in (0, 4):
                try:
                    resp = dev.ctrl_transfer(bm, breq, 0x0000, windex, 64, timeout=200)
                except usb.core.USBError:
                    continue
                data = resp.tobytes()
                if data:
                    print(f"  HIT bReq={breq:3d} ({breq:#04x}) wIndex={windex} "
                          f"len={len(data)}: {data.hex(' ')}")
                    hits.append((bm, breq, windex, data))
                    found += 1
        if not found:
            print("  nessuna risposta")
        print()

    print(f"Totale control request che rispondono: {len(hits)}")
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
