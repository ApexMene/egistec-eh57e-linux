#!/usr/bin/env python3
"""Qual e' il punto di lavoro che NON butta via meta' immagine?

Il guadagno era stato fissato a 0x0a perche' a 0x00 il dito non si vedeva, e li'
ci si era fermati. Misurando dopo, con quel valore fra il 25% e il 75% dei pixel
finisce tagliato a 0 o a 255: informazione distrutta all'acquisizione, che nessun
confronto puo' recuperare. Quel che sopravvive e' dominato da dove il dito preme,
cioe' dalla componente che tutte le dita hanno in comune.

Qui si spazzola guadagno e offset con il dito fermo, e per ciascuno si misura
quanto si taglia e quanta energia resta nella banda delle creste rispetto al
rumore. Il punto giusto e' quello che massimizza il rapporto tenendo la
saturazione bassa: piu' contrasto non serve a niente se arriva tagliando.
"""
import importlib.util, os, sys
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
spec = importlib.util.spec_from_file_location("egis", f"{RADICE}/lib/egis_usb.py")
egis = importlib.util.module_from_spec(spec); spec.loader.exec_module(egis)

W, H = 70, 57
fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
rad = np.sqrt(fy ** 2 + fx ** 2)
BANDA = (rad > 0.08) & (rad < 0.18)
RUMORE = rad > 0.30


def frame(dev):
    egis.cmd(dev, "45474953632c020013")
    b = egis.cmd(dev, egis.img_req(), read_len=egis.FRAME, timeout=2000)
    if len(b) < W * H:
        return None
    return np.frombuffer(b[:W * H], dtype=np.uint8).reshape(H, W).astype(np.float64)


def qualita(img):
    sat = 100.0 * float(((img <= 1) | (img >= 254)).mean())
    F = np.abs(np.fft.fft2(img - img.mean())) ** 2
    snr = 10 * np.log10(F[BANDA].mean() / max(F[RUMORE].mean(), 1e-9))
    return sat, snr


def ha_creste(img, soglia_db=10.0):
    """Il dito c'e' se c'e' energia alla frequenza delle creste.

    Criterio autosufficiente: non serve un fondo di riferimento, e quindi non
    puo' essere ingannato da un fondo imparato per sbaglio con il dito gia'
    appoggiato -- che e' esattamente come le prime due spazzolate hanno finito
    per misurare il sensore libero credendo di misurare un dito.
    """
    F = np.abs(np.fft.fft2(img - img.mean())) ** 2
    return 10 * np.log10(F[BANDA].mean() / max(F[RUMORE].mean(), 1e-9)) > soglia_db


def main():
    import time
    dev = egis.open_dev(); egis.init(dev)
    egis.wr(dev, egis.REG_GAIN, 0x0a); egis.wr(dev, egis.REG_OFFSET, 0x20)
    egis.drain(dev)

    print("appoggia il dito quando vuoi, aspetto di vedere le creste...")
    fine_attesa = time.time() + 90
    visto = False
    while time.time() < fine_attesa:
        img = frame(dev)
        if img is not None and ha_creste(img):
            visto = True
            break
        time.sleep(0.05)
    if not visto:
        print("creste mai viste in 90 secondi, misura annullata")
        return 1
    print("creste viste, misuro -- NON staccare\n")

    print(f"{'gain':>5s} {'offset':>7s} {'satura%':>8s} {'SNR dB':>8s} {'media':>7s}")
    righe = []
    for offset in (0x20,):
        for gain in range(0x00, 0x10):
            egis.wr(dev, egis.REG_GAIN, gain)
            egis.wr(dev, egis.REG_OFFSET, offset)
            egis.drain(dev)
            img = None
            for _ in range(3):
                img = frame(dev)
            if img is None:
                continue
            # Se il dito e' stato tolto a meta' spazzolata i numeri che seguono
            # sarebbero del sensore libero, e sembrerebbero ottimi.
            if not ha_creste(img, 8.0):
                print(f"{gain:#5x} {offset:#7x}   -- creste assenti, saltato")
                continue
            sat, snr = qualita(img)
            righe.append((snr, sat, gain, offset))
            print(f"{gain:#5x} {offset:#7x} {sat:8.1f} {snr:8.1f} {img.mean():7.1f}")

    buoni = [r for r in righe if r[1] < 5.0]
    if buoni:
        snr, sat, g, o = max(buoni)
        print(f"\nmigliore con saturazione sotto il 5%: gain {g:#04x} offset {o:#04x} "
              f"-> SNR {snr:.1f} dB, satura {sat:.1f}%")
    print(f"attuale nel driver: gain 0x0a offset 0x20")
    egis.wr(dev, egis.REG_GAIN, 0x0a); egis.wr(dev, egis.REG_OFFSET, 0x20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
