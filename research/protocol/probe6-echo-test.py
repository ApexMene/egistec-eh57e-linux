#!/usr/bin/env python3
"""Probe v6: il device esegue davvero i comandi o fa solo eco?

Se risponde SIGE anche a comandi spazzatura, l'init "24/24" non prova nulla.
Verifica anche se una write seguita da read del registro restituisce il valore scritto.
"""

import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN = 0x01, 0x82


def main():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device non trovato")

    dev.reset()
    time.sleep(0.5)
    dev.set_configuration(1)
    usb.util.claim_interface(dev, 0)

    def cmd(pkt, label):
        try:
            dev.write(EP_OUT, pkt, timeout=3000)
            resp = dev.read(EP_IN, 64, timeout=3000).tobytes()
            print(f"  {label:28s} TX {pkt.hex(' ')} -> RX {resp.hex(' ')}")
            return resp
        except usb.core.USBError as e:
            print(f"  {label:28s} TX {pkt.hex(' ')} -> FAIL: {e}")
            return None

    print("--- A. Comandi spazzatura (registri inesistenti / prefisso errato) ---")
    cmd(b"\x45\x47\x49\x53\x01\xaa\x55", "reg 0xAA = 0x55 (fake)")
    cmd(b"\x45\x47\x49\x53\x01\xff\xff", "reg 0xFF = 0xFF (fake)")
    cmd(b"\x45\x47\x49\x53\x99\x99\x99", "type 0x99 (invalido)")
    cmd(b"\x00\x00\x00\x00\x01\x10\x00", "prefisso NON-EGIS")
    cmd(b"\xde\xad\xbe\xef\xde\xad\xbe", "spazzatura totale")

    print("\n--- B. Write/read coerente? (scrivo valore, rileggo registro) ---")
    for reg, val in [(0x11, 0x38), (0x11, 0x12), (0x13, 0x71), (0x13, 0x44)]:
        cmd(bytes([0x45, 0x47, 0x49, 0x53, 0x01, reg, val]), f"WRITE reg {reg:#04x}={val:#04x}")
        cmd(bytes([0x45, 0x47, 0x49, 0x53, 0x00, reg, 0x00]), f"READ  reg {reg:#04x}")

    print("\n--- C. Read stesso registro con valore-dummy diverso ---")
    print("    (se la risposta segue il dummy invece del valore scritto = puro eco)")
    cmd(b"\x45\x47\x49\x53\x00\x11\x00", "READ reg 0x11 (dummy 0x00)")
    cmd(b"\x45\x47\x49\x53\x00\x11\xaa", "READ reg 0x11 (dummy 0xAA)")
    cmd(b"\x45\x47\x49\x53\x00\x11\x5c", "READ reg 0x11 (dummy 0x5C)")

    usb.util.release_interface(dev, 0)
    usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
