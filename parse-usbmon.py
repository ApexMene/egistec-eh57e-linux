#!/usr/bin/env python3
"""Decodifica una cattura usbmon del sensore Egis in comandi EGIS/SIGE.

Il log arriva da usbmon-capture.sh, cioe' dall'interfaccia testo di usbmon:

    <tag> <ts_us> <S|C|E> <Bo:3:005:1> <status> <len> [= <parole esadecimali>]

Il quarto campo e' `tipo+direzione : bus : device : endpoint`. Interessano solo
il device 005 sugli endpoint bulk 1 (OUT, host->sensore) e 2 (IN, risposte).

Protocollo, come ricostruito finora:
    richiesta   "EGIS" + cmd + p1 + p2 + p3
    risposta    "SIGE" + reg + val + status
Comandi noti: 0x60 read reg, 0x61 write reg, 0x62 burst read, 0x63 burst write,
0x64 get image.

Uso:
    ./parse-usbmon.py usbmon.log            # traccia leggibile
    ./parse-usbmon.py usbmon.log --seq      # solo la sequenza di scritture,
                                            # pronta da incollare in capture2.py
"""

import re
import sys

DEV = "005"
CMD_NAMES = {
    0x60: "rd_reg",
    0x61: "wr_reg",
    0x62: "burst_rd",
    0x63: "burst_wr",
    0x64: "get_image",
}

LINE = re.compile(
    r"^\S+\s+(\d+)\s+([SCE])\s+(\w+):(\d+):(\d+):(\d+)\s+(-?\d+)\s+(\d+)(.*)$"
)


def parse(path):
    """Restituisce (ts, evento, direzione, endpoint, byte) per ogni URB con dati."""
    out = []
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = LINE.match(line)
            if not m:
                continue
            ts, ev, typ, bus, dev, ep, status, ln, rest = m.groups()
            if dev != DEV:
                continue
            if "=" not in rest:
                continue
            words = rest.split("=", 1)[1].split()
            data = bytes.fromhex("".join(words))
            out.append((int(ts), ev, typ, int(ep), int(ln), data))
    return out


def describe(data):
    """Interpretazione di un pacchetto, se riconosciuto."""
    if len(data) >= 5 and data[:4] == b"EGIS":
        cmd = data[4]
        args = " ".join(f"{b:02x}" for b in data[5:8])
        name = CMD_NAMES.get(cmd, f"cmd_{cmd:02x}")
        if cmd in (0x60, 0x61) and len(data) >= 7:
            reg, val = data[5], data[6]
            extra = f"reg={reg:#04x} val={val:#04x}"
        else:
            extra = f"args={args}"
        return f"-> {name:9s} {extra}"
    if len(data) >= 4 and data[:4] == b"SIGE":
        body = " ".join(f"{b:02x}" for b in data[4:8])
        return f"<- SIGE      {body}"
    return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "usbmon.log"
    only_seq = "--seq" in sys.argv
    pkts = parse(path)
    if not pkts:
        print(f"nessun pacchetto per il device {DEV} in {path}", file=sys.stderr)
        return 1

    t0 = pkts[0][0]
    writes = []
    for ts, ev, typ, ep, ln, data in pkts:
        d = describe(data)
        if d and d.startswith("-> wr_reg"):
            writes.append((data[5], data[6]))
        if only_seq:
            continue
        head = f"{(ts - t0) / 1000:9.2f}ms {ev} ep{ep} len={ln:5d}"
        if d:
            print(f"{head}  {d}")
        else:
            hexd = " ".join(f"{b:02x}" for b in data[:16])
            print(f"{head}  {hexd}")

    if only_seq:
        print("SEQUENCE = [")
        for reg, val in writes:
            print(f"    ({reg:#04x}, {val:#04x}),")
        print("]")
    else:
        print(f"\n{len(pkts)} pacchetti, {len(writes)} scritture di registro")
    return 0


if __name__ == "__main__":
    sys.exit(main())
