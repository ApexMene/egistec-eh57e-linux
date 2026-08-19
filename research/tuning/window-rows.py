#!/usr/bin/env python3
"""Le 19 righe costanti sono morte, o solo spente?

Il blocco che arriva sul filo e' 5320 byte, che e' esattamente 70 x 76. Di
quelle 76 righe ne uso 57: le ultime 19 sono costanti a 117 e finora le ho
trattate come coda di riempimento.

Nell'init pero' ci sono quattro scritture che sembrano definire una finestra di
lettura, e i numeri combaciano troppo bene per essere un caso:

    reg 0x20 = 0x00    reg 0x21 = 0x45 (69)   -> colonne 0..69  = 70
    reg 0x23 = 0x00    reg 0x24 = 0x38 (56)   -> righe   0..56  = 57

Se e' cosi', quelle 19 righe non sono riempimento ma silicio che non sto
accendendo, e portare 0x24 a 0x4b (75) darebbe 76 righe: da 15.6 a 20.8 mm2,
un terzo di area in piu'. L'area e' l'unica leva che ha sempre funzionato in
questo progetto, quindi vale la pena chiederlo al sensore invece di dedurlo.

Il criterio e' la deviazione standard per riga: una riga spenta e' piatta, una
riga attiva contiene rumore anche a sensore libero.
"""

import importlib.util
import os
import sys

import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))

spec = importlib.util.spec_from_file_location("egis", f"{RADICE}/lib/egis_usb.py")
egis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(egis)

W, ALTEZZA_BLOCCO = 70, 76
BLOCCO = W * ALTEZZA_BLOCCO      # 5320, il blocco intero sul filo
REG_RIGA_FINE = 0x24


def righe_vive(blocco):
    """Deviazione standard di ogni riga del blocco intero, non solo delle 57."""
    a = np.frombuffer(blocco, dtype=np.uint8)
    n = len(a) // W
    return a[:n * W].reshape(n, W).astype(np.float64).std(axis=1)


def main():
    dev = egis.open_dev()
    egis.init(dev)
    egis.wr(dev, egis.REG_GAIN, 0x0a)
    egis.wr(dev, egis.REG_OFFSET, 0x20)

    for valore in (0x38, 0x4b, 0x4f, 0x5f):
        egis.wr(dev, REG_RIGA_FINE, valore)
        egis.drain(dev)

        # Due fotogrammi: il primo dopo un cambio di configurazione puo' essere
        # quello vecchio ancora in coda.
        for _ in range(2):
            egis.cmd(dev, "45474953632c020013")
            # egis.FRAME e' 3990, cioe' le sole righe attive. Qui serve il
            # blocco intero da 5320 = 70 x 76, altrimenti le righe che si
            # cerca di accendere non arrivano nemmeno sul filo.
            blocco = egis.cmd(dev, egis.img_req(BLOCCO),
                              read_len=BLOCCO, timeout=3000)

        sd = righe_vive(blocco)
        vive = int((sd > 1.0).sum())
        letto = egis.rd(dev, REG_RIGA_FINE)

        print(f"0x24 scritto {valore:#04x}  riletto {letto:#04x}  "
              f"righe con segnale {vive:2d}/76   "
              f"sd righe 55-60 {np.round(sd[55:61], 1)}")

    # Sempre lasciare il sensore come lo si e' trovato: il valore di fabbrica e'
    # quello su cui e' tarato tutto il resto.
    egis.wr(dev, REG_RIGA_FINE, 0x38)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
