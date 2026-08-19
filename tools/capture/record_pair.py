#!/usr/bin/env python3
"""Sei appoggi etichettati: tre di indice, tre di medio, al punto di lavoro corretto.

Serve a rispondere a una domanda sola: quanti modelli iscritti massimizzano la
separazione? Il punteggio del confronto e' il massimo su tutti i modelli, e il
massimo di N prove cresce con N anche senza segnale, quindi una galleria grande
regala occasioni anche a un dito estraneo. Sul ferro il medio ha fatto 0.303
contro due modelli e 0.734 contro trenta.

Con queste catture la prova si fa offline, variando N senza chiedere altre dita.

L'etichetta e' fissata prima e un dito alla volta: la sessione del 19/08 aveva
prodotto una conclusione sbagliata perche' cinque verifiche guidate da messaggi
in un terminale non guardato avevano scambiato un indice per un medio.

Le catture NON vanno nel repository: sono impronte digitali.
"""
import importlib.util, os, subprocess, sys, time
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
DATI = os.path.join(RADICE, "data")
spec = importlib.util.spec_from_file_location("egis", f"{RADICE}/lib/egis_usb.py")
egis = importlib.util.module_from_spec(spec); spec.loader.exec_module(egis)

W, H = 70, 57
NFRAMES = 300
fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
rad = np.sqrt(fy**2 + fx**2)
BANDA = (rad > 0.08) & (rad < 0.18); RUMORE = rad > 0.30


def finestra(testo, titolo="Cattura"):
    subprocess.Popen(["zenity", "--info", "--width=420",
                      f"--title={titolo}", f"--text={testo}"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def frame(dev):
    egis.cmd(dev, "45474953632c020013")
    b = egis.cmd(dev, egis.img_req(), read_len=egis.FRAME, timeout=2000)
    if len(b) < W * H:
        return None
    return np.frombuffer(b[:W*H], dtype=np.uint8).reshape(H, W).astype(np.float64)


def snr(img):
    F = np.abs(np.fft.fft2(img - img.mean()))**2
    return 10*np.log10(F[BANDA].mean() / max(F[RUMORE].mean(), 1e-9))


def appoggio(dev, nome, n):
    finestra(f"<b>{nome.upper()} — appoggio {n} di 3</b>\n\n"
             f"Appoggia e tieni fermo.\nTi avviso quando staccare.",
             f"{nome} {n}/3")
    print(f"[{nome} {n}/3] aspetto il dito...", flush=True)
    fine = time.time() + 120
    while time.time() < fine:
        img = frame(dev)
        if img is not None and snr(img) > 10:
            break
        time.sleep(0.05)
    else:
        sys.exit("dito mai visto")

    acc, sat = [], []
    while len(acc) < NFRAMES:
        img = frame(dev)
        if img is not None and snr(img) > 8:
            acc.append(img.astype(np.uint8))
            sat.append(100*float(((img <= 1) | (img >= 254)).mean()))

    a = np.array(acc, dtype=np.uint8)
    percorso = os.path.join(DATI, f"g01-{nome}-{n}.bin")
    a.tofile(percorso)
    print(f"    {len(acc)} fotogrammi, satura {np.mean(sat):.1f}%, "
          f"SNR {snr(a.mean(axis=0)):.1f} dB -> {os.path.basename(percorso)}",
          flush=True)

    finestra(f"<b>STACCA il dito.</b>\n\nAppoggio {n} di 3 registrato.", "Stacca")
    fine = time.time() + 60
    while time.time() < fine:
        img = frame(dev)
        if img is not None and snr(img) < 6:
            break
        time.sleep(0.05)


def main():
    os.makedirs(DATI, exist_ok=True)
    dev = egis.open_dev(); egis.init(dev)
    egis.wr(dev, egis.REG_GAIN, 0x01); egis.wr(dev, egis.REG_OFFSET, 0x20)
    egis.drain(dev)

    # Si puo' chiedere un dito solo: la prima sessione si e' interrotta dopo i
    # tre appoggi dell'indice, e rifare anche quelli sarebbe tempo di dito
    # sprecato. Il fondo si riusa se c'e' gia'.
    quali = sys.argv[1:] or ["indice", "medio"]
    percorso_fondo = os.path.join(DATI, "g01-fondo.bin")

    if os.path.exists(percorso_fondo):
        print("fondo gia' presente, lo riuso", flush=True)
        for nome in quali:
            for n in (1, 2, 3):
                appoggio(dev, nome, n)
        finestra("<b>Finito, puoi togliere il dito.</b>", "Finito")
        print(f"\nfatto: {3*len(quali)} appoggi in data/g01-*.bin")
        return 0

    print("fondo -- non toccare...", flush=True)
    finestra("<b>Non toccare per qualche secondo.</b>\n\nSto registrando il fondo.",
             "Fondo")
    time.sleep(3)
    acc = [f for f in (frame(dev) for _ in range(20)) if f is not None]
    np.mean(acc, axis=0).astype(np.uint8).tofile(os.path.join(DATI, "g01-fondo.bin"))
    print("fondo salvato", flush=True)

    for nome in quali:
        for n in (1, 2, 3):
            appoggio(dev, nome, n)

    finestra("<b>Finito, puoi togliere il dito.</b>\n\n"
             "Sei appoggi registrati. Il resto lo faccio senza di te.", "Finito")
    print("\nfatto: 6 appoggi + fondo in data/g01-*.bin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
