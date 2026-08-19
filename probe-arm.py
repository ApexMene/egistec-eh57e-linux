#!/usr/bin/env python3
"""Due ipotesi nate dal confronto con il driver libfprint egis0570.

A) Quanto manda davvero il sensore dopo una richiesta d'immagine?
   Il driver del fratello 0570 restituisce 32512 byte per richiesta, cioe'
   cinque frame in blocco, non uno. Se anche il nostro fa cosi' e noi ne
   leggiamo 5320, stiamo guardando una fetta disallineata di un buffer piu'
   grande — che ha esattamente l'aspetto di rumore senza fixed-pattern.

B) L'ordine di arming e' giusto?
   In egis0570 la sequenza e': scrivi reg, riscrivi lo stesso reg con il bit
   0x20 acceso, POI chiedi l'immagine. Il nostro get_frame scrive 0x2d=0x13,
   chiede l'immagine, e solo dopo scrive 0x2d=0x20. Se 0x20 e' il "vai",
   stiamo acquisendo prima di far partire la scansione.

Criterio, come sempre: correlazione fra frame consecutivi a sensore libero.
Se l'array viene davvero scandito compare il fixed-pattern noise e la
correlazione sale ben oltre lo 0.02-0.05 della baseline.
"""

import importlib.util
import statistics
import time

import usb.core
import usb.util

spec = importlib.util.spec_from_file_location("c2", "capture2.py")
c2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c2)


def apri(tent=8):
    """open_dev fa un reset USB: dopo il reset il device sparisce per qualche
    decimo di secondo e riappare. Si riprova invece di morire."""
    ultimo = None
    for _ in range(tent):
        try:
            return c2.open_dev()
        except (usb.core.USBError, SystemExit, AttributeError) as e:
            ultimo = e
            time.sleep(1.2)
    raise RuntimeError(f"sensore non riapribile: {ultimo}")


def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    den = (sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) ** 0.5
    return num / den if den else 0.0


def read_all(dev, budget=131072, quiet_ms=400):
    """Legge finche' il sensore smette di parlare, senza fermarsi a WIRE."""
    buf = bytearray()
    last = time.time()
    while len(buf) < budget and (time.time() - last) * 1000 < quiet_ms:
        try:
            chunk = dev.read(c2.EP_IN, 16384, timeout=200)
        except usb.core.USBError:
            continue
        if chunk:
            buf.extend(chunk)
            last = time.time()
    return bytes(buf)


def esperimento_a():
    """Ogni misura su un device appena riaperto: chiedere piu' byte di quanti
    il firmware si aspetti lascia la pipe in stato inconsistente, e da li' in
    poi anche le scritture vanno in timeout."""
    print("=== A) quanti byte manda davvero il sensore ===", flush=True)
    for n in (c2.WIRE, 11970, 32512, 65535):
        dev = apri()
        try:
            c2.init(dev)
            c2.drain(dev)
            c2.wr(dev, 0x2C, 0x00)
            c2.wr(dev, 0x2D, 0x13)
            dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(n)), timeout=1000)
            data = read_all(dev)
            nz = sum(1 for b in data if b)
            print(f"  richiesti {n:6d} -> ricevuti {len(data):6d} byte "
                  f"({nz} non nulli, {len(data)/c2.WIRE:.2f}x WIRE)", flush=True)
        except usb.core.USBError as e:
            print(f"  richiesti {n:6d} -> errore: {e}", flush=True)
        finally:
            try:
                usb.util.release_interface(dev, 0)
            except Exception:
                pass


def variante(dev, nome, arma):
    """arma(dev) deve lasciare il sensore pronto; poi si chiede l'immagine."""
    frames = []
    for _ in range(4):
        c2.wr(dev, 0x2C, 0x00)
        arma(dev)
        dev.write(c2.EP_OUT, bytes.fromhex(c2.img_req(c2.WIRE)), timeout=1000)
        data = read_all(dev, budget=c2.WIRE * 8, quiet_ms=250)
        if len(data) < c2.WIRE:
            print(f"  {nome:38s} frame corto ({len(data)})", flush=True)
            return
        frames.append(list(c2.depad(data[:c2.WIRE])))
        c2.wr(dev, 0x2D, 0x20)
        c2.drain(dev)
    cs = [corr(frames[i], frames[i + 1]) for i in range(len(frames) - 1)]
    c = statistics.mean(cs)
    f0 = frames[0]
    mark = "   <<< FIXED PATTERN" if c > 0.30 else ""
    print(f"  {nome:38s} corr={c:+.3f} media={statistics.mean(f0):6.1f} "
          f"sd={statistics.pstdev(f0):5.2f} liv={len(set(f0)):3d}{mark}",
          flush=True)


def esperimento_b():
    print("\n=== B) ordine di arming ===", flush=True)
    varianti = [
        ("attuale: 0x2d=13, img",
         lambda d: c2.wr(d, 0x2D, 0x13)),
        ("stile 0570: 0x2d=13, 0x2d=33, img",
         lambda d: (c2.wr(d, 0x2D, 0x13), c2.wr(d, 0x2D, 0x33))),
        ("0x2d=13, 0x2d=20, img",
         lambda d: (c2.wr(d, 0x2D, 0x13), c2.wr(d, 0x2D, 0x20))),
        ("0x2d=0f, 0x2d=2f, img (valori 0570)",
         lambda d: (c2.wr(d, 0x2D, 0x0F), c2.wr(d, 0x2D, 0x2F))),
        ("0x02=0f, 0x02=2f, img (reg 0570)",
         lambda d: (c2.wr(d, 0x02, 0x0F), c2.wr(d, 0x02, 0x2F))),
    ]
    for nome, arma in varianti:
        dev = apri()
        try:
            c2.init(dev)
            c2.wr(dev, 0x12, 0x0A)
            c2.drain(dev)
            variante(dev, nome, arma)
        except usb.core.USBError as e:
            print(f"  {nome:38s} errore: {e}", flush=True)
        finally:
            try:
                usb.util.release_interface(dev, 0)
            except Exception:
                pass


def main():
    esperimento_a()
    esperimento_b()


if __name__ == "__main__":
    main()
