#!/usr/bin/env python3
"""Probe v5: init OK (24/24), manca il trigger immagine.

Completa l'init, manda il comando di capture e poi ascolta TUTTI gli endpoint IN
per capire dove/quando arriva l'immagine. Tocca il sensore quando richiesto.
"""

import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT = 0x01
EPS_IN = [(0x82, "BULK 0x82"), (0x83, "INTR 0x83"), (0x84, "INTR 0x84")]
INPSIZE = 32512

INIT_PKTS2 = [
    b"\x45\x47\x49\x53\x01\x10\x00", b"\x45\x47\x49\x53\x01\x11\x38",
    b"\x45\x47\x49\x53\x01\x12\x00", b"\x45\x47\x49\x53\x01\x13\x71",
    b"\x45\x47\x49\x53\x01\x20\x3f", b"\x45\x47\x49\x53\x01\x58\x3f",
    b"\x45\x47\x49\x53\x01\x21\x07", b"\x45\x47\x49\x53\x01\x57\x07",
    b"\x45\x47\x49\x53\x01\x22\x02", b"\x45\x47\x49\x53\x01\x56\x02",
    b"\x45\x47\x49\x53\x01\x23\x00", b"\x45\x47\x49\x53\x01\x55\x00",
    b"\x45\x47\x49\x53\x01\x24\x00", b"\x45\x47\x49\x53\x01\x54\x00",
    b"\x45\x47\x49\x53\x01\x25\x00", b"\x45\x47\x49\x53\x01\x53\x00",
    b"\x45\x47\x49\x53\x01\x15\x00", b"\x45\x47\x49\x53\x01\x16\x3b",
    b"\x45\x47\x49\x53\x01\x09\x0a", b"\x45\x47\x49\x53\x01\x14\x00",
    b"\x45\x47\x49\x53\x01\x02\x0f", b"\x45\x47\x49\x53\x01\x03\x80",
    b"\x45\x47\x49\x53\x00\x02\x80", b"\x45\x47\x49\x53\x01\x02\x2f",
]
CAPTURE_PKT = b"\x45\x47\x49\x53\x06\x00\xfe"


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device non trovato")

    dev.reset()
    time.sleep(0.5)
    dev.set_configuration(1)
    usb.util.claim_interface(dev, 0)

    for pkt in INIT_PKTS2:
        dev.write(EP_OUT, pkt, timeout=5000)
        dev.read(0x82, 7, timeout=5000)
    print("Init completato (24/24)\n")

    print(">>> APPOGGIA IL DITO SUL TASTO DI ACCENSIONE E TIENILO PREMUTO <<<")
    for i in range(3, 0, -1):
        print(f"    {i}...")
        time.sleep(1)

    print(f"\nTX capture: {CAPTURE_PKT.hex(' ')}")
    dev.write(EP_OUT, CAPTURE_PKT, timeout=5000)

    print("\nAscolto tutti gli endpoint IN per 15 secondi...\n")
    deadline = time.time() + 15
    totals = {ep: 0 for ep, _ in EPS_IN}
    samples = {ep: [] for ep, _ in EPS_IN}

    while time.time() < deadline:
        for ep, label in EPS_IN:
            try:
                data = dev.read(ep, 4096, timeout=300).tobytes()
            except usb.core.USBError:
                continue
            totals[ep] += len(data)
            if len(data) != 7 or not data.startswith(b"SIGE"):
                print(f"  !! {label} PAYLOAD ANOMALO len={len(data)}: {data[:32].hex(' ')}")
            if len(samples[ep]) < 400:
                samples[ep].append(data)

    print("\n--- Totali ---")
    for ep, label in EPS_IN:
        print(f"  {label}: {totals[ep]} byte")
        blob = b"".join(samples[ep])
        if blob:
            uniq = sorted(set(blob))
            print(f"      valori distinti={len(uniq)} min={uniq[0]} max={uniq[-1]}")
            non_ack = [s for s in samples[ep] if not (len(s) == 7 and s.startswith(b"SIGE"))]
            print(f"      risposte non-ACK: {len(non_ack)}/{len(samples[ep])}")
            if non_ack:
                with open(f"capture-ep{ep:02x}.bin", "wb") as f:
                    f.write(b"".join(non_ack))
                print(f"      salvato capture-ep{ep:02x}.bin")

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
