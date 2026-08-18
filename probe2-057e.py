#!/usr/bin/env python3
"""Probe v2: la risposta a ogni comando arriva troncata a 7 byte.

Drena tutti gli endpoint IN dopo ogni comando per capire dove finisce il resto
del payload. Non distruttivo.
"""

import struct
import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN, EP_INTR, EP_INTR2 = 0x01, 0x82, 0x83, 0x84

WRITE_PREFIX = b"EGIS\x00\x00\x00\x01"

INIT_SEQUENCE = [
    ("init-1 (7f)", b"\x07\x50\x7f\x00\x00\x00\x00\x0c"),
    ("init-2 (43)", b"\x07\x50\x43\x00\x00\x00\x00\x04"),
    ("init-3 (07)", b"\x07\x50\x07\x00\x02\x00\x00\x1d"),
    ("list-fingers (19)", b"\x07\x50\x19\x04\x00\x00\x01\x40"),
]


def check_bytes(payload):
    full = WRITE_PREFIX + b"\x00\x00\x00\x00\x00" + payload
    words = []
    for i in range(0, len(full), 2):
        chunk = full[i:i + 2]
        if len(chunk) == 1:
            chunk += b"\x00"
        words.append(struct.unpack(">H", chunk)[0])
    return struct.pack(">H", 0xFFFF - (sum(words) % 0xFFFF))


def drain(dev, ep, label, tries=4, timeout=800, length=4096):
    for n in range(tries):
        try:
            data = dev.read(ep, length, timeout=timeout).tobytes()
        except usb.core.USBError:
            if n == 0:
                print(f"    {label}: (niente)")
            return
        print(f"    {label}[{n}] len={len(data)}: {data.hex(' ')}")


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device non trovato")

    dev.reset()
    time.sleep(0.5)
    dev.set_configuration(1)
    usb.util.claim_interface(dev, 0)
    print(f"Device pronto. maxPacketSize bulk = 512\n")

    for label, payload in INIT_SEQUENCE:
        full = WRITE_PREFIX + check_bytes(payload) + b"\x00\x00\x00" + payload
        print(f"[{label}] TX {full.hex(' ')}")
        try:
            written = dev.write(EP_OUT, full, timeout=5000)
            print(f"    scritti {written} byte")
        except usb.core.USBError as e:
            print(f"    WRITE FAILED: {e}")
            continue

        drain(dev, EP_IN, "BULK-IN 0x82")
        drain(dev, EP_INTR, "INTR 0x83", tries=2, timeout=500, length=64)
        drain(dev, EP_INTR2, "INTR 0x84", tries=2, timeout=500, length=64)
        print()

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
