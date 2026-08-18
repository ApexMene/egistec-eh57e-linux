#!/usr/bin/env python3
"""Ascolta gli endpoint interrupt (0x83, 0x84) dopo l'init.

Le stringhe di debug di EgisTouchFP057E.dll descrivono il flusso come
  get_image send EGIS_WAIT_INTERRUPT
  get_image receive EGIS_WAIT_INTERRUPT
  get_image receive EGIS_TZ_STATE_NOTIFY_FINGER_DOWN
quindi l'acquisizione e' guidata da un interrupt, non da polling sul bulk.
Qui verifichiamo se il sensore emette qualcosa quando il dito tocca.
"""

import importlib.util
import time

import usb.core

spec = importlib.util.spec_from_file_location("cap", "capture-057e.py")
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

EPS = [0x83, 0x84]
DURATION = 20.0

# comandi plausibili per armare l'attesa interrupt, provati in sequenza
ARM = [
    ("read 0x0f  (INT status)", "45474953600f00"),
    ("write 0x2c = 00 57", "45474953632c020057"),
    ("read 0x2d", "45474953602d00"),
    ("burst read 0x67 x3", "45474953626703"),
]


def main():
    dev = cap.open_dev()
    ok, tot = cap.init(dev)
    print(f"init: {ok}/{tot}")

    for label, c in ARM:
        r = cap.cmd(dev, c)
        print(f"  {label:26s} -> {r[:12].hex(' ')}")

    print(f"\nAscolto {EPS} per {DURATION:.0f}s. Tocca e togli il dito piu' volte.\n")
    events = []
    t0 = time.time()
    while time.time() - t0 < DURATION:
        for ep in EPS:
            try:
                data = dev.read(ep, 64, timeout=100).tobytes()
            except usb.core.USBError:
                continue
            if data:
                dt = time.time() - t0
                events.append((dt, ep, data))
                print(f"  [{dt:5.2f}s] EP {ep:#04x}: {data.hex(' ')}")

    print(f"\n--- {len(events)} eventi interrupt ---")
    if not events:
        print("  Nessun interrupt: gli endpoint restano muti anche al tocco.")
        print("  L'acquisizione va quindi armata diversamente, oppure il rilevamento")
        print("  dito e' interamente software (come sul 0576).")

    cap.usb.util.release_interface(dev, 0)


if __name__ == "__main__":
    main()
