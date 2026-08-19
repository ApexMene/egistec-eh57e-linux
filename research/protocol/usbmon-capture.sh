#!/usr/bin/env bash
# Cattura il traffico USB del bus 3 mentre il sensore e' passato alla VM Windows.
#
# Il driver Egis gira dentro la VM, ma il device resta fisicamente sull'host:
# qemu-usb-host inoltra ogni URB, quindi usbmon sull'host vede tutto senza dover
# installare USBPcap dentro Windows.
#
# usbmon in formato testo tronca i dati a 32 byte per URB: basta, i comandi EGIS
# sono di 8 byte. I frame immagine si vedono troncati e non servono.
#
# Uso: ./usbmon-capture.sh <file-output>   (Ctrl-C per fermare)
set -euo pipefail

OUT="${1:-usbmon.log}"
BUS=3

if [[ ! -e /dev/bus/usb/00${BUS}/005 ]]; then
    echo "attenzione: bus ${BUS} dev 005 non presente, controlla lsusb" >&2
fi

echo "cattura bus ${BUS} -> ${OUT}   (Ctrl-C per fermare)"
pkexec bash -c "cat /sys/kernel/debug/usb/usbmon/${BUS}u > '${OUT}'; chown $(id -u):$(id -g) '${OUT}'"
