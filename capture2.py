#!/usr/bin/env python3
"""Cattura che replica il flusso del driver Windows EgisTouchFP057E.dll.

Ricostruito dal disassemblato della funzione a 0x18000935c ("Getting Zone1/2
Image"):

    reg 0x2c = 0x00
    ripeti 3 volte:
        reg 0x2d = 0x13          # arma l'acquisizione
        get_image(70, 57)        # 3990 byte
        reg 0x2d = 0x20          # chiudi
    binarizza: |pixel - riferimento| > 0x20

Le costanti vengono dal binario, non da congetture:
  0xf96  = 3990 = 70*57   lunghezza frame
  0x2ec2 = 11970 = 3990*3 buffer per i tre frame
  0x46   = 70             stride di riga
  0x39   = 57             altezza
"""

import statistics
import struct
import sys
import time
import zlib

import usb.core
import usb.util

VID, PID = 0x1C7A, 0x057E
EP_OUT, EP_IN = 0x01, 0x82

W, H = 70, 57
FRAME = W * H              # 0xf96 = 3990 pixel
NFRAMES = 3                # il driver ne prende tre
THRESH = 0x20              # soglia di binarizzazione del driver

# Il trasporto impacchetta 3 byte di payload ogni parola da 4 byte (il
# quarto e' sempre 0). Per ottenere FRAME pixel bisogna quindi chiedere
# FRAME*4/3 byte e scartare il byte di padding: verificato, chiedendo 5320
# tornano esattamente 3990 byte non nulli.
WIRE = FRAME * 4 // 3      # 5320

# guadagno e offset dell'AFE, trovati con afe-sweep.py
REG_GAIN, REG_OFFSET = 0x12, 0x0F

# init 0576, invariato: e' l'unica sequenza nota che il firmware accetta
INIT_SEQUENCE = [
    "45474953600000", "45474953600100", "454749536110fd", "45474953613502",
    "45474953618000", "45474953608000", "454749536110fc", "454749536301020f03",
    "45474953610c22", "45474953610983", "45474953632606066006052f06",
    "454749536110f4", "45474953610c44", "45474953615003", "45474953605000",
    "FLUSH",
    "45474953604000", "4547495363090b832400440f082020000052",
    "45474953632606066006052f06", "45474953612300", "45474953612438",
    "45474953612000", "45474953612145", "45474953600000", "45474953600100",
    "45474953632c020057", "45474953602d00", "45474953626703",
    "45474953600f00", "45474953632c020013",
]


def open_dev():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("sensore non trovato")
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except usb.core.USBError:
        pass
    # una run interrotta lascia la pipe disallineata: il reset e' l'unico
    # modo affidabile per ripartire in sincrono
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
    for _ in range(32):
        try:
            if not dev.read(EP_IN, 4096, timeout=30):
                return
        except usb.core.USBError:
            return


def cmd(dev, hexstr, read_len=64, timeout=1000):
    dev.write(EP_OUT, bytes.fromhex(hexstr), timeout=timeout)
    time.sleep(0.008)
    try:
        return bytes(dev.read(EP_IN, read_len, timeout=timeout))
    except usb.core.USBError:
        return b""


def wr(dev, reg, val):
    """cmd 0x61 = write register"""
    return cmd(dev, f"4547495361{reg:02x}{val:02x}")


def rd(dev, reg):
    """cmd 0x60 = read register"""
    r = cmd(dev, f"4547495360{reg:02x}00")
    return r[5] if len(r) >= 6 else None


def img_req(n=FRAME):
    return f"4547495364{(n >> 8) & 0xFF:02x}{n & 0xFF:02x}"


def init(dev):
    ok = 0
    for c in INIT_SEQUENCE:
        if c == "FLUSH":
            cmd(dev, img_req(), read_len=FRAME, timeout=1500)
            drain(dev)
            ok += 1
            continue
        if cmd(dev, c)[:4] == b"SIGE":
            ok += 1
    return ok, len(INIT_SEQUENCE)


def depad(wire):
    """Toglie il byte di padding da ogni parola di 4. La fase e' quella
    del residuo interamente nullo, non si assume che sia sempre la stessa."""
    counts = [sum(1 for b in wire[r::4] if b == 0) for r in range(4)]
    pad = max(range(4), key=lambda r: counts[r])
    return bytes(b for i, b in enumerate(wire) if i % 4 != pad)


def get_frame(dev):
    """Un frame secondo il flusso del driver: arma, leggi esattamente
    WIRE byte, chiudi. Legge a blocchi finche' non ha la lunghezza esatta,
    cosi' la pipe resta allineata per il frame successivo."""
    wr(dev, 0x2D, 0x13)
    dev.write(EP_OUT, bytes.fromhex(img_req(WIRE)), timeout=1000)

    buf = bytearray()
    t0 = time.time()
    while len(buf) < WIRE and time.time() - t0 < 1.5:
        try:
            chunk = dev.read(EP_IN, min(4096, WIRE - len(buf)), timeout=250)
        except usb.core.USBError:
            break
        if not chunk:
            break
        buf.extend(chunk)

    wr(dev, 0x2D, 0x20)
    if len(buf) < WIRE:
        return b""
    return depad(bytes(buf[:WIRE]))[:FRAME]


def burst(dev):
    """I tre frame consecutivi che prende il driver."""
    wr(dev, 0x2C, 0x00)
    return [get_frame(dev) for _ in range(NFRAMES)]


def stats(f):
    if len(f) < FRAME:
        return f"corto ({len(f)})"
    return (f"var={statistics.pvariance(f):8.2f} mean={sum(f)/len(f):6.1f} "
            f"min={min(f):3d} max={max(f):3d} distinti={len(set(f)):3d}")


def png_gray(path, data, w, h, scale=6):
    rows = []
    for y in range(h):
        line = data[y * w:(y + 1) * w]
        if scale > 1:
            line = bytes(px for px in line for _ in range(scale))
        for _ in range(scale):
            rows.append(b"\x00" + line)
    raw = b"".join(rows)

    def chunk(tag, payload):
        c = struct.pack(">I", len(payload)) + tag + payload
        return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w * scale, h * scale, 8, 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def stretch(data):
    lo, hi = min(data), max(data)
    if hi == lo:
        return data
    return bytes((b - lo) * 255 // (hi - lo) for b in data)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    dev = open_dev()
    ok, tot = init(dev)
    print(f"init: {ok}/{tot}")

    gain = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x08
    wr(dev, REG_GAIN, gain)
    print(f"guadagno reg {REG_GAIN:#04x} = {gain:#04x}")

    frames = burst(dev)
    for i, f in enumerate(frames):
        print(f"  frame {i}: {stats(f)}")
        if len(f) == FRAME:
            open(f"c2-{label}-{i}.bin", "wb").write(f)
            png_gray(f"c2-{label}-{i}.png", stretch(f), W, H)

    usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
