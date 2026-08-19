#!/bin/bash
#
# Rende permanente il driver: fprintd riparte da solo al riavvio e trova la
# nostra libfprint invece di quella di sistema.
#
# Niente sovrascritture. La libreria di distribuzione resta dov'e' e com'e': la
# nostra va in /usr/local/lib/egis057e/ e un drop-in di systemd dice a fprintd
# dove cercarla. Cosi' un aggiornamento di sistema non cancella niente e
# smontare tutto vuol dire togliere due cose.
#
# /usr/local/ e non /home/ perche' SELinux e' in Enforcing: un servizio
# confinato che carica una libreria da una home utente produce negazioni. In
# /usr/local/lib l'etichetta giusta esiste, e restorecon la applica.
#
# Per tornare indietro:
#   sudo rm -rf /usr/local/lib/egis057e
#   sudo rm /etc/systemd/system/fprintd.service.d/egis057e.conf
#   sudo systemctl daemon-reload && sudo systemctl restart fprintd

set -euo pipefail

SORGENTE=${SORGENTE:-$(cd "$(dirname "$0")/.." && pwd)/libfprint-src/build/libfprint}
DEST=/usr/local/lib/egis057e
DROPIN=/etc/systemd/system/fprintd.service.d
STAMPO=$(date +%Y%m%d-%H%M%S)

echo "== fermo fprintd =="
systemctl stop fprintd.service 2>/dev/null || true
pkill -x fprintd 2>/dev/null || true

echo "== copio la libreria in $DEST =="
install -d -m 0755 "$DEST"
if [ -e "$DEST/libfprint-2.so.2.0.0" ]; then
  cp -a "$DEST/libfprint-2.so.2.0.0" "$DEST/libfprint-2.so.2.0.0.bak.$STAMPO"
  echo "   copia precedente salvata come .bak.$STAMPO"
fi
install -m 0755 "$SORGENTE/libfprint-2.so.2.0.0" "$DEST/"
ln -sf libfprint-2.so.2.0.0 "$DEST/libfprint-2.so.2"
ln -sf libfprint-2.so.2     "$DEST/libfprint-2.so"

echo "== etichette SELinux =="
if command -v restorecon >/dev/null; then
  restorecon -RF "$DEST"
  ls -Z "$DEST/libfprint-2.so.2.0.0"
fi

echo "== drop-in per fprintd.service =="
install -d -m 0755 "$DROPIN"
cat > "$DROPIN/egis057e.conf" <<'CONF'
# Driver egis057e per EgisTec EH57E (1c7a:057e).
#
# fprintd carica la libfprint costruita in casa, che contiene il driver: quella
# della distribuzione non conosce questo sensore. La libreria sta a parte, in
# /usr/local/lib/egis057e, quindi la copia di sistema resta intatta e questo
# file e' l'unica cosa che le da' la precedenza.
#
# Toglilo e riavvia il servizio per tornare al comportamento originale.
[Service]
Environment=LD_LIBRARY_PATH=/usr/local/lib/egis057e
CONF

systemctl daemon-reload

echo "== riavvio fprintd =="
systemctl start fprintd.service

sleep 2
systemctl --no-pager --lines=0 status fprintd.service | head -5 || true

echo
echo "== il servizio vede il sensore? =="
if systemctl is-active --quiet fprintd.service; then
  echo "fprintd attivo"
else
  echo "fprintd NON attivo -- controlla journalctl -u fprintd"
fi
