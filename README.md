# EgisTec EH57E (`1c7a:057e`) — reverse engineering per Linux

Note e strumenti per far funzionare il sensore di impronte **EgisTec EH57E**
(USB `1c7a:057e`) su Linux. Il sensore monta il tasto di accensione dei Samsung
Galaxy Book ed è privo di supporto upstream: su
[linux-hardware.org](https://linux-hardware.org) risultava **0 successi su 118
macchine**.

Questo repo documenta come si è arrivati a farci parlare, e cosa manca ancora.

> **Stato:** il sensore risponde ai comandi, i registri si leggono e si scrivono,
> l'init viene accettato e il buffer immagine si scarica. **L'immagine non reagisce
> ancora al dito**: manca la sequenza di esposizione specifica per questo PID.
> Non è ancora un unlock funzionante.

## Il punto chiave

Il device appartiene alla famiglia **ET5XX** (progetto interno Egis `ETU813`), non
alla famiglia gestita dai driver libfprint esistenti.

| | `egis0570` / `egismoc` | **ET5XX (questo device)** |
|---|---|---|
| CmdID | `0x00` read, `0x01` write | `0x60`–`0x64` |
| Esito | il firmware **echeggia** i byte | comandi eseguiti |

Un singolo byte di differenza. Con `0x01` il firmware valida solo il prefisso
`EGIS` e rimanda indietro i parametri, il che produce falsi positivi molto
convincenti — una sequenza di init può risultare "24/24 OK" senza che il device
abbia eseguito nulla. Vedi `probe6-echo-test.py`, che è il test che lo smaschera.

## Protocollo

```
Richiesta:  "EGIS" (45 47 49 53) + CmdID (1B) + Param1 (1B) + Param2 (1B)
Risposta:   "SIGE" (53 49 47 45) + registro (1B) + valore (1B) + status (1B)
```

| Cmd | Significato |
|---|---|
| `0x60` | read / execute register |
| `0x61` | write register |
| `0x62` | burst read (risposta: header + N valori) |
| `0x63` | burst write — usato nell'init |
| `0x64` | get image; Param1/Param2 = lunghezza richiesta (big endian) |

**Endpoint:** OUT `0x01`, IN bulk `0x82`, interrupt `0x83` / `0x84`.
Attenzione: non sono quelli hardcoded nei driver upstream.

**Immagine:** 70×57 = 3990 byte. Chiedendo più byte il device pad-da con `0x75` e
inserisce un marker `02 HH LL` con la lunghezza richiesta.

**Nessuna cifratura sul trasporto.** `bcrypt` compare nel driver Windows solo per
i template a riposo.

## Esempio

```
TX 45474953 60 00 00  ->  RX 53494745 00 aa 01
```

Registro `0x00` = `0xAA`: è il *polling token 0xAA* citato dalle stringhe di debug
del driver Windows. Se qui rispondesse `SIGE 00 00 01` seguendo il byte dummy,
saresti nel caso eco.

## Script

| File | Cosa fa |
|---|---|
| `probe6-echo-test.py` | distingue esecuzione reale da eco del firmware |
| `probe7-ctrl-scan.py` | scan dei vendor control request (trova il descrittore WinUSB) |
| `probe8-et5xx.py` | primo dialogo col set comandi corretto; dump registri |
| `capture-057e.py` | init + download del buffer immagine |
| `ab-test.py` | test A/B cronometrato dito / non-dito |
| `reg-sweep.py` | cerca i registri di guadagno/esposizione |
| `shoot.py` | salva i frame in PNG (senza dipendenze esterne) |
| `int-listen.py` | ascolta gli endpoint interrupt |
| `capture-usb.sh` | cattura `usbmon` con `tshark` |

Serve `pyusb`. Per l'accesso senza root, una regola udev con `TAG+="uaccess"` sul
device. Se il sensore è in autosuspend va risvegliato:

```sh
echo on | sudo tee /sys/bus/usb/devices/3-5/power/control
```

## Analisi del driver Windows

I binari Egis **non sono ridistribuiti qui**. Si ottengono dal Microsoft Update
Catalog cercando l'hardware ID `VID_1C7A&PID_057E`; il CAB è firmato Microsoft e
si estrae con `cabextract`. Contiene `EgisTouchFP057E.dll` (driver UMDF2, dove
vive il protocollo), più sensor adapter e motore di matching.

I path di build sono rimasti nel binario e identificano il sorgente:
`...\UMDFSource\ET5XX\egis_fp_get_image.c`, `egis_fp_calibration.c`,
`egis_fp_common_5XX.c`, `USBCtrl.cpp`.

Le sequenze di init **non** sono tabelle statiche nel binario: sono costruite in
codice, registro per registro. Vanno quindi catturate dal traffico USB.

## Cosa manca

L'immagine scaricata è rumore di ADC: 18 livelli su 256, varianza identica con e
senza dito (4,31 vs 4,30 su 125 frame per fase). L'AFE non è pilotato. Diversi
registri (`0x07`, `0x12`, `0x20`–`0x2b`) alzano il range dinamico fino a 255, ma
le immagini risultanti sono corruzione — scacchiere binarie, righe verticali —
non segnale.

Serve la sequenza di init/esposizione specifica del `057e`, che si ottiene
catturando con `usbmon` una sessione Windows Hello (VM + passthrough USB).

## Crediti

- [Pengu601/EgisTec-EH576](https://github.com/Pengu601/EgisTec-EH576) — reverse
  engineering del `1c7a:0576`, da cui viene il set comandi ET5XX e la struttura
  del pacchetto. Senza quel lavoro questo repo non esisterebbe.
- [Animeshz/EgisTec-EH575](https://github.com/Animeshz/EgisTec-EH575)
- [indev29/egis0570](https://github.com/indev29/egis0570)
