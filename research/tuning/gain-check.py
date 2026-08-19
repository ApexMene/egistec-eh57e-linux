#!/usr/bin/env python3
"""Il guadagno giusto separa il tuo indice dal tuo medio?

Prova piu' corta che risponde: due appoggi di indice e uno di medio, allo stesso
punto di lavoro. Se il medio resta ben sotto l'indice, la saturazione era la
causa del falso accesso del 19/08; se no, il problema e' altrove e va cercato
altrove.

Tre appoggi non misurano un tasso di errore. Misurano se vale la pena rifare
tutto l'insieme al nuovo punto di lavoro.
"""
import importlib.util, os, sys, time
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
spec = importlib.util.spec_from_file_location("egis", f"{RADICE}/lib/egis_usb.py")
egis = importlib.util.module_from_spec(spec); spec.loader.exec_module(egis)

W, H = 70, 57
GAIN = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x01
fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
rad = np.sqrt(fy**2 + fx**2)
BANDA = (rad > 0.08) & (rad < 0.18); RUMORE = rad > 0.30
PASSA = np.exp(-((rad - 0.125)**2) / (2 * 0.045**2))


def frame(dev):
    egis.cmd(dev, "45474953632c020013")
    b = egis.cmd(dev, egis.img_req(), read_len=egis.FRAME, timeout=2000)
    if len(b) < W*H: return None
    return np.frombuffer(b[:W*H], dtype=np.uint8).reshape(H, W).astype(np.float64)


def snr(img):
    F = np.abs(np.fft.fft2(img - img.mean()))**2
    return 10*np.log10(F[BANDA].mean() / max(F[RUMORE].mean(), 1e-9))


def modello(p):
    p = np.fft.ifft2(np.fft.fft2(p - p.mean()) * PASSA).real
    s = p.std()
    return p/s if s > 1e-6 else p


def raccogli(dev, etichetta, n=40):
    print(f"  [{etichetta}] appoggia e tieni fermo...", flush=True)
    fine = time.time() + 90
    while time.time() < fine:
        img = frame(dev)
        if img is not None and snr(img) > 10: break
        time.sleep(0.05)
    else:
        sys.exit("dito mai visto")
    acc, sat = [], []
    while len(acc) < n:
        img = frame(dev)
        if img is not None and snr(img) > 8:
            acc.append(img); sat.append(100*float(((img<=1)|(img>=254)).mean()))
    m = np.mean(acc, axis=0)
    print(f"     satura {np.mean(sat):.1f}%   SNR {snr(m):.1f} dB", flush=True)
    print(f"     STACCA il dito", flush=True)
    fine = time.time() + 30
    while time.time() < fine:
        img = frame(dev)
        if img is not None and snr(img) < 6: break
        time.sleep(0.05)
    return modello(m)


def somiglianza(a, b, r=8):
    best = -1
    for dy in range(-r, r+1):
        for dx in range(-r, r+1):
            A = a[max(0,dy):H+min(0,dy), max(0,dx):W+min(0,dx)]
            B = b[max(0,-dy):H+min(0,-dy), max(0,-dx):W+min(0,-dx)]
            if A.size < 1500: continue
            A = A-A.mean(); B = B-B.mean()
            d = A.std()*B.std()
            if d > 1e-6: best = max(best, float((A*B).mean()/d))
    return best


def main():
    dev = egis.open_dev(); egis.init(dev)
    egis.wr(dev, egis.REG_GAIN, GAIN); egis.wr(dev, egis.REG_OFFSET, 0x20)
    egis.drain(dev)
    print(f"punto di lavoro: guadagno {GAIN:#04x}, offset 0x20\n")

    i1 = raccogli(dev, "INDICE destro, 1")
    i2 = raccogli(dev, "INDICE destro, 2")
    md = raccogli(dev, "MEDIO destro")

    gen = somiglianza(i1, i2)
    imp = max(somiglianza(md, i1), somiglianza(md, i2))
    print(f"\nindice contro indice (genuino):  {gen:.3f}")
    print(f"medio  contro indice (impostore): {imp:.3f}")
    print(f"margine: {gen-imp:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
