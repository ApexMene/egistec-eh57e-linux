#!/usr/bin/env python3
"""Quali CmdID esistono davvero, oltre ai cinque che usa l'init?

Di questa famiglia si conoscono 0x60 (leggi registro), 0x61 (scrivi), 0x62 e
0x63 (burst) e 0x64 (immagine), perche' sono quelli che compaiono nella sequenza
di inizializzazione catturata. Nessuno ha mai chiesto al sensore cosa altro
accetta: si e' costruito tutto sopra l'ipotesi che sia solo una telecamera.

L'ipotesi merita di essere verificata, perche' se esistesse un comando di
confronto sul chip - come nella famiglia Match-on-Chip di Egis - allora tutto
il lavoro sul confronto per correlazione sarebbe la strada sbagliata: il
firmware del produttore fa quel mestiere meglio di qualsiasi cosa si possa
scrivere da fuori, ed e' probabilmente il motivo per cui su Windows lo stesso
sensore non sbaglia.

I comandi MoC erano gia' stati provati e ignorati, ma con il formato di pacchetto
sbagliato: 21 byte in stile egismoc, non "EGIS" + CmdID. Qui si usa il formato
che questo firmware capisce.

Criterio: un comando accettato risponde "SIGE"; uno rifiutato non risponde o
risponde qualcosa d'altro. La lunghezza della risposta dice se restituisce dati.
"""

import importlib.util
import os
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))

spec = importlib.util.spec_from_file_location("egis", f"{RADICE}/lib/egis_usb.py")
egis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(egis)

NOTI = {0x60: "leggi registro", 0x61: "scrivi registro", 0x62: "burst read",
        0x63: "burst write", 0x64: "richiesta immagine"}


def main():
    dev = egis.open_dev()
    egis.init(dev)

    vivi = []
    for cid in range(0x00, 0x100):
        # Argomenti a zero: si cerca l'esistenza del comando, non il suo effetto.
        try:
            r = egis.cmd(dev, f"45474953{cid:02x}0000", read_len=256, timeout=300)
        except Exception as e:
            print(f"  {cid:#04x}: eccezione {e}")
            egis.drain(dev)
            continue

        if r[:4] == b"SIGE":
            vivi.append((cid, len(r), r[4:12].hex()))

        egis.drain(dev)
        time.sleep(0.002)

    print(f"comandi che rispondono SIGE: {len(vivi)}\n")
    print("CmdID  lung.  primi byte           note")
    for cid, n, testa in vivi:
        print(f" {cid:#04x}   {n:4d}  {testa:20s} {NOTI.get(cid, '')}")

    ignoti = [c for c, _, _ in vivi if c not in NOTI]
    print(f"\nsconosciuti: {[hex(c) for c in ignoti]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
