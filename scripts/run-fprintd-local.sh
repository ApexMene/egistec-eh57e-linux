#!/bin/bash
# Ferma il fprintd di sistema e mette al suo posto il nostro, quello che carica
# la libfprint costruita in casa.
#
# I due non possono convivere: net.reactivated.Fprint e' un nome solo sul bus di
# sistema, e chi arriva secondo resta senza. Il servizio di sistema si accende da
# solo appena qualcuno chiede il servizio, quindi va fermato adesso e il nostro
# va lanciato subito dopo, prima che qualcuno lo risvegli.
#
# Niente disable: si ferma e basta, cosi' chiudendo questo processo la macchina
# torna com'era senza altri interventi.

set -e

LIB=/home/gianlucameneghetti/projects/fingerprint/libfprint-src/build/libfprint

systemctl stop fprintd.service || true

# E anche una nostra copia rimasta in giro da un giro precedente: gira da root,
# quindi dall'utente non si riesce a chiuderla.
pkill -x fprintd || true

# Aspetta che il nome sia davvero libero: systemctl torna prima che il processo
# sia sparito, e la corsa si perderebbe di nuovo.
for i in $(seq 1 20); do
  pgrep -x fprintd >/dev/null || break
  sleep 0.2
done

echo "=== fprintd di sistema fermo, parte il nostro ==="

# -t toglie l'uscita automatica: senza, fprintd prende il nome sul bus e muore
# dopo mezzo minuto di silenzio, e il nome torna al servizio di sistema.
#
# Non "all": la macchina a stati stampa quattro righe per fotogramma a novanta
# fotogrammi al secondo, due megabyte di log al minuto in cui le righe che
# contano non si trovano piu'. Servono solo il dominio del driver e quello del
# dispositivo.
exec env LD_LIBRARY_PATH="$LIB" \
     G_MESSAGES_DEBUG="libfprint-egis057e libfprint-device fprintd" \
     /usr/libexec/fprintd -t
