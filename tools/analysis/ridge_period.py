#!/usr/bin/env python3
"""Trova la lunghezza vera del frame nello stream continuo del sensore.

Scoperta di probe-arm.py: dopo la richiesta d'immagine il sensore non manda un
frame e si ferma, ma **continua a trasmettere**. Con la lettura a lunghezza
fissa (5320 byte) si ritagliavano fette a fase arbitraria: due fette
consecutive non sono allineate, la correlazione fra loro fa 0, e sembrava che
l'array non venisse scandito. Il fixed-pattern noise c'e', ma va cercato al
passo giusto.

Si cattura un blocco lungo e si misura l'autocorrelazione al variare del
ritardo, via FFT (Wiener-Khinchin): in Python puro sarebbero centinaia di
milioni di moltiplicazioni, con la trasformata sono millisecondi. Il ritardo
che la massimizza e' il periodo del frame.
"""

import importlib.util
import time

import numpy as np
import usb.core
import usb.util

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)

TARGET = 400000
LAG_MIN, LAG_MAX = 256, 80000


def apri(tent=8):
    ultimo = None
    for _ in range(tent):
        try:
            return c2.open_dev()
        except Exception as e:                      # noqa: BLE001
            ultimo = e
            time.sleep(1.2)
    raise RuntimeError(f"sensore non riapribile: {ultimo}")


def cattura(arma, target=TARGET):
    dev = apri()
    try:
        c2.init(dev)
        c2.drain(dev)
        arma(dev)
        dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(c2.WIRE)), timeout=1000)
        buf = bytearray()
        last = time.time()
        while len(buf) < target and (time.time() - last) < 2.0:
            try:
                chunk = dev.read(c2.EP_IN, 16384, timeout=300)
            except usb.core.USBError:
                continue
            if chunk:
                buf.extend(chunk)
                last = time.time()
        return bytes(buf)
    finally:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:                           # noqa: BLE001
            pass


def autocorr_fft(x):
    """Autocorrelazione normalizzata, a media sottratta."""
    x = x.astype(np.float64)
    x -= x.mean()
    n = 1 << int(np.ceil(np.log2(len(x) * 2)))
    f = np.fft.rfft(x, n)
    ac = np.fft.irfft(f * np.conj(f), n)[:len(x)]
    ac = ac / np.arange(len(x), 0, -1)     # campioni sovrapposti per ritardo
    return ac / ac[0] if ac[0] else ac


def analizza(nome, d):
    print(f"\n--- {nome}: {len(d)} byte ---", flush=True)
    x = np.frombuffer(d, dtype=np.uint8)
    zeri = [int((x[r::4] == 0).sum()) for r in range(4)]
    print(f"  zeri per residuo mod 4: {zeri}", flush=True)
    print(f"  media={x.mean():.1f} sd={x.std():.2f} livelli={len(np.unique(x))}",
          flush=True)
    if len(x) < 20000:
        print("  troppo corto", flush=True)
        return None

    ac = autocorr_fft(x)
    hi = min(LAG_MAX, len(ac) - 1)
    seg = ac[LAG_MIN:hi]
    ordine = np.argsort(seg)[::-1]

    print("  picchi di autocorrelazione:", flush=True)
    visti = []
    for i in ordine:
        lag = int(i) + LAG_MIN
        if any(abs(lag - v) < 300 for v in visti):
            continue
        visti.append(lag)
        print(f"    lag={lag:6d}  corr={seg[i]:+.4f}", flush=True)
        if len(visti) >= 8:
            break
    if not visti:
        return None

    best = visti[0]
    print(f"  PERIODO = {best}  corr={ac[best]:+.4f}", flush=True)
    if best % 4 == 0:
        print(f"    {best} = 4 x {best // 4}  -> payload {best // 4 * 3} "
              f"se il trasporto e' 3 byte utili su 4", flush=True)
    for w in (57, 70, 96, 114, 128, 144, 192):
        if best % w == 0:
            print(f"    divisibile per {w}: {best}//{w} = {best // w}",
                  flush=True)
    arm = [(k, float(ac[best * k])) for k in (2, 3) if best * k < len(ac)]
    if arm:
        print("    armoniche: " +
              ", ".join(f"{k}x -> {v:+.3f}" for k, v in arm), flush=True)
    return best


def main():
    prove = [
        ("reg0x02", lambda d: (c2.wr(d, 0x02, 0x0F), c2.wr(d, 0x02, 0x2F))),
        ("reg0x2d", lambda d: (c2.wr(d, 0x2D, 0x13), c2.wr(d, 0x2D, 0x20))),
        ("reg0x2d_33", lambda d: (c2.wr(d, 0x2D, 0x13), c2.wr(d, 0x2D, 0x33))),
    ]
    for nome, arma in prove:
        try:
            d = cattura(arma)
        except Exception as e:                      # noqa: BLE001
            print(f"\n--- {nome}: errore {e}", flush=True)
            continue
        if d:
            open(f"stream-{nome}.bin", "wb").write(d)
            analizza(nome, d)


if __name__ == "__main__":
    main()
