#!/usr/bin/env python3
"""Probe v3: protocollo egis0570 (image-based), sequenza init_pkts2.

Pacchetti da 7 byte su EP OUT 0x01, risposte su EP IN 0x83 (interrupt).
Dopo l'ultimo pacchetto il sensore dovrebbe restituire 32512 byte di immagine.
Non distruttivo: il sensore è image-based, non memorizza nulla.
"""

import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN = 0x01, 0x83
PKTSIZE = 7
INPSIZE = 32512

INIT_PKTS2 = [
    b"\x45\x47\x49\x53\x01\x10\x00",
    b"\x45\x47\x49\x53\x01\x11\x38",
    b"\x45\x47\x49\x53\x01\x12\x00",
    b"\x45\x47\x49\x53\x01\x13\x71",
    b"\x45\x47\x49\x53\x01\x20\x3f",
    b"\x45\x47\x49\x53\x01\x58\x3f",
    b"\x45\x47\x49\x53\x01\x21\x07",
    b"\x45\x47\x49\x53\x01\x57\x07",
    b"\x45\x47\x49\x53\x01\x22\x02",
    b"\x45\x47\x49\x53\x01\x56\x02",
    b"\x45\x47\x49\x53\x01\x23\x00",
    b"\x45\x47\x49\x53\x01\x55\x00",
    b"\x45\x47\x49\x53\x01\x24\x00",
    b"\x45\x47\x49\x53\x01\x54\x00",
    b"\x45\x47\x49\x53\x01\x25\x00",
    b"\x45\x47\x49\x53\x01\x53\x00",
    b"\x45\x47\x49\x53\x01\x15\x00",
    b"\x45\x47\x49\x53\x01\x16\x3b",
    b"\x45\x47\x49\x53\x01\x09\x0a",
    b"\x45\x47\x49\x53\x01\x14\x00",
    b"\x45\x47\x49\x53\x01\x02\x0f",
    b"\x45\x47\x49\x53\x01\x03\x80",
    b"\x45\x47\x49\x53\x00\x02\x80",
    b"\x45\x47\x49\x53\x01\x02\x2f",
    b"\x45\x47\x49\x53\x06\x00\xfe",  # dopo questo arriva l'immagine
]


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device non trovato")

    dev.reset()
    time.sleep(0.5)
    dev.set_configuration(1)
    usb.util.claim_interface(dev, 0)
    print(f"Device pronto — invio {len(INIT_PKTS2)} pacchetti init\n")

    ok = 0
    for i, pkt in enumerate(INIT_PKTS2):
        try:
            dev.write(EP_OUT, pkt, timeout=5000)
        except usb.core.USBError as e:
            print(f"[{i:02d}] TX {pkt.hex(' ')} -> WRITE FAIL: {e}")
            continue

        is_last = i == len(INIT_PKTS2) - 1
        if is_last:
            print(f"[{i:02d}] TX {pkt.hex(' ')} -> ultimo pacchetto, leggo immagine...")
            break

        try:
            resp = dev.read(EP_IN, PKTSIZE, timeout=5000).tobytes()
            marker = "OK " if resp.startswith(b"SIGE") else "?? "
            if resp.startswith(b"SIGE"):
                ok += 1
            print(f"[{i:02d}] TX {pkt.hex(' ')} -> {marker}RX {resp.hex(' ')}")
        except usb.core.USBError as e:
            print(f"[{i:02d}] TX {pkt.hex(' ')} -> READ FAIL: {e}")

    print(f"\nRisposte SIGE valide: {ok}/{len(INIT_PKTS2) - 1}")

    print("\n--- Lettura immagine (32512 byte attesi) ---")
    total = b""
    try:
        while len(total) < INPSIZE:
            chunk = dev.read(EP_IN, INPSIZE - len(total), timeout=10000).tobytes()
            if not chunk:
                break
            total += chunk
            print(f"  chunk {len(chunk)} byte (totale {len(total)}/{INPSIZE})")
    except usb.core.USBError as e:
        print(f"  stop: {e}")

    print(f"\nTotale ricevuto: {len(total)} byte")
    if total:
        with open("capture-057e.bin", "wb") as f:
            f.write(total)
        vals = sorted(set(total))
        print(f"Salvato in capture-057e.bin")
        print(f"Valori distinti: {len(vals)}, min={vals[0]}, max={vals[-1]}")
        print(f"Primi 64 byte: {total[:64].hex(' ')}")

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
