#!/usr/bin/env python3
"""Probe non distruttivo per EgisTec EH57E (1c7a:057e).

Esegue solo la sequenza di init del protocollo Egis MoC e riporta dove fallisce.
Non registra, non cancella, non modifica nulla sul sensore.
"""

import struct
import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E

# Endpoint reali di questo device (da lsusb -v), diversi dal 0582 upstream
EP_OUT = 0x01
EP_IN = 0x82
EP_INTR = 0x83

WRITE_PREFIX = b"EGIS\x00\x00\x00\x01"
READ_PREFIX = b"SIGE\x00\x00\x00\x01"

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


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit(f"Device {VID:04x}:{PID:04x} non trovato")

    print(f"Trovato {VID:04x}:{PID:04x} su bus {dev.bus} addr {dev.address}")

    if dev.is_kernel_driver_active(0):
        print("Driver kernel attivo su interface 0 -> detach")
        dev.detach_kernel_driver(0)

    dev.reset()
    time.sleep(0.5)
    dev.set_configuration(1)
    usb.util.claim_interface(dev, 0)
    print("Interface 0 acquisita\n")

    print("--- Control transfers ---")
    for desc, args in [
        ("bmReq=0xc0 bReq=32 len=16", (0xC0, 32, 0x0000, 4, 16)),
        ("bmReq=0xc0 bReq=32 len=40", (0xC0, 32, 0x0000, 4, 40)),
        ("bmReq=0x80 bReq=0 len=2", (0x80, 0, 0x0000, 0, 2)),
        ("bmReq=0xc0 bReq=82 len=8", (0xC0, 82, 0x0000, 0, 8)),
    ]:
        try:
            resp = dev.ctrl_transfer(*args)
            print(f"  OK   {desc}: {resp.tobytes().hex(' ')}")
        except usb.core.USBError as e:
            print(f"  FAIL {desc}: {e}")

    print("\n--- Sequenza init (bulk) ---")
    for label, payload in INIT_SEQUENCE:
        full = WRITE_PREFIX + check_bytes(payload) + b"\x00\x00\x00" + payload
        print(f"\n[{label}]")
        print(f"  TX: {full.hex(' ')}")
        try:
            dev.write(EP_OUT, full, timeout=5000)
        except usb.core.USBError as e:
            print(f"  WRITE FAILED: {e}")
            break
        try:
            resp = dev.read(EP_IN, 4096, timeout=5000).tobytes()
        except usb.core.USBError as e:
            print(f"  READ FAILED: {e}")
            break
        print(f"  RX: {resp.hex(' ')}")
        if resp.startswith(READ_PREFIX):
            print("  >>> PREFISSO SIGE VALIDO — protocollo Egis MoC confermato")
        else:
            print(f"  >>> prefisso inatteso: {resp[:8].hex(' ')}")

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
