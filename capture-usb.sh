#!/usr/bin/env bash
# Cattura il traffico USB del sensore mentre Windows (in VM) lo pilota.
#
# Uso:
#   ./capture-usb.sh enroll     # durante l'enrollment in Windows Hello
#   ./capture-usb.sh verify     # durante uno sblocco
#   ./capture-usb.sh init       # solo avvio/rilevamento del device
#
# Il sensore sta sul bus 3 (verifica con: lsusb | grep 1c7a).
# I .pcapng finiscono in traces/ e si aprono con Wireshark.

set -euo pipefail

BUS=3
LABEL="${1:-capture}"
OUTDIR="$(dirname "$0")/traces"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$OUTDIR/${LABEL}-${STAMP}.pcapng"

mkdir -p "$OUTDIR"

if ! lsusb | grep -q "1c7a:057e"; then
  echo "ATTENZIONE: sensore 1c7a:057e non visibile su questo host."
  echo "Se è già in passthrough alla VM è normale — la cattura usbmon funziona comunque."
fi

echo "Cattura su usbmon$BUS -> $OUT"
echo "Fai ORA l'operazione in Windows. Ctrl-C per fermare."
echo

pkexec tshark -i "usbmon$BUS" -w "$OUT"

echo
echo "Salvato: $OUT"
echo "Analisi rapida:"
echo "  tshark -r '$OUT' -Y 'usb.device_address==<addr>' -x | less"
