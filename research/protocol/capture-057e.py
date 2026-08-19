#!/usr/bin/env python3
"""Cattura immagini dal sensore Egis 1c7a:057e (famiglia ET5XX).

Init + polling + fetch del buffer immagine. Rileva il dito via varianza di
popolazione: il sensore non segnala il tocco, la discriminazione e' software.

Uso:
  python3 capture-057e.py            # loop: mostra la varianza in tempo reale
  python3 capture-057e.py N          # salva N frame con dito rilevato
"""

import statistics
import sys
import time

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN = 0x01, 0x82
IMG_W, IMG_H = 114, 57
IMG_SIZE = IMG_W * IMG_H

INIT_SEQUENCE = [
    "45474953600000", "45474953600100", "454749536110fd", "45474953613502",
    "45474953618000", "45474953608000", "454749536110fc", "454749536301020f03",
    "45474953610c22", "45474953610983", "45474953632606066006052f06",
    "454749536110f4", "45474953610c44", "45474953615003", "45474953605000",
    "FLUSH",  # svuota il buffer immagine (0x64 + size); size inserita in init()
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


def open_dev():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("device 1c7a:057e non trovato")
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass
    # una run interrotta lascia la pipe disallineata: il reset riporta il
    # sensore a uno stato noto prima di rifare l'init.
    try:
        dev.reset()
        time.sleep(0.8)
        dev = usb.core.find(idVendor=VID, idProduct=PID)
    except usb.core.USBError:
        pass
    dev.set_configuration()
    usb.util.claim_interface(dev, 0)
    return dev


def drain(dev):
    """Svuota la pipe IN: una fetch parziale lascia byte in coda e disallinea
    tutte le letture successive."""
    for _ in range(16):
        try:
            if not dev.read(EP_IN, 4096, timeout=50):
                return
        except usb.core.USBError:
            return


def cmd(dev, hexs, read_len=64, timeout=1000):
    try:
        dev.write(EP_OUT, bytes.fromhex(hexs), timeout=timeout)
    except usb.core.USBError:
        return b""
    time.sleep(0.008)
    try:
        return dev.read(EP_IN, read_len, timeout=timeout).tobytes()
    except usb.core.USBError:
        return b""


def init(dev):
    ok = 0
    for c in INIT_SEQUENCE:
        if c == "FLUSH":
            cmd(dev, img_request(), read_len=IMG_SIZE, timeout=1500)
            drain(dev)
            ok += 1
            continue
        if cmd(dev, c)[:4] == b"SIGE":
            ok += 1
    return ok, len(INIT_SEQUENCE)


def img_request():
    return f"4547495364{(IMG_SIZE >> 8) & 0xff:02x}{IMG_SIZE & 0xff:02x}"


def grab(dev):
    # svuotare PRIMA: farlo dopo il poll mangia i primi byte del frame
    drain(dev)
    for c in REPEAT_SEQUENCE:
        cmd(dev, c)
    cmd(dev, "45474953600000", timeout=500)

    try:
        dev.write(EP_OUT, bytes.fromhex(img_request()), timeout=1000)
    except usb.core.USBError:
        return b""

    buf = bytearray()
    deadline = time.time() + 0.6
    while time.time() < deadline and len(buf) < IMG_SIZE:
        try:
            buf.extend(dev.read(EP_IN, 4096, timeout=150).tobytes())
        except usb.core.USBError:
            break
    return bytes(buf[:IMG_SIZE])


def save_pgm(path, data):
    with open(path, "wb") as f:
        f.write(b"P5\n%d %d\n255\n" % (IMG_W, IMG_H))
        f.write(data.ljust(IMG_SIZE, b"\0")[:IMG_SIZE])


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    dev = open_dev()
    ok, tot = init(dev)
    print(f"init: {ok}/{tot} comandi accettati\n")

    print("Appoggia e togli il dito. Ctrl-C per uscire.\n")
    saved = 0
    try:
        while True:
            img = grab(dev)
            if len(img) < IMG_SIZE:
                print(f"\r  frame corto ({len(img)} B)          ", end="")
                continue
            var = statistics.pvariance(img)
            mean = statistics.fmean(img)
            bar = "#" * min(int(var), 60)
            state = "DITO" if var > 12 else "    "
            print(f"\r  var={var:7.2f} media={mean:6.1f} {state} {bar:<60s}", end="")
            if target and var > 12:
                saved += 1
                name = f"finger-{saved:03d}"
                save_pgm(name + ".pgm", img)
                open(name + ".bin", "wb").write(img)
                print(f"\n  salvato {name}.pgm (var={var:.2f}) — togli il dito")
                time.sleep(1.5)
                if saved >= target:
                    break
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        usb.util.release_interface(dev, 0)
        usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
