# Changelog — Fingerprint EgisTec EH57E (1c7a:057e)

Formato: data · cosa provato · esito (✅ funziona / ❌ non funziona / ⏳ da testare)

---

## Timeline sessione 2026-08-18 (sera)

| Ora | Evento | Esito |
|---|---|---|
| ~21:20 | Identificazione hardware (`lsusb`, DMI) | ✅ EgisTec EH57E su Galaxy Book Pro |
| ~21:25 | Ricerca supporto Linux (libfprint, linux-hardware, forum) | ❌ 0 successi documentati al mondo |
| ~21:30 | Scoperta lavoro pregresso locale del 2026-05-10 | ⚠️ patch non committate, mai funzionanti |
| ~21:33 | `lsusb -v`: mappatura endpoint | ✅ OUT `0x01`, IN `0x82`, INTR `0x83`/`0x84` |
| ~21:36 | Setup ambiente (pyusb, tshark, usbmon, udev) | ✅ completato |
| ~21:38 | **probe1** — primo contatto col sensore | ✅ **risponde `SIGE`** |
| ~21:39 | **probe2** — drenaggio endpoint | ❌ risposta statica |
| ~21:40 | Intuizione famiglia: `057x` = image-based, non MoC | 💡 |
| ~21:41 | Disabilitato autosuspend USB (era `suspended`) | ✅ `active` |
| ~21:42 | **probe3** — init_pkts2, letture da INTR `0x83` | ❌ 0/24 timeout |
| ~21:42 | **probe4** — init_pkts2, letture da BULK `0x82` | ⚠️ 24/24 "OK" (falso positivo) |
| ~21:43 | **probe5** — capture col dito sul sensore | ❌ nessuna immagine |
| ~21:44 | **probe6** — test comandi invalidi | 🔬 **smascherato: è puro eco** |
| ~21:44 | **probe7** — scan control request | 🔑 **MS OS Descriptor: `WINUSB`** |
| ~21:45 | Ricerca driver Windows + GitHub code search | ❌ nulla per `057e` |
| ~21:45 | Decisione: strada VM Windows + trace USB | ▶️ |
| ~21:45 | `quickemu` installato, `quickget windows 11` | ⚠️ ISO bloccata da Microsoft (IP) |
| ~21:46 | Download `virtio-win.iso` da fedorapeople (il primo era corrotto, 4 KB) | ⏳ in corso |

---

## 2026-08-18 — Sessione ricognizione

### ✅ Fatti accertati (hardware)

| Voce | Valore |
|---|---|
| Laptop | Samsung `950XDB/951XDB/950XDY` (Galaxy Book Pro), BIOS `P14RFW` |
| Sensore | EgisTec EH57E — USB `1c7a:057e` |
| Serial | `50C768B2DC23`, bcdDevice `12.01` |
| Classe USB | `ff/ff` Vendor Specific (nessun driver standard possibile) |
| Bulk OUT | **`0x01`** |
| Bulk IN | **`0x82`** |
| Interrupt IN | `0x83` e `0x84` (16 byte, bInterval 8) |
| Bus | 003 Device 005, High Speed 480Mbps |

> **Nota chiave:** gli endpoint sono **diversi** dal driver `egismoc` upstream, che
> assume OUT `0x02` / IN `0x81`. Per 057e vanno invertiti → OUT `0x01`, IN `0x82`.
> Questa è la prima causa quasi certa dei fallimenti passati.

### ❌ Cosa NON funziona / non esiste

- ❌ **libfprint upstream** (1.94.100, installato da RPM): `057e` non presente in nessuna id-table.
- ❌ **linux-hardware.org**: 118 macchine con questo sensore, **0 successi**, su Ubuntu/Fedora/Arch/Mint/Pop!_OS.
- ❌ **Nessun driver kernel** fino a 7.1 (il tuo kernel è 7.1.8).
- ❌ **Thread Fedora Discussion** su Galaxy Book Pro: irrisolto, nessun tentativo serio documentato.
- ❌ Tentativo del **2026-05-10** (vedi sotto): `enroll-unknown-error`.

### ⚠️ Regressione scoperta

La libfprint compilata a mano il **10/05** è stata **sovrascritta da un update RPM l'11/08/2026**
(`/usr/lib64/libfprint-2.so.2.0.0` datato Aug 11). Il sistema ora gira **stock**, quindi
qualsiasi patch precedente è persa. Va ricompilata e va gestita la persistenza vs `dnf update`.

### 📦 Lavoro pregresso trovato in questo progetto (10/05/2026)

Due clone già presenti:

- `libfprint/` — clone upstream
- `libfprint-egismoc-sdcp/` — fork **TenSeventy7/libfprint-egismoc-sdcp** (driver Egis
  Match-on-Chip + protocollo SDCP), `master` allineato a origin.

Modifiche **non committate** in `libfprint-egismoc-sdcp`:

```diff
egismoc.c:
+  { .vid = 0x1c7a, .pid = 0x057e, .driver_data = EGISMOC_DRIVER_CHECK_PREFIX_TYPE1 },

egismoc.h:
-  EP_CMD_OUT 0x02 / EP_CMD_IN 0x81
+  EP_CMD_OUT 0x01 / EP_CMD_IN 0x82      ← corretto per 057e (confermato da lsusb -v)
-  timeout 5000
+  timeout 10000
```

Esito registrato in `enroll_debug.log` / `enroll_debug2.log`:

```
Enrolling right-index-finger finger.
Enroll result: enroll-unknown-error     ❌
```

**Valutazione:** l'errore NON è "device non trovato" né timeout → il driver ha *agganciato*
il device e ha tentato un dialogo. Fallisce più avanti nel protocollo. Segnale incoraggiante,
ma i log erano senza `G_MESSAGES_DEBUG=all`, quindi non si sa **dove** rompe. Da rifare con debug pieno.

### 🔍 Riferimenti utili trovati online

| Risorsa | Perché serve |
|---|---|
| [joshuagrisham/galaxy-book2-pro-linux](https://github.com/joshuagrisham/galaxy-book2-pro-linux/tree/main/fingerprint) | PoC Python per Egis MoC `1c7a:0582` su Galaxy Book2 Pro — **stesso vendor, stessa famiglia Samsung**. Base migliore. |
| [TenSeventy7/libfprint-egismoc-sdcp](https://github.com/TenSeventy7/libfprint-egismoc-sdcp) | Fork con SDCP + ID aggiunti (0582–05a5). Già clonato qui. |
| [linux-fingerprint-drivers](https://github.com/jedbillyb/linux-fingerprint-drivers) | Hub community, MR libfprint aperte per Egis. |
| [libfprint upstream](https://gitlab.freedesktop.org/libfprint/libfprint) | Destinazione finale di un'eventuale patch. |

### 🧬 Protocollo Egis MoC (da PoC Grisham) — ipotesi di lavoro per 057e

Payload bulk, struttura:

1. prefisso 8 byte — OUT `45 47 49 53 00 00 00 01` (`EGIS\x00\x00\x00\x01`), IN `SIGE\x00\x00\x00\x01`
2. 2 byte check (somma MOD `0xFFFF` su word 32-bit big-endian)
3. 3 byte hardcoded `00 00 00`
4. 2 byte type/subtype
5. payload variabile

Sensore **Match-on-Chip**: impronte memorizzate e confrontate *sul chip*, l'host non vede
mai l'immagine. Interrupt IN usato per notificare "dito appoggiato".

### 📥 Scaricato in questa sessione

- `egismoc-1c7a-0582.py` (469 righe) — PoC Python di riferimento, da adattare a `057e`.

### ✅ Setup ambiente — FATTO

Installati: `python3-pyusb`, `python3-docopt`, `wireshark-cli` (+ `libsmi`, `bcg729`).
Toolchain build (meson/ninja/gcc/glib2-devel/…) risultava **già presente**.
Caricato `usbmon`. Creata regola udev `/etc/udev/rules.d/60-egis-fingerprint.rules`
(`TAG+="uaccess"`) → il sensore è accessibile **senza root**.

Disabilitato autosuspend USB sul device (era `runtime_status: suspended`):
`echo on > /sys/bus/usb/devices/3-5/power/control` → ora `active`.
⚠️ Non persistente al reboot; se serve, va fatta una regola udev dedicata.

---

## Fase probe — risultati sperimentali

Quattro script scritti in `~/projects/fingerprint/`, tutti **non distruttivi**.

### ✅ probe-057e.py — il sensore PARLA

Prima comunicazione riuscita in assoluto con questo sensore.
Risposta al prefisso `EGIS…`: **`53 49 47 45` = `SIGE`**.

- ✅ `dev.reset()`, `set_configuration(1)`, `claim_interface(0)` funzionano
- ✅ bulk OUT `0x01` accetta le write
- ✅ bulk IN `0x82` restituisce dati
- ❌ control transfer `bReq=32` e `bReq=82` → **timeout** (su 0582 funzionano)
- ⚠️ risposta sempre lunga 7 byte

### ❌ probe2 — la risposta è statica

Drenando `0x82`/`0x83`/`0x84` dopo ogni comando: `0x82` restituisce **sempre**
`53 49 47 45 00 00 00`, all'infinito, uguale per ogni comando. Interrupt `0x83`/`0x84` muti.
→ i comandi in stile MoC (21 byte) non vengono interpretati.

### 💡 Intuizione: famiglia sbagliata

I PID `057x` (0570/0571/0575/0576/**057e**) sono sensori **image-based**;
i `0582+` sono **Match-on-Chip**. Stavo usando il protocollo dei fratelli sbagliati.

Inoltre `libfprint/` (clone locale) contiene già, **non committato**, una
`init_pkts2` marcata *"Alternative initialization sequence for 057e device"*:
era commentata in upstream, a maggio è stata scommentata e agganciata a `057e`,
insieme a EP `0x01`/`0x83`, retry, e molto debug logging. Coerente: pacchetti da **7 byte**
= esattamente la lunghezza delle risposte osservate.

### ❌ probe3 — interrupt 0x83 non risponde

Sequenza `init_pkts2` (25 pacchetti da 7 byte) su OUT `0x01`, letture da interrupt `0x83`
come fa il driver upstream: **0/24 risposte, tutti timeout**. Nessuna immagine.
→ su questo device le risposte NON arrivano dall'interrupt endpoint.

### ⚠️ probe4 — 24/24 comandi "accettati" (poi smentito)

Stessa sequenza, letture da **bulk `0x82`**: **24/24 risposte valide**, con eco strutturato:

```
TX 45 47 49 53 01 10 00   ->  RX 53 49 47 45 10 00 00
TX 45 47 49 53 01 11 38   ->  RX 53 49 47 45 11 38 00
TX 45 47 49 53 01 16 3b   ->  RX 53 49 47 45 16 3b 00
```

Sembrava conferma piena del protocollo. **Ma** dopo il pacchetto di capture
(`EGIS 06 00 fe`) non arriva l'immagine: solo ACK da 7 byte ripetuti
(32508 byte letti = `SIGE 00 fe 00` all'infinito, poi `Errno 75 Overflow`).

### ❌ probe5 — nessuna immagine nemmeno col dito sul sensore

Init completo + capture + ascolto 15 s su `0x82`/`0x83`/`0x84` con dito premuto:
`0x82` → 175 byte, **0 risposte non-ACK**. `0x83` e `0x84` → 0 byte.

### 🔬 probe6 — DIAGNOSI: è puro ECO

Test con comandi deliberatamente invalidi:

| TX | RX | Verdetto |
|---|---|---|
| `…01 aa 55` (registro inesistente) | `SIGE aa 55 00` | echeggia |
| `…01 ff ff` | `SIGE ff ff 00` | echeggia |
| `…99 99 99` (type invalido) | `SIGE 99 99 00` | echeggia |
| `00 00 00 00 01 10 00` (prefisso errato) | **timeout** | prefisso validato |
| `de ad be ef …` | **timeout** | prefisso validato |

E soprattutto — la *read* di un registro restituisce il byte **dummy** che gli passo,
non il valore scritto prima:

```
WRITE reg 0x11 = 0x38   ->  SIGE 11 38 00
READ  reg 0x11 (dummy 00)  ->  SIGE 11 00 00     ← dovrebbe dire 0x38
READ  reg 0x11 (dummy aa)  ->  SIGE 11 aa 00     ← segue il dummy
```

**Conclusione: il firmware valida solo i 4 byte `EGIS` e rimbalza il resto.
Non esegue nulla.** Il "24/24" di probe4 era un falso positivo.
→ `057e` **non implementa** il protocollo egis0570, e nemmeno egismoc.
→ Questo spiega l'`enroll-unknown-error` di maggio e i 118 fallimenti su linux-hardware.

### 🔑 probe7 — il device è WinUSB

Scan di tutti i vendor control request in lettura (`bmRequestType` `0xc0`/`0xc1`,
`bReq` 0–255, `wIndex` 0 e 4). **Un solo hit:**

```
bReq=4 (0x04) wIndex=4 len=40:
28 00 00 00 00 01 04 00 01 00 00 00 00 00 00 00
00 01 57 49 4e 55 53 42 00 00 00 00 00 00 00 00
                ^^^^^^^^^^^^^^^^^ "WINUSB"
```

È il **Microsoft OS 1.0 Compatible ID Descriptor**: il device dichiara compatibilità
**WinUSB**. Su Windows non c'è driver kernel — il sensore è pilotato in **user-space**
dal software Samsung (*CanvasBio*).

**Implicazioni (grosse):**
- tutta la logica di init/protocollo sta in una **DLL user-space**, non in un `.sys`
- il traffico è banale da catturare in VM (nessun driver kernel di mezzo)
- la DLL è analizzabile **staticamente**, anche senza far girare Windows

### 📊 Stato: cosa va / cosa non va

| Elemento | Stato |
|---|---|
| Enumerazione USB, reset, claim interface | ✅ |
| Endpoint mappati (OUT `0x01`, IN `0x82`, INTR `0x83`/`0x84`) | ✅ |
| Comunicazione bidirezionale col sensore | ✅ |
| Handshake prefisso `EGIS` → `SIGE` | ✅ |
| Autosuspend che metteva il device in sleep | ✅ risolto |
| Accesso senza root (udev) | ✅ |
| Protocollo **egismoc** (MoC, 0582+) | ❌ escluso con prova |
| Protocollo **egis0570** (image, init_pkts2) | ❌ escluso con prova |
| Esecuzione reale dei comandi | ❌ solo eco |
| Cattura immagine | ❌ mai ottenuta |
| Control transfer di init (`bReq` 32/82) | ❌ timeout |

### 🎯 Prossimo passo obbligato

L'inferenza dai driver esistenti è **esaurita**: il firmware non parla nessuno dei due
protocolli noti, quindi la sequenza di init va **osservata**, non indovinata. Due strade,
entrambe possibili senza dual boot:

1. **Analisi statica della DLL CanvasBio/Egis** (nessun Windows necessario) — scaricare il
   pacchetto driver Samsung, estrarlo, cercare nella DLL i pattern dei comandi USB.
2. **VM Windows + USB passthrough** + cattura `usbmon`/`tshark` durante un enroll reale
   in Windows Hello. Dà la verità assoluta. `/dev/kvm`, `qemu-kvm` e `virt-manager` già pronti.

La strada 1 è più veloce da tentare; la 2 è quella che chiude il caso con certezza.

---

## Fase VM Windows — avviata 2026-08-18 21:45

Scelta operativa: **strada 2** (VM Windows + trace USB reale).

### Valutazione onesta delle probabilità (fatta prima di partire)

| Passo | Probabilità |
|---|---|
| Passthrough USB + cattura trace funzionante | ~85% |
| Arrivare a uno sblocco impronta funzionante | ~50% |

Rischi noti:
- **CanvasBio potrebbe rifiutare l'installazione** in VM (DMI dice QEMU, non Samsung) → aggirabile con spoofing DMI
- **Windows Hello richiede TPM** → `tpm="on"` già nella conf di quickemu
- **Rischio grosso: cifratura.** Se il canale è protetto (stile SDCP con certificati/chiavi in hardware), vedere i byte non basta per replicarli. Non verificabile finché non si guarda il trace.

### 21:45 — quickemu installato ✅

`quickemu 4.9.9` + `edk2-tools`, `spice-gtk-tools`, `mesa-demos`.

### 21:45 — `quickget windows 11` ⚠️ parzialmente fallito

```
WARNING! Microsoft blocked the automated download request based on your IP address.
```

- ❌ **ISO Windows 11 NON scaricata** → va presa a mano dal browser
  (https://www.microsoft.com/en-us/software-download/windows11),
  poi salvata come `vm/windows-11/windows-11.iso`
- ❌ `virtio-win.iso` scaricato **corrotto** (4464 byte invece di ~700 MB)
- ✅ `unattended.iso` generato (14 MB)
- ✅ `windows-11.conf` generato: disco 64 GB, `tpm="on"`, `secureboot="off"`

### 21:46 — Rimedio virtio ⏳

Download `virtio-win.iso` da fonte ufficiale
(`fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/`) in background.
Serve a Windows setup per vedere il disco virtio durante l'installazione.

### 21:48 — virtio-win.iso ✅

789 MB scaricati da fedorapeople (fonte ufficiale). Il file corrotto è stato sostituito.

### 21:50 — ISO Windows 11 ⏳ in download

Microsoft blocca `quickget` ma non il browser. Risolto pilotando Chrome:
pagina download → edition `3321` (multi-edition x64) → lingua *English International*
→ link generato (host `software.download.prss.microsoft.com`, **valido 24h**,
scadenza `2026-08-19T19:48 UTC`).

Download in corso in `~/Downloads` (Chrome). Da spostare a fine download in
`vm/windows-11/windows-11.iso`.

### 21:52 — Preparativi completati ✅

**`capture-usb.sh`** — cattura il traffico del sensore con `tshark` su `usbmon3`,
salva `.pcapng` timestampati in `traces/`. Tre modi: `enroll`, `verify`, `init`.

**`vm/windows-11.conf`** — aggiunto:

```
ram="6G"
cpu_cores="4"
usb_devices=("1c7a:057e")   # passthrough del sensore alla VM
```

### Sequenza operativa prevista

1. Spostare l'ISO in `vm/windows-11/windows-11.iso`
2. `quickemu --vm vm/windows-11.conf` → installare Windows 11
3. Verificare in Gestione dispositivi che il sensore appaia (passthrough attivo)
4. Installare il driver Samsung/Egis (CanvasBio) nella VM
5. `./capture-usb.sh enroll` **sull'host**, poi enroll in Windows Hello nella VM
6. Analizzare il `.pcapng`: estrarre init sequence, comandi, formato risposte
7. Riscrivere il PoC Python sulla sequenza reale
8. Se funziona → portare in libfprint (fork `libfprint-egismoc-sdcp` o driver nuovo)

### Bloccante attuale

Nessuno — si attende solo il completamento del download (~5.5 GB).

---

## 2026-08-18 — Sessione notturna: la svolta

### 21:54 — Cambio di strategia: il driver Windows, senza VM

La VM serve a osservare il driver mentre lavora. Ma il driver è un file, e i file
si possono leggere direttamente.

**Microsoft Update Catalog** indicizza i driver per hardware ID. Ricerca
`VID_1C7A&PID_057E` → 22 risultati, famiglia "Egis Technology Inc. - Biometric".
Preso il più recente (3.12.3.2, 06/07/2021, GUID
`3a18ff3c-ad04-4f6b-9c54-5da9368eea7a`) risolvendo l'URL via
`POST /DownloadDialog.aspx`:

```
https://catalog.s.download.windowsupdate.com/d/msdownload/update/driver/drvs/
  2023/02/2de16ba8-b132-43e5-9949-abb72aed3f57_94e1...ca.cab
```

CAB firmato Microsoft, 738.468 byte,
sha256 `6d63197a3917b80ed0c1840e4528d746176ff89a6c730c490a6d618105a8c106`.

Contenuto (`cabextract`):

| File | Ruolo |
|---|---|
| `EgisTouchFP057E.dll` (1,19 MB) | driver UMDF2 — **contiene il protocollo USB** |
| `EgisTouchFPSensor057E.dll` (131 KB) | WBF sensor adapter (`WbioQuerySensorInterface`) |
| `EgisTouchFPEngine057E.dll` (968 KB) | motore di matching (`WbioQueryEngineInterface`) |
| `EgisTouchFP057E.inf` | `USB\VID_1C7A&PID_057E`, `Include=WINUSB.INF` |
| `egistouchfp057e.cat` | firma |

Il `.inf` conferma l'architettura: `UmdfService`, `UmdfDispatcher=WinUsb`,
`LowerFilters=WinUsb`. Driver **user-space** su WinUSB → nessun codice kernel da
replicare, tutto il protocollo passa da bulk transfer osservabili.

### 22:00 — Cosa dicono le stringhe del driver

I path di build sono rimasti nel binario:

```
C:\builds\Application.Notebook\ETU813\etu813.driver2\Main\WBF\source\UMDF\
  UMDFSource\ET5XX\egis_fp_calibration.c
  ...\ET5XX\egis_fp_common_5XX.c
  ...\ET5XX\egis_fp_get_image.c
  ...\USBCtrl.cpp
```

**Il sensore è della famiglia ET5XX, progetto ETU813.** Funzioni identificate:
`et5xx_power_on_initialize`, `fp_tz_secure_sensor_init`,
`fp_tz_secure_set_detect_mode`, `fp_tz_secure_pre_calibrate`,
`et5xx_calibrate_bad_pixel`, `calibrate_detect_mode_5_series`,
`et5xx_fetch_dynamic_intensity`, `get_image_state_handler`.

Messaggi di debug rilevanti:

```
polling token 0xAA fail
%s, poll poacf fail 0x00
get_image send EGIS_WAIT_INTERRUPT
get_image receive EGIS_TZ_STATE_NOTIFY_FINGER_DOWN
STUS_ET5XX_ADDR EGIS_COMMAND_FAIL
Getting Zone1 Image / Getting Zone2 Image
%s,Max == 0xff   /   %s,Min == 0x0
```

**Nessun canale cifrato.** `bcrypt.dll` è importata solo da `EgisTouchFP057E.dll`
e `...Engine057E.dll` per i template a riposo, non per il trasporto. Il rischio
"SDCP-like" stimato a inizio serata è escluso.

### 22:05 — L'errore che ci bloccava da maggio

Il driver contiene 30 costruzioni inline della costante `EGIS` e altrettanti
confronti con `SIGE`: il framing è quello che avevamo già osservato. Il problema
era un altro.

Ricerca incrociata → **[Pengu601/EgisTec-EH576](https://github.com/Pengu601/EgisTec-EH576)**,
reverse engineering del cugino `1c7a:0576` (stessa famiglia ET5XX). Formato:

```
Header "EGIS" (4B) + CmdID (1B) + Param1 (1B) + Param2 (1B)
```

Set comandi:

| Cmd | Significato |
|---|---|
| `0x60` | read / execute register |
| `0x61` | write register |
| `0x62` | burst read register |
| `0x63` | burst write (usato nell'init) |
| `0x64` | get image (i due parametri = lunghezza richiesta) |

**`egis0570` e `egismoc` usano CmdID `0x00` / `0x01`.** Questa famiglia usa `0x6X`.
Il firmware riceveva comandi che non esistono, e rispondeva rimandando indietro i
byte — l'eco diagnosticato in `probe6`. Sette probe e un `enroll-unknown-error`
spiegati da un singolo byte sbagliato.

### 22:08 — Primo dialogo reale (`probe8-et5xx.py`) ✅

```
TX 45474953 60 00 00  ->  RX 53494745 00 aa 01
TX 45474953 60 00 aa  ->  RX 53494745 00 aa 01     <- non segue piu' il dummy
TX 45474953 60 01 00  ->  RX 53494745 01 00 01
```

Risposta = `SIGE` + registro + valore + status. **Registro `0x00` = `0xAA`**, cioè
esattamente il *polling token 0xAA* nominato dal driver Windows: il sensore
risponde da manuale.

- Scan registri `0x00`–`0x2f`: **48/48 valori distinti e coerenti**
- Burst read (`0x62`): 39 byte = header + 32 valori
- Init completo (29 comandi, adattato da EH576): **29/29 accettati**, e i valori
  scritti restano (`0x21`→`0x45`, `0x24`→`0x38`, `0x23`→`0x00` riletti corretti)

Prima comunicazione documentata con `1c7a:057e` su Linux.

### 22:20 — Il buffer immagine

`0x64` con lunghezza richiesta restituisce esattamente quella quantità di byte.
Confronto fra frame consecutivi: **60% dei byte cambia** → lettura live, non un
buffer statico.

Struttura scoperta chiedendo 6498 byte:

```
[0 .. 3989]  dati vivi        <- 3990 byte = 70x57
[3990..6143] padding 0x75
[6144..6146] 02 19 62         <- marker, 0x1962 = 6498 = lunghezza richiesta
[6147..6497] padding 0x75
```

**Geometria reale: 70×57, 3990 byte** — la stessa dell'EH576.

### 22:35 — Il dito non si vede

Test A/B cronometrato (`ab-test.py`), 125 frame per fase:

| | varianza | media | range px | valori distinti |
|---|---|---|---|---|
| senza dito | 4.31 | 114.80 | 106–124 | 18 |
| con dito | 4.30 | 114.83 | 107–124 | 18 |

Delta varianza **−0,03**. Nessuna reazione. Range dinamico 18 livelli su 256:
l'AFE non è pilotato, stiamo leggendo rumore di ADC.

Sweep di 28 registri × 6 valori (`reg-sweep.py`): `0x07`, `0x12`, `0x20`–`0x2b`,
`0x25` alzano la varianza fino a 3268 e il range a 255. Ma le immagini salvate
(`shoot.py` → PNG) mostrano che è **corruzione, non segnale**: `0x2a=0x80` produce
una scacchiera binaria, `0x12=0xff` righe verticali regolari, base = rumore
uniforme. Solo 6–18 valori distinti a fronte di varianza altissima.

Ascolto degli endpoint interrupt `0x83`/`0x84` per 20 s con tocchi ripetuti
(`int-listen.py`): **0 eventi**. Come sul 0576, non c'è notifica hardware di
finger-down.

### 22:50 — Perché serve comunque la cattura da Windows

Ricerca delle sequenze di init dentro i binari: i payload burst
(`0b83 2400 440f 0820 2000 0052`, `0606 6006 052f 06`, `020f03`) **non esistono
come tabelle statiche** né in `EgisTouchFP0576.dll` né in `EgisTouchFP057E.dll`.
Sono costruiti in codice, registro per registro.

Conseguenza: la sequenza dell'EH576 la si ottiene solo dal traffico, ed è
esattamente così che l'ha ottenuta Pengu601. Le catture del 0576 presenti nel suo
repo sono incapsulate in TLS (`16 03 03 ...` sui pipe `0x01`/`0x82`), quindi non
riutilizzabili in chiaro.

**La nostra sequenza di init va catturata dal nostro sensore.** La VM torna ad
essere il passo successivo — ma ora con una differenza sostanziale: sappiamo già
il framing, il set comandi, la geometria e il formato delle risposte, quindi la
cattura serve solo a riempire i valori dei registri.

### 22:14 — ISO Windows 11 completata ✅

8.486.862.848 byte, spostata in `vm/windows-11/windows-11.iso`.
VM configurata e pronta: 6 GB RAM, 4 core, TPM on, secureboot off,
passthrough `1c7a:057e`.

---

## Stato: cosa va / cosa non va

| Cosa | Stato |
|---|---|
| Identificazione hardware (ET5XX / ETU813) | ✅ |
| Driver Windows ottenuto e analizzato | ✅ |
| Assenza di cifratura sul trasporto | ✅ confermata |
| Endpoint (OUT `0x01`, IN bulk `0x82`, INTR `0x83`/`0x84`) | ✅ |
| Set comandi (`0x60`–`0x64`) | ✅ |
| Lettura/scrittura registri | ✅ |
| Init 29/29 accettato, valori persistenti | ✅ |
| Download buffer immagine, geometria 70×57 | ✅ |
| **Immagine che reagisce al dito** | ❌ |
| Interrupt di finger-down | ❌ assenti |
| Sequenza di init specifica per 057e | ❌ da catturare |
| Enroll / unlock | ❌ |

## Prossimo passo

Installare Windows 11 nella VM già pronta, installare il driver Egis (che
**abbiamo già**, `vm/` + CAB estratto), fare un enroll e catturare con
`./capture-usb.sh enroll`. Dalla traccia servono solo i valori dei registri di
init e il comando di esposizione: tutto il resto del protocollo è già mappato.


---

## 2026-08-18 22:20–22:35 — La VM non serve più: il driver aveva già tutto

Ripreso dopo la pubblicazione su GitHub. Invece di installare Windows, ho
disassemblato per bene `EgisTouchFP057E.dll`. Le costanti che mancavano erano
tutte lì dentro.

### 22:20 — Le primitive del protocollo, trovate via `.pdata`

Il `.pdata` (exception directory) dà i confini esatti di 536 funzioni, quindi
si disassembla per funzione invece che con uno sweep lineare che si
disallinea. Cercando gli store di byte immediati nel range `0x60`–`0x64`
saltano fuori esattamente cinque funzioni:

| VA | Ruolo |
|---|---|
| `0x18001a3a0`, `0x18001a4e0` | read register (`0x60`) |
| `0x18001b7c0`, `0x18001b9b0` | write register (`0x61`) |
| `0x180018720` | get image (`0x64`) |

I chiamanti diretti sono solo wrapper sottili: le sequenze vere passano per
vtable, quindi cercare i call statici non porta da nessuna parte. La strada
giusta è stata partire dalle stringhe di debug.

### 22:25 — `get_image` ha due formati, e questo spiega mesi di confusione

In `0x180018720` c'è un bivio su `cmp word ptr [rbx+0x48], 3`:

- **versione ≥ 3**: `mov byte [rbx+0x4f], al` con `shr eax, 8` → lunghezza
  big-endian su due byte, cioè `EGIS 64 HH LL`
- **versione < 3**: `lea ecx,[rsi+0x1ff]` + `and ecx,0xfffffe00` (arrotonda a
  multipli di 512) e `shr eax, 9` → `EGIS 64 00 NN` con NN = numero di blocchi

Il nostro device usa il primo formato: restituisce esattamente il numero di
byte richiesto. Testata anche la forma a blocchi, dà solo spazzatura.

### 22:28 — Le dimensioni vere, dalla funzione delle zone

Le stringhe `Getting Zone1 Image, height width=(%d,%d)` e `SENSOR_WIDTH`
portano a `0x18000935c`. Lì dentro:

| Costante | Valore | Significato |
|---|---|---|
| `mov r14d, 0xf96` | 3990 | byte per frame |
| `mov ecx, 0x2ec2` | 11970 | buffer = 3990 × 3 |
| `imul eax, r8d, 0x46` | 70 | stride di riga |
| `cmp r9d, 0x39` | 57 | altezza |
| `cmp ebp, 0x7cb` | 1995 | soglia di copertura (metà immagine) |

Quindi **70×57**, e il driver preleva **tre frame consecutivi**, non uno.
Il flusso per frame è: `reg 0x2c = 0x00`, poi `reg 0x2d = 0x13`, get image,
`reg 0x2d = 0x20`. Subito dopo binarizza con
`|pixel − riferimento| > 0x20` — è il rilevamento del dito, interamente
software, e conferma che non esiste un interrupt di finger-down.

Ricostruito tutto in `capture2.py`.

### 22:31 — L'errore che teneva fermo il progetto: il padding 3-su-4

Con il flusso corretto il frame torna strutturato a **gruppi di 4 byte: 3 di
payload e 1 sempre a zero**. Verificato:

```
chiesto 3990 -> ricevuto 3990  nonzero=2993
chiesto 5320 -> ricevuto 5320  nonzero=3990   <-- esatto
```

Per avere i 3990 pixel di un 70×57 bisogna chiedere **5320 byte** (= 3990×4/3)
e scartare il byte di padding. Chiedendone 3990 se ne ottenevano 2993, cioè
tre quarti di immagine disallineata: da qui l'apparenza di puro rumore che mi
aveva portato alle conclusioni sbagliate di ieri sera.

Nota: anche la geometria "114×57 = 6498" annotata prima era sbagliata. Il
marker `02 19 62` non era una lunghezza dichiarata dal device, era solo l'eco
di quanto avevo chiesto io.

### 22:33 — Guadagno e offset dell'AFE (`afe-sweep.py`)

Sweep dei registri `0x09`–`0x13`, che l'init carica con il burst
`63 09 0b 83 24 00 44 0f 08 20 20 00 00 52` (riletti uno per uno: i valori
corrispondono, l'init si applica davvero).

| Registro | Ruolo | Effetto |
|---|---|---|
| `0x0f` | offset DC | `0x04`→media 5, `0x10`→51, `0x20`→112, `0xff`→231 |
| `0x12` | **guadagno** | `0x00`→6 livelli distinti, `0x08`→**43**, range 9–87 |

Con `0x12 = 0x08` e la lunghezza corretta il frame ha 42–43 livelli distinti e
varianza ~33: rumore di fondo uniforme, che è esattamente ciò che deve dare un
sensore capacitivo libero. Prima erano 6 livelli su un buffer affettato male.

### Stato

| Cosa | Stato |
|---|---|
| Geometria 70×57 confermata dal binario | ✅ |
| Lunghezza di trasporto 5320 + de-padding | ✅ |
| Guadagno (`0x12`) e offset (`0x0f`) dell'AFE | ✅ |
| Flusso di acquisizione a 3 frame del driver | ✅ replicato |
| Immagine di fondo pulita e a pieno range | ✅ |
| **Immagine che reagisce al dito** | ⏳ in test (`live.py`) |
| Enroll / unlock | ❌ |

La VM Windows resta pronta ma non è più il passo obbligato: le costanti che
volevo estrarre dalla cattura USB erano già nel binario.

### 22:40 — Tutte le scritture di registro del driver, e una mia correzione

Trovato l'helper `write_register(cl=registro, dl=valore)` a `0x18000d274` e
il burst a `0x18000d17c`. Enumerando i chiamanti si ottiene l'elenco completo
dei registri che il driver 057e tocca:

```
0x0a: fd fc f4 43     0x0b: 22        0x0c: 22 44     0x0f: calibrato
0x12: 0a (guadagno)   0x20: 00        0x21: 45        0x23: 00
0x24: 38              0x2c: 00        0x2d: 13 20     0x35: 02
0x40: 00              0x50: 44        0x54: 00        0x80: 00
burst: 0x0d 0x11 0x26 0x34 0x67
```

**Correzione a quanto scritto sopra alle 22:35**: la mia prima estrazione
automatica appaiava male gli immediati e mi aveva fatto scrivere che
`reg 0x35 = 0xfd` e `reg 0x09 = 0x22`. Leggendo il disassemblato per esteso a
`0x180009f3c` i valori veri sono `reg 0x35 = 0x02` e `reg 0x09 = 0x83`, cioe'
**identici al 0576**. La differenza reale e' una sola:

    0x180009fc0   mov dl, 0xfd ; mov cl, 0xa ; call write_register
    0x18000a03e   mov dl, 0xfc ; mov cl, 0xa ; call write_register
    0x180009e49   mov dl, 0xf4 ; mov cl, 0xa ; call write_register

la rampa di bias `fd -> fc -> f4` va sul **registro 0x0a**, mentre l'init del
0576 la manda sul **registro 0x10**. Piu' `reg 0x50 = 0x44` invece di `0x03`,
e due burst che sul 0576 non esistono: `63 11 03 01 00 72` e `63 34 02 07 01`.

### 22:44 — La calibrazione (`0x180008f84`)

Il driver non usa valori fissi per l'esposizione: c'e' un loop a
`0x180009060` che scrive `reg 0x12 = 0x0a` (guadagno) e poi abbassa
`reg 0x0f` di uno alla volta finche' il livello letto con `burst 0x67`
scende sotto `0x80`. Conferma indipendente di quanto avevo dedotto dallo
sweep: `0x12` guadagno, `0x0f` offset.

### 22:47 — Bisezione (`bisect-init.py`)

Il primo tentativo di init "tutto 057e" (`capture3.py`) dava frame
completamente neri. Colpa mia: avevo omesso il burst
`63 09 0b 83 24 00 44 0f 08 20 20 00 00 52` che carica i registri
0x09–0x13. Rimesso, tutte le varianti producono immagine:

| Variante | var | max | livelli |
|---|---|---|---|
| A 0576 puro | 53.54 | 131 | 48 |
| B 0x10 → 0x0a | 42.65 | 45 | 45 |
| C B + reg 0x50 = 0x44 | 41.74 | 45 | 44 |
| D B + burst 0x11/0x34 | 47.43 | 115 | 47 |
| E 0576 + reg 0x50 = 0x44 | 52.58 | 132 | 49 |
| F 0576 + burst 0x11/0x34 | 47.14 | 116 | 46 |

Quindi la sostituzione `0x10 → 0x0a` da sola **non** migliora: riduce il
massimo da 131 a 45. Con il guadagno a `0x0a` l'immagine di fondo e' comunque
molto piu' ricca di prima (48 livelli contro 6 di ieri).

### Test del dito

Due run continue (`live.py`, 1664 e 2801 frame) non hanno mostrato alcuna
reazione: `|Δ|` medio fermo a ~5, nessun pixel oltre la soglia `0x20` del
driver. Non e' pero' confermato che il sensore sia stato toccato durante le
finestre, quindi il dato non e' ancora conclusivo. Terza run in corso.

## 2026-08-18 22:44 — Il sensore reagisce al dito (primo risultato positivo)

Le due run precedenti erano nulle per un motivo banale: **non c'era modo di
sapere se il dito fosse davvero appoggiato**. Le notifiche `notify-send` non
venivano aggiornate a schermo da GNOME, quindi tutte e tre le fasi passavano
mentre l'utente vedeva ancora la prima. Confermato dall'utente: "io non ho
toccato nulla".

Sostituite con finestre modali `zenity --info`, che bloccano lo script finche'
non si clicca OK: e' l'utente a dettare i tempi, non il timer.
(`ab-zenity.py`, 40 frame per fase, gain `0x12 = 0x0a`.)

```
libero-1   n= 40  mean=  22.03 var=   43.94
dito       n= 40  mean=  21.59 var=  164.82
libero-2   n= 40  mean=  21.95 var=   44.06
|Δ| per pixel: medio=8.78 max=144.1
```

La varianza quasi quadruplica con il dito e **torna esatta al valore di
partenza** quando lo si toglie. La fase di controllo esclude derive termiche o
di calibrazione. Primo caso documentato di risposta al dito per `1c7a:057e`
su Linux.

Nota fisica: il sensore e' dentro il tasto di accensione, quindi il dito va
**appoggiato, non premuto**, altrimenti il portatile va in sospensione.

## 2026-08-18 22:47 — Flat-field: la diagonale non era quella che pensavo

`shot-finger.py` sottrae un riferimento per pixel (30 frame a vuoto) da 60
frame col dito e tiene i 5 a varianza piu' alta. La correzione **non** ha
tolto il pattern a diagonali:

```
0: var_corretta=172.44  var_grezza=188.66  range=103-197
```

Analisi dei frame salvati:

- l'autocorrelazione ha picchi a *tutti* i multipli di 3 (r ≈ 0.71), nessun
  picco alla larghezza di riga → il pattern e' dei canali ADC, non geometrico;
- nei frame a vuoto i 3 canali hanno la stessa media (35.5 / 35.2 / 35.2), ma
  nei frame col dito il canale 2 sta 23 livelli sotto gli altri due.

Quindi l'offset fra canali **non e' costante**: dipende dal segnale. Un
riferimento per pixel non lo puo' togliere. La correzione giusta e'
normalizzare la media di ciascun canale *dentro ogni frame*:

```python
def chan_norm(d):
    m = [statistics.mean(d[k::3]) for k in range(3)]
    g = statistics.mean(m)
    return [d[i] + g - m[i % 3] for i in range(len(d))]
```

Con questa la diagonale sparisce del tutto. Resta pero' un rumore per pixel di
sd ≈ 7.3, dello stesso ordine del segnale: un singolo frame non mostra creste,
solo sale e pepe. Aggiunto anche lo stretch sui percentili (2–98%), perche' con
min/max bastano pochi outlier a schiacciare tutto il resto.

## 2026-08-18 22:50 — Cattura ad alta SNR

`capture-hq.py`: 40 frame di fondo + 120 col dito **fermo**, tutti salvati
grezzi in `hq-ref.raw` / `hq-dito.raw`. Il dito e' statico e il rumore no,
quindi la media di N frame guadagna sqrt(N) ≈ 11×: sd 7.3 → ~0.7, sotto il
segnale. Salvare i grezzi serve a poter rielaborare offline senza dover
richiedere il dito a ogni tentativo.

## 2026-08-18 22:58 — Non e' un'immagine: l'array non viene scandito

`capture-hq.py` ha catturato 40 frame di fondo e 120 col dito fermo, tutti
salvati grezzi (`hq-ref.raw`, `hq-dito.raw`) per poterli rielaborare offline
senza richiedere il dito a ogni tentativo. `rework.py` prova media, mediana,
differenza e passa-alto a tre raggi.

Nessuna cresta. E il motivo non e' il rumore — mediando 120 frame la sd scende
da 12.8 a 3.7, quindi un segnale ripetibile *c'e'* (la correlazione fra frame
col dito sale a +0.20 contro +0.02 a vuoto). Il punto e' un altro:

```
autocorrelazione della media dei 120 frame col dito
  lag 1 = +0.29   lag 2 = -0.01   lag 3 = +0.01 ... lag 70 = -0.03
```

Correlano solo i byte adiacenti, e nient'altro. In un'immagine vera il lag 1
decade gradualmente e ricompare un picco alla larghezza di riga. Qui non c'e'
nessun picco a 70: **i dati non hanno struttura bidimensionale**.

La prova decisiva non richiede nemmeno il dito: **due frame consecutivi a
sensore libero correlano r = 0.019**. Ogni sensore d'immagine reale ha un
fixed-pattern noise, cioe' una firma per pixel identica frame dopo frame, e
due frame a vuoto devono correlare forte. A r = 0.02 stiamo leggendo rumore
casuale dell'AFE, non l'array di pixel. Il dito si fa sentire per accoppiamento
capacitivo residuo, non perche' lo stiamo fotografando.

### Due registri identificati male

`level-sweep.py` (griglia guadagno × offset, a sensore libero) ha smentito
quello che avevo scritto ieri:

- **il reg 0x12 non e' un guadagno**: da `0x10` a `0x80` l'uscita e' identica
  (media 112.4, sd 0.58, 5 livelli). Non amplifica niente;
- **il reg 0x0f non e' un offset DC ma un livello di test**: scritto
  singolarmente forza l'uscita piatta, e conta solo nei 6 bit bassi —
  `0x00`→0, `0x10`→51, `0x20`→112, `0x30`→173, `0x40`→0, `0x60`→112 (come
  `0x20`), `0xff`→230. Cioe' uscita ≈ `(reg & 0x3f) × 3.6`.

Quello che il reg 0x12 fa davvero e' **uscire dalla modalita' piatta**: dopo
il solo init il frame e' DC a 112.4 con 5 livelli, e serve `0x12 = 0x0a` per
ottenere un frame variabile. E' un arm, non un guadagno.

### Errore di metodo, corretto

La prima versione di `find-scan.py` cercava per forza bruta il registro che
accende la scansione, usando come criterio la correlazione fra frame a vuoto.
Ha girato 140 configurazioni **senza scrivere `0x12 = 0x0a` dopo l'init**,
quindi ha misurato la modalita' DC piatta per tutte, baseline inclusa: media
112.4 e correlazione ~0.24 ovunque, nessuna differenza fra i registri. Run
buttata.

Ho anche sbagliato la diagnosi: ho creduto che il sensore fosse rimasto
bloccato in modalita' test dalle scritture precedenti, e ho fatto un ciclo di
alimentazione USB (`authorized` 0→1 su `/sys/bus/usb/devices/3-5`) che non ha
cambiato nulla — perche' non c'era niente da sbloccare. Lo script e' stato
corretto con una funzione `arm()` che rimette `0x12 = 0x0a` dopo ogni init, e
la ricerca e' stata rilanciata.

### Perche' il driver Windows non basta

Le sequenze di comandi non sono tabelle di byte nelle DLL — cercate, zero
riscontri. Sono costruite in codice e per il 057e passano da vtable, cioe'
chiamate indirette che si risolvono solo a runtime: nel disassemblato statico
si vede *che* chiama qualcosa, non *cosa*. Il comando che accende la scansione
esiste ma non si estrae leggendo il binario. Restano due strade: la forza
bruta sui registri (in corso) oppure una VM Windows con cattura USB.

## 2026-08-18 23:12 — Registri 0x28–0x39 esclusi

`find-scan.py` rilanciato con l'`arm()` corretto (baseline sana: media 27.4,
sd 6.94, 50 livelli, corr +0.054). Risultato **negativo e pulito**: 18 registri
× 7 valori = 126 configurazioni, correlazione fra frame consecutivi sempre fra
+0.022 e +0.065. Nessuna si stacca dalla baseline, nessuna variazione di media
o di numero di livelli. In quell'intervallo non c'e' il bit che accende la
scansione.

Nota su come e' andata la prima esecuzione: la pipeline era
`python3 find-scan.py 2>&1 | tee scan-out.txt | head -8`, e `head` chiudendosi
dopo 8 righe ha ucciso il processo con SIGPIPE dopo il solo reg 0x28. Non era
un errore dello script.

## 2026-08-18 23:15 — Sweep del registro di modalita'

Il reg 0x12 resta l'unico che cambia il comportamento dell'acquisizione: dopo
il solo init il frame e' DC piatto (112.4, 5 livelli), con `0x12 = 0x0a`
diventa variabile (media 26, ~49 livelli). Non e' un guadagno, e' un selettore
di modalita' — e 0x0a e' solo *una* delle modalita'. `sweep-arm.py` prova tutti
e 256 i valori con lo stesso criterio del fixed-pattern noise, salvando il
frame delle dieci configurazioni migliori.

## 2026-08-18 23:30 — Sweep 0x12: nessun valore accende l'array

256 valori provati, nessun frame corto. Risultato negativo.

Le correlazioni piu' alte (0x12 = 0xd0, 0x60, 0x80, 0xb0 ... con corr +0.22 /
+0.25) sono tutte la **modalita' DC piatta**: media 112.5, sd 0.58, 6 livelli.
La correlazione alta li' e' un artefatto — con varianza quasi nulla si
correlano i pochi bit di rumore di quantizzazione, non un fixed-pattern. Vanno
scartate.

Fra le modalita' che producono un frame variabile (>35 livelli) il massimo e'
`0x12 = 0x2e` con corr +0.209, ma con media 3.7: immagine quasi nera. Le altre
si fermano a +0.17. Nessuna arriva a un fixed-pattern noise credibile.

Struttura del registro, dedotta dallo sweep: **conta il nibble basso**. Con
nibble basso 0 (0x10, 0x30, 0x40, 0x60, 0x70, 0x80, 0xb0, 0xd0, 0xf0) l'uscita
e' il DC piatto; con nibble basso diverso da 0 il frame e' variabile. Il nibble
alto sposta il livello medio.

Conclusione: la scansione dell'array non si accende ne' dai registri 0x28-0x39
ne' da nessun valore di 0x12. Il comando che manca non e' una scrittura di
registro fra quelle esplorate. Prossima strada seria: cattura USB del driver
Windows in VM.

## 2026-08-18 23:45 → 2026-08-19 00:30 — VM Windows 11: installazione e driver Egis

Costruita la VM `win11-fp` (libvirt `qemu:///system`, q35, UEFI+SecureBoot via
edk2-ovmf, TPM 2.0 via swtpm, 6144 MiB) con il sensore `1c7a:057e` passato in
hostdev. Obiettivo: far girare il driver Egis vero e catturare da host, con
usbmon, la sequenza di comandi che accende la scansione dell'array.

Cronologia e inciampi, inclusi i miei:

- **Boot fallito**: l'utente aveva scelto la voce `UEFI QEMU HARDDISK` (disco
  vuoto) invece del CD. Il firmware non trovava nulla e il guest si spegneva da
  solo — `terminating on signal 15` in `/var/log/libvirt/qemu/win11-fp.log`,
  cioe' spegnimento richiesto dal guest, non OOM ne' crash di QEMU.
  Prima di toccare altro ho verificato l'integrita' della ISO parsando il PVD
  ISO9660 (dimensione dichiarata == dimensione reale) e il catalogo El Torito
  (entry EFI, platform 0xEF presente): ISO sana. Risolto stabilmente con
  `virt-xml --edit target=sdb --disk boot.order=1` e `target=sda ... boot.order=2`.
- **Mio errore di unita'**: `virt-xml --edit --memory memory=6291456` →
  `Cannot allocate memory`. `virt-xml --memory` vuole **MiB**, quindi avevo
  chiesto 6 TB di RAM. Corretto con `--memory memory=6144,currentMemory=6144`.
- **Mio errore di metodo**: ho guidato la GUI del guest alla cieca con una
  sequenza concatenata di tasti; e' finita su "Devices and Printers" e poi in
  Impostazioni → Account. Da li' in poi: **un gruppo di tasti per chiamata,
  screenshot di verifica prima del successivo**. Regola tenuta per tutto il
  resto della sessione.
- Windows 11 25H2 installato con account locale (bypass `ms-cxh:localonly`),
  nessuna credenziale dell'utente coinvolta.
- Windows Update non aveva il driver: il sensore veniva legato al generico
  **WinUsb**. Impacchettato il driver proprietario (INF + CAT + 3 DLL) in una
  ISO (`genisoimage -J -r -V EGISDRV`), montata come CD, installato con
  "Update Driver" puntando a `d:\`. Esito: **"Windows has successfully updated
  your drivers — EgisTec Touch Fingerprint Sensor"**, firma accettata.

Nota di metodo per il guest: layout tastiera **italiano** (`:` = Shift+KEY_DOT,
`\` = KEY_GRAVE, `/` = Shift+KEY_7). Scritto `type.sh` per digitare stringhe via
`virsh send-key`, e `shot.sh` per screenshot+conversione. Da li' in poi i
comandi lunghi non si digitano: si mettono in un `.cmd` sulla ISO e si lancia
`d:\nome.cmd` da un terminale admin (Win+X → A).

## 2026-08-19 00:00 — Cattura usbmon avviata

`usbmon-capture.sh` + `parse-usbmon.py` (decoder EGIS/SIGE, `--seq` produce la
lista `(reg, val)` da incollare in `capture2.py`). Verificati sulla cattura
reale. Il device resta su bus 3 dev 5 con `driver = usbfs`: QEMU lo possiede e
ogni URB e' visibile da host, quindi niente USBPcap dentro Windows.

Finora nel log solo enumerazione ep0 (descriptor `12 01 00 02 ff 00 00 40 7a 1c
7e 05 ...`, VID/PID confermati), **0 scritture di registro**: il driver parla
solo quando Windows Hello lo usa davvero.

## 2026-08-19 08:50 → 09:15 — Windows Hello: "nessun sensore compatibile". Causa trovata

Sintomo: Impostazioni → Account → Opzioni di accesso →
*"We couldn't find a fingerprint scanner compatible with Windows Hello"*.

**Prima ipotesi (sbagliata): Enhanced Sign-in Security.** ESS blocca i sensori
biometrici non-ESS e i sensori "periferici", e il nostro passa via USB. Ho
predisposto il flag documentato
`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WinBio\SupportPeripheralsWithEnhancedSignInSecurity=1`.
Non era quello.

**Causa reale**, da `pnputil /enum-devices /class Biometric`:

    Device Description: EgisTec Touch Fingerprint Sensor
    Class Name:         Biometric          <- enumerato nella classe giusta
    Status:             Problem
    Problem Code:       10 (0x0A) [CM_PROB_FAILED_START]
    Problem Status:     0xC00002D3
    Driver Name:        oem2.inf           <- il nostro INF

`0xC00002D3` = **STATUS_POWER_STATE_INVALID**. Log UMDF (va abilitato:
`wevtutil sl Microsoft-Windows-DriverFrameworks-UserMode/Operational /e:true`):

    [Error]   id=2103  Completed a Pnp or Power operation (27, 0) ... status 0xC00002D3
    [Verbose] id=2006  The UMDF Host successfully loaded the driver at level 0
    [Warning] id=219   WudfRd failed to load. Status: 0xC0000365 (FAILED_DRIVER_ENTRY)

Quindi: **il DLL Egis si carica senza problemi** — nessuna dipendenza mancante,
nessun problema di firma — e fallisce subito dopo su un'operazione di power.

Interpretazione, confermata da un thread OSR su `WdfDeviceAssignS0IdleSettings`:
la funzione ritorna `STATUS_POWER_STATE_INVALID` quando le capabilities del
device riportano `DeviceWake = PowerDeviceD0`, cioe' "questo device non puo'
segnalare wake". Il driver Egis pretende il wake-from-S0 — e ha senso: **il
sensore sta dentro il tasto di accensione**, il suo mestiere e' svegliare il
PC al tocco. L'INF lo dichiara: `RemoteWakeupEnable=1`, `DeviceIdleEnabled=1`,
`WdfDirectedPowerTransitionEnable=1`. E il device stesso lo dichiara nel
descrittore di configurazione: `bmAttributes = 0xa0`, bit remote-wakeup acceso.

Ma il wake non dipende solo dal device: serve che lo offra anche il controller.
E il controller qui e' emulato.

**Tentativi lato registro, tutti negativi** (device riavviato ogni volta con
`pnputil /restart-device`, stesso `Code 10` / `0xC00002D3`):

- `DeviceIdleEnabled=0`, `SystemWakeEnabled=0`, `DeviceIdleIgnoreWakeEnable=1`
- `WudfPowerPolicySettings\WdfDefaultIdleInWorkingState=0`,
  `WdfDefaultWakeFromSleepState=0`
- `WDF\WdfDirectedPowerTransitionEnable=0`
- `WudfPowerPolicySettings\IdleInWorkingState=0` (valore *effettivo*, distinto
  dal `WdfDefault...`: l'ho trovato solo enumerando davvero le chiavi invece di
  assumerle)

Il driver evidentemente hardcoda `IdleCanWakeFromS0` e ignora gli override.

Nota: la sottochiave che l'INF crea con **spazio finale** (`EgisTouchFP057E `,
scritta nell'INF come `HKR,EgisTouchFP057E\ ,`) non e' raggiungibile ne' con
`reg add "...\EgisTouchFP057E "` ne' con `Get-Item -LiteralPath`: entrambi
trimmano. Da rivedere se dovesse tornare utile.

**Azione in corso**: sostituito il controller USB della VM, da `qemu-xhci` a
`ich9-ehci1` + tre compagni `ich9-uhci1/2/3` (XML salvato prima in
`win11-fp.xml.bak.20260819-091200`), per vedere se un controller con power
management PCI diverso espone il wake al guest.

**Se non basta**: la strada certa e' Windows su ferro vero — su questo laptop
il sensore *funzionava* con Windows 11 preinstallato, quindi li' il driver
parte per definizione. Installazione su SSD USB esterno (Windows To Go) o
partizione dedicata, e cattura con USBPcap dentro Windows invece che con
usbmon da host.

---

## 2026-08-19 — la VM chiude, e il vero problema era da un'altra parte

### 09:15–10:30 — chiusura della strada VM, con le misure in mano

La SSDT con `_PRW` era **progresso vero e misurato**: `powercfg /devicequery
wake_from_any` passava da NONE a includere i root hub. Ma il device USB in se'
non guadagnava mai la capacita' di wake, ne' con `_PRW` da solo ne' aggiungendo
`_S0W`. Il buco sta **dentro il controller USB emulato**, e da ACPI non ci si
arriva: ACPI dichiara il wake del bus, non quello della porta.

Tentativi e loro esito, in ordine:

| tentativo | esito |
|---|---|
| ESS (`SupportPeripheralsWithEnhancedSignInSecurity=1`) | ipotesi sbagliata, smentita da `pnputil` |
| override di registro sull'idle/wake del driver | nessun effetto, `Code 10` invariato |
| `qemu-xhci` -> `ich9-ehci1` + `uhci1/2/3` | nessun wake |
| SSDT `_PRW` {0x0D, 0x03} | root hub wake-capable, device no |
| SSDT `_PRW` {0x0D, 0x04} (+S4) | **regressione mia**: la VM non supporta S4, Windows ha scartato tutto il `_PRW` e la lista wake si e' richiusa. Ripristinato 0x03 |
| `_S0W` 0x03 sui device USB | nessun cambiamento |

**Perche' avevamo scelto la VM**: era l'unico modo di far girare il driver Egis
vero e catturare da host con usbmon la sequenza che accende la scansione.
**Perche' l'abbiamo abbandonata**: il driver *si carica* correttamente (UMDF
id=2006, classe Biometric, `oem2.inf`) — quindi niente problemi di firma,
dipendenze o ESS — ma fallisce `IRP_MN_START_DEVICE` con
`STATUS_POWER_STATE_INVALID` perche' pretende il wake-from-S0. Cosa peraltro
logica: **il sensore *e'* il tasto di accensione**. Un requisito hardware che
una macchina virtuale non puo' soddisfare. Non e' una resa: e' una diagnosi.

### 10:30–11:00 — il confronto che ha fatto girare tutto

Invece di insistere, siamo andati a leggere il driver libfprint del fratello
`egis0570` (stesso produttore, sensore vicino). Scaricato da
`gitlab.freedesktop.org/libfprint/libfprint`. Tre cose non tornavano col nostro
modello:

1. legge blocchi da **32512 byte** = 5 frame in una volta, non uno;
2. arma con reg `0x02`: `0x0f` -> `0x2f` -> richiesta immagine;
3. tratta il flusso come **continuo**.

Verifica diretta (`probe-arm.py`): chiedendo 5320 byte il sensore ne consegna
**133000**. Il flusso e' continuo, confermato.

### 11:00–11:30 — la causa del vicolo cieco: `depad()`

`stream-period.py` (autocorrelazione via FFT, Wiener-Khinchin — in Python puro
erano centinaia di milioni di moltiplicazioni) su 400 KB di flusso:

- picchi a `corr = +1.0000` a ogni multiplo di **5320**;
- **zeri per residuo mod 4 = [0, 0, 0, 0]**.

Cioe': **nessun byte di padding**. Ma `capture2.py::depad()` assumeva
"3 byte utili su 4", sceglieva il residuo mod 4 con piu' zeri e lo buttava.
Su dati senza padding questo **distrugge un quarto dei pixel e sfasa il resto**,
in modo diverso a ogni frame.

**Ecco l'errore che ci ha bloccati per giorni.** Due frame consecutivi, mutilati
e sfasati ciascuno a modo suo, non correlavano (r ~ 0.02), e da li' la
conclusione sbagliata "l'array non viene scandito" — che e' quella che ci ha
spinti a cercare il comando magico dentro Windows, cioe' tutta la strada VM.
La lezione: prima di dedurre dal comportamento, **verificare il modello di
trasporto**. Il disassemblato dava le costanti giuste (70x57); era sbagliata
l'ipotesi su come quei pixel viaggiano sul filo.

### 11:30–11:45 — geometria vera

`frame-geom.py` sui flussi salvati:

- 76 frame per cattura, **0 byte diversi** fra l'uno e l'altro (senza
  ri-armare il sensore ripete lo stesso buffer);
- autocorrelazione interna con picchi a lag 70, 140, 210, 280... -> passo di
  riga **70**;
- righe 0..56 con segnale; righe 57..75 tutte a **117 esatto**, sd 0.00.

Quindi: **70 x 57 = 3990 pixel + 1330 byte di coda costante = 5320**. Il
padding esiste ma sta **in coda**, non intercalato.

Con la lettura corretta (`capture3.py`), due catture indipendenti correlano a
**r = +0.95 / +0.96** invece di +0.02: il fixed-pattern noise c'e', l'array
viene scandito. Il criterio e' quello giusto perche' il rumore a pattern fisso
e' una firma del silicio: se due frame indipendenti lo condividono, vengono
davvero dallo stesso array letto due volte.

### 11:45–12:00 — ri-armare senza reset USB

Riaprire il device costa un reset USB e ~2 secondi: troppo per inseguire un
dito. `retrigger.py` ha provato 8 candidate. Una sola ri-arma davvero:

    45474953632c020013   = burst write (cmd 0x63) reg 0x2c = 02 00 13

E' l'ultima riga dell'INIT_SEQUENCE e da sola basta (sd 2.08, ~1380 byte che
cambiano a ogni frame, r +0.96). Tutte le altre lasciano il sensore congelato
sullo stesso buffer, 0 byte diversi. Frame da millisecondi invece che secondi.

### 12:00 — il dito non compariva: guadagno a zero

Primo test col dito: **piatto**. Scarto massimo 0.403 contro rumore 0.230, e
per giunta al frame 0 (transitorio d'avvio); gli altri 79 frame tutti a ~0.28.
`dito-differenza.png` era rumore puro.

Prima di richiedere il dito all'utente, controllo che non costa niente
(`sweep-gain.py`): **l'immagine risponde ai registri analogici?**

    reg 0x12 (guadagno):  0x00 -> sd 2.06,  18 livelli
                          0x0a -> sd 36.0, 201 livelli
                          0x0f -> sd 44.6, 221 livelli, gamma piena 0-255

E rileggendo i registri si scopre la larghezza vera dei campi:

- **guadagno 0x12 = 4 bit**: 0x20 rilegge 0x00, 0xff rilegge 0x0f;
- **offset 0x0f = 6 bit**: 0xff rilegge 0x3f.

`calib.py` (griglia 16 guadagni x 5 offset): l'offset ha **una sola posizione
utile, 0x20** — fuori di li' l'immagine va tutta a 0 o tutta a 255. Miglior
punto senza tosatura: **guadagno 0x0a, offset 0x20**, sd 35.9, 1.8% di pixel a
fondo scala.

**Il punto**: dopo l'init il guadagno resta a **0x00**, cioe' 18 livelli su
256. Tutti i test col dito fatti finora giravano li'. La variazione prodotta da
un dito appoggiato finiva **sotto il passo di quantizzazione**. Non e' che il
sensore non reagiva: non lo stavamo mai chiedendo con abbastanza guadagno.

### Metodo — errori miei da non ripetere

- `_PRW` con S4 su una VM che S4 non ce l'ha: ho peggiorato una cosa che
  funzionava. Cambiare **una** variabile per volta e rimisurare.
- `pkill -f stream-period.py` ha fatto match sulla **mia stessa riga di
  comando** (conteneva il testo dell'heredoc) e si e' ucciso da solo: lo script
  nuovo non e' mai stato scritto e continuava a girare il vecchio. Uccidere per
  PID, scrivere i file con lo strumento di scrittura.
- Registri Windows azzerati "per sicurezza" (`DeviceIdleEnabled`,
  `SystemWakeEnabled`, `RemoteWakeupEnable`) quando il wake non esisteva
  ancora: appena `_PRW` l'ha creato, quegli zeri lo bloccavano. Non lasciare in
  giro mitigazioni di problemi risolti.
- Notifiche `notify-send`: restano a schermo, non si cancellano comodamente e
  soprattutto non garantiscono che il dito fosse appoggiato nella fase giusta.
  Sostituite da finestre modali `zenity` — i tempi li detta l'utente
  (`dito-zenity.py`).
- Regola generale emersa: **prima di dedurre dal comportamento, verificare il
  modello di trasporto e il punto di lavoro**. Due giorni persi su una
  conclusione ("l'array non scandisce") che era un artefatto di `depad()`, e
  mezza giornata su un dito invisibile che era solo guadagno a zero.

### File

- `capture3.py` — lettura corretta (5320 sul filo, 3990 pixel, coda scartata)
- `probe-arm.py` — misura del flusso continuo
- `stream-period.py` — periodo e assenza di padding, FFT
- `frame-geom.py` — passo di riga e righe attive
- `retrigger.py` — ricerca del comando di ri-arming
- `sweep-gain.py` — risposta ai registri analogici, larghezza dei campi
- `calib.py` — punto di lavoro (guadagno, offset)
- `dito-zenity.py` — A/B del dito con finestre modali e fase di controllo

`capture2.py` resta importato per `init/cmd/wr/rd/png_gray`, ma **`depad()` e
`get_frame()` non vanno piu' usati**: portano dentro l'ipotesi di trasporto
sbagliata.

### 12:20 — **prima impronta letta su Linux**

`dito-zenity.py --frames 30`, guadagno 0x0a, offset 0x20, tre fasi modali:

    libero-1   n=30  media= 71.28  sd spaziale=35.82  sd temporale=4.60
    dito       n=30  media=100.78  sd spaziale=90.61  sd temporale=3.38
    libero-2   n=30  media= 68.90  sd spaziale=35.71  sd temporale=4.55

    libero-1 vs libero-2   |delta| medio= 2.44  max=  9.0  pixel oltre 8 =    1
    dito vs fondo          |delta| medio=80.87  max=181.8  pixel oltre 8 = 3780

    rapporto segnale/deriva = 33.11x

`dz-dito.png` mostra **creste dattiloscopiche nitide, con una biforcazione
visibile**. La fase di controllo e' quella che rende il risultato solido: il
sensore lasciato a se stesso deriva di 2.4 livelli, il dito ne sposta 81. Non
e' deriva, non e' un artefatto di elaborazione.

Il contrasto spaziale passa da 35.8 (vuoto) a 90.6 (dito): il dito non aggiunge
solo un livello medio, aggiunge **struttura**.

Cronologia del tappo, per chiarezza: (1) `depad()` mutilava un pixel su quattro
e sfasava il resto, facendo sembrare che l'array non venisse scandito — da li'
tutta la deviazione su Windows/VM; (2) risolto quello, l'init lasciava il
guadagno a 0x00 (18 livelli su 256) e il dito restava sotto il passo di
quantizzazione. Due cause indipendenti, in fila.

**Prossimi passi**: enrollment e matching, poi driver libfprint per
`1c7a:057e`, poi PAM (`authselect enable-feature with-fingerprint`).

### 12:00–12:20 — driver libfprint `egis057e`

Un PNG non sblocca niente: serve il driver dentro libfprint, perche' e' da li'
che passano fprintd, GDM, `sudo` e il blocco schermo.

Sorgente clonato da `gitlab.freedesktop.org/libfprint/libfprint`, versione
**1.94.100**, identica a quella installata su Fedora 44 — cosi' la libreria
compilata e' sostituibile a quella di sistema senza disallineamenti di ABI.

Nuovi file: `libfprint/drivers/egis057e.{c,h}`, registrati in `meson.build` e
`libfprint/meson.build`. Modello preso da `egis0570` (stessa famiglia), ma il
nostro e' un sensore **a pressione**, non a strisciata: un frame e' gia' tutta
l'immagine, niente `fpi_assemble_frames`.

Struttura: `FpImageDevice` con una macchina a stati che manda i 31 pacchetti di
init (il pacchetto "flush" e' un caso a parte: la sua risposta e' un frame
intero, non un ack corto), poi cicla ri-arma -> richiedi immagine -> leggi 5320
byte. Le prime 8 letture diventano il fondo di riferimento; i frame con
deviazione spaziale sopra 60 sono scartati dal fondo, cosi' un dito gia'
appoggiato all'attivazione non viene imparato come sfondo e reso invisibile.

Due correzioni di build fatte strada facendo:

- `tests/meson.build:295` itera un dict con una sola variabile di ciclo, cosa
  che meson 1.11 rifiuta. Colpisce solo il ramo senza introspection, che e'
  come compiliamo noi. Corretto in `foreach driver_test, _unused:`.
- **segfault in `fpi_image_resize`**: pixman vuole il passo di riga multiplo di
  4 byte e libfprint gli passa la larghezza come passo. 70 non lo e'.
  Si scarta una colonna per lato: 68 e' multiplo di 4, e lo e' anche 68*4.
  Immagine finale 272x228 (fattore 4, NBIS trova piu' minuzie su una copia
  ingrandita).

**Prima prova con il driver, log di `img-capture`:**

    distance from background  3.99  -> finger status: off
    distance from background  4.01  -> finger status: off
    distance from background 60.22  -> finger status: on
    distance from background 60.63  -> finger status: on

Init, ciclo di cattura e **rilevamento del dito funzionano dentro libfprint**.
La soglia a 15 e' esattamente dove serve: 4 a vuoto, 60 col dito.

### 12:20–12:50 — NBIS non trova minuzie: perche', e cosa non era il problema

`img-capture` col driver arriva in fondo senza crash ma finisce con
**"No minutiae found"**. Prima di cambiare codice a caso, si e' misurato.

**Scala.** Spettro di potenza 2D del frame col dito, fondo sottratto: picco
netto a 32 cicli su 256, cioe' **creste ogni 8.0 pixel**. Il sensore e' quindi
sui 400 dpi, e 8 px per cresta e' gia' quasi la scala che NBIS si aspetta (a
500 dpi sarebbero 9.8). Ingrandire 4 volte portava il periodo a **32 px**: e'
per quello che NBIS non trovava niente. Il fattore giusto e' circa **1.25**,
non 4. Errore di metodo: avevo scelto il 4 per "aiutare NBIS", senza misurare
la scala a cui NBIS lavora.

**Il flag PARTIAL.** Avevo messo `FPI_IMAGE_PARTIAL` ragionando che
l'immagine e' un frammento. In `fp-image.c` quel flag accende pero'
`remove_perimeter_pts`, che **scarta le minuzie vicine al bordo**: su
un'immagine di 4 mm per lato sono quasi tutte. Tolto.

**Strumenti costruiti per non chiedere il dito a ogni tentativo:**

- `grab-raw.py` — cattura fondo e dito **grezzi** una volta sola
- `make-pgm.py` — genera le varianti di elaborazione (grezza, mediana, fondo
  sottratto, equalizzata, percentili stretti)
- `mintest.c` — carica un PGM, prova scale da 1.0 a 4.0 e le due polarita', e
  stampa quante minuzie trova NBIS

Risultato dello spazzamento, su tutte e cinque le elaborazioni:

    scala 1.00  -> nessuna minuzia
    scala 1.25  -> 2
    scala 1.75  -> 3      <- massimo
    scala 2.00  -> 3
    scala 3.00  -> 2
    scala 4.00  -> nessuna

**Il limite non e' l'elaborazione: e' l'area.** L'immagine e' pulita — creste
nette, una biforcazione ben visibile (`v3-menofondo.png`). Ma 68x57 px a 400
dpi sono **4.3 x 3.6 mm, cioe' 15 mm²**, e con una densita' tipica di 0.25-0.5
minuzie per mm² ci si aspettano proprio due o quattro minuzie. NBIS ne trova
tre: sta funzionando correttamente su un'immagine troppo piccola.

Tre minuzie non bastano a bozorth3 per decidere alcunche'. Abbassare la soglia
di somiglianza per farlo "funzionare" con tre punti significherebbe accettare
chiunque: non e' una soluzione, e' un buco.

**Direzione scelta: mosaico.** E' quello che fa anche `egis0570`, il fratello
con un sensore di area doppia, che infatti e' dichiarato `FP_SCAN_TYPE_SWIPE` e
unisce strisce di fotogrammi. Se il dito scorre, fotogrammi successivi vedono
parti diverse del polpastrello e insieme coprono molta piu' area.

`capture-swipe.py` registra la sequenza; `stitch.py` stima lo spostamento fra
fotogrammi consecutivi per **correlazione di fase** (il picco della cross-
potenza normalizzata cade esattamente sullo scostamento, ed e' insensibile al
cambio di contrasto — che qui c'e', perche' la pressione varia durante la
passata) e li fonde su una tela comune.

Se il mosaico porta le minuzie a venti o piu', la strada e' quella. Se no,
questo sensore non e' compatibile con il confronto a minuzie e serve un
confronto per correlazione, che libfprint non offre per gli image device.

### 12:50 — prima passata: troppo corta, ma un dato inatteso

La finestra di cattura era di 220 fotogrammi. A 55 fotogrammi al secondo sono
**4 secondi**, e il dito e' comparso al fotogramma 134: restavano 1.6 secondi di
passata. Corsa totale stimata 5 righe e 12 colonne — praticamente fermo.
Finestra portata a 1400 fotogrammi (25 secondi).

Il mosaico di quei pochi fotogrammi dice pero' una cosa che non ci si
aspettava:

    singolo fotogramma, scala 1.75   ->  3 minuzie
    mosaico di 86, scala 1.75        -> 12 minuzie
    mosaico di 86, scala 3.00        -> 22 minuzie

L'area coperta e' quasi la stessa (80x62 contro 68x57): il guadagno non viene
dallo scorrimento, viene dall'aver **mediato 86 fotogrammi**. Il rumore
temporale e' 3.4 livelli per fotogramma, e mediandone 86 scende di quasi dieci
volte; NBIS vede creste molto piu' pulite e trova punti che prima annegavano.

Quindi ci sono due leve distinte, e vanno tenute separate:

  1. **mediare** molti fotogrammi -> meno rumore -> piu' minuzie sulla stessa
     area. Non chiede niente all'utente se non tenere il dito fermo un attimo;
  2. **unire** fotogrammi spostati -> piu' area. Chiede una passata.

La prima e' gratis e va messa comunque nel driver. Della seconda si vedra' con
la passata lunga.

Cautela: a scala 3 e 4 il conteggio sale ancora (21, 30), ma su un'immagine
molto interpolata NBIS puo' inventare punti dove c'e' solo levigatura. Il
numero di minuzie e' un indizio, non la prova: la prova e' che un confronto
riconosca lo stesso dito e rifiuti gli altri.


## 2026-08-19 14:xx — il confronto smonta lo stitching (e due errori miei)

Fatta la catena di confronto vera, che mancava: `cmp.c` estrae le minuzie con
l'API pubblica `fp_image_detect_minutiae` e poi chiama bozorth3. I simboli
interni della libreria sono nascosti dal version script (`nm -D` non mostra
nessun `bozorth_*`), quindi i sei sorgenti di `nbis/bozorth3/` si compilano
dentro l'eseguibile. `bozorth_main` e' dichiarato in `bozorth.h` ma non esiste
piu' nel codice: la coppia viva e' `bozorth_probe_init` + `bozorth_to_gallery`,
che e' anche quella che usa `fpi_print_bz3_match`. `minutiae_to_xyt` e
`lfs2nist_minutia_XYT` sono ricopiate identiche, altrimenti i punteggi non
sarebbero confrontabili con quelli che produrra' il driver.

Prova di sanita': stessa immagine contro se' stessa, 441. La catena gira.

### Il verdetto

Tre passate: indice, indice, medio. Punteggi bozorth3, soglia libfprint 40:

                  mosaico    m1    m2    m3
        mosaico         -     8     3     0
             m1         8     -     3     0
             m2         3     3     -     0
             m3         0     0     0     -

L'ordine e' quello giusto (stesso dito sopra dita diverse) ma la magnitudo e'
inutilizzabile: serve 40, si ottiene 8.

### Primo errore mio: la correlazione di fase a passo intero

`stitch.py` stimava lo spostamento fra fotogrammi *consecutivi*, e la stima e'
intera. A 55 fotogrammi al secondo e 16 pixel per millimetro, un dito che
scorre a un millimetro al secondo si sposta 0.3 pixel per fotogramma, che
arrotondato fa zero. Mille zeri sommati fanno zero: `corsa totale 0 righe` su
una passata in cui il dito si era mosso. E la richiesta che avevo fatto
all'utente -- "cinque millimetri in venti secondi" -- peggiorava apposta la
cosa: piu' lento vai, piu' la stima si annulla.

Corretto misurando contro un fotogramma di riferimento tenuto fermo finche' lo
scostamento non supera otto pixel. Ogni misura sta cosi' ben sopra il passo di
quantizzazione, e non si accumula l'errore di mille stime.

### Secondo errore mio: la corsa di ieri era inventata

Con la versione sbagliata, i 1399 errori da un pixel si sommano come un
cammino casuale: sqrt(1399) ~ 37 passi di deriva, che e' l'ordine dei "115
righe per 189 colonne" registrati ieri. Il mosaico grande non era piu' area:
era una sbavatura. Il che spiega da solo perche' le sue 44 minuzie contro
un'immagine vera dello stesso dito facessero 8 -- erano quasi tutte prodotte
dall'interpolazione, esattamente la cautela che avevo scritto ieri e poi non
avevo applicato.

### E il dito non trasla comunque

Misurato invece di supporre. Fra fotogrammi lontani nel tempo l'immagine
cambia moltissimo (distanza media fino a 167, correlazione -0.15), ma la
correlazione di fase mette il picco a (0,0) con qualita' 0.94. Un picco alto
centrato sullo zero vuol dire che il disegno delle creste sta nello stesso
posto. Quello che cambia e' la pressione: la media per fotogramma oscilla fra
-57 e +123, la deviazione spaziale fra 36 e 102, mentre fra fotogrammi
consecutivi la distanza resta 3.6.

Il sensore e' dentro un tasto da cinque millimetri: l'utente muove il dito, ma
il lembo di pelle a contatto resta lo stesso e si deforma soltanto. Non e' un
sensore a scorrimento e non lo diventa chiedendo una passata piu' lunga.

Quindi: niente stitching, niente area in piu', e con 15 mm2 di creste quasi
parallele bozorth3 non ha abbastanza minuzie per decidere. Questa strada e'
chiusa, ed e' bene saperlo adesso invece che dopo aver messo lo stitching nel
driver.

### La strada che resta: confronto per correlazione

Se non ci sono minuzie, si confronta il disegno. Provato sui dati gia' presi,
sei campioni per passata, ognuno media di 40 fotogrammi vicini, correlazione
normalizzata massima su tutti gli scorrimenti fino a 8 pixel:

    grezza              stesso dito max 0.657   dita diverse max 0.594
    con passabanda      stesso dito max 0.759   dita diverse max 0.576

Il passabanda e' una gaussiana attorno a 0.125 cicli/pixel, cioe' il periodo
di 8 pixel misurato ieri: sotto c'e' la pressione, sopra il rumore termico.
Togliere entrambi apre un margine che sulla correlazione grezza non c'era.

E' sottile e su tre sole passate, ma e' la prima cosa che separa. Va nella
direzione giusta anche per un'altra ragione: un `FpImageDevice` puo' solo
usare bozorth3, mentre un `FpDevice` normale si scrive enroll e verify per
conto suo e puo' salvare come modello quello che vuole. Il driver quindi
cambia forma: non piu' image device.

Prossimo passo: raccogliere abbastanza dita per stimare falsi accessi e falsi
rifiuti sul serio. Tre passate non bastano a fissare una soglia.


## 2026-08-19 15:xx — il driver diventa un FpDevice

Raccolti quindici appoggi: cinque dita per tre. Niente passate, perche' non
servono piu' a niente; otto secondi di dito fermo ciascuno.

Iscrivendo gli appoggi 1 e 2 e verificando col terzo, filtro in frequenza:

    genuini    min 0.288   media 0.606   max 0.815
    impostori  min 0.068   media 0.254   max 0.519

Nessun falso accesso su venti confronti a soglia 0.55. Venti confronti non
misurano un tasso di falsi accessi -- per quello servono migliaia -- ma dicono
che il segnale c'e'.

### Quanti modelli, e di che tipo

    1 appoggio,  4 campioni    genuino min 0.143   impostore max 0.458
    1 appoggio,  8 campioni    genuino min 0.143   impostore max 0.458
    2 appoggi,   8 campioni    genuino min 0.288   impostore max 0.519
    2 appoggi,  16 campioni    genuino min 0.288   impostore max 0.519
    2 appoggi,  32 campioni    genuino min 0.288   impostore max 0.519

Quadruplicare i campioni estratti dallo stesso appoggio non sposta un
millesimo; raddoppiare gli appoggi raddoppia il genuino peggiore. Conta il
numero di posizioni distinte del dito, e nient'altro. Da cui: un modello per
appoggio, venti appoggi in iscrizione, e nessuno spreco di spazio a tenere
venti varianti della stessa posizione.

E' anche la spiegazione dell'unico dito che falliva, l'indice sinistro: il suo
terzo appoggio aveva preso una zona di polpastrello che i primi due non
coprivano. Non e' il confronto che sbaglia, e' l'iscrizione troppo magra.

### Il passabanda diventa differenza di gaussiane

libfprint non porta una FFT e non ha senso scriverne una nel driver. Provata la
differenza di due sfocature gaussiane, che e' separabile e costa poche passate:

    banda in frequenza 0.125 +- 0.045   genuini media 0.606   impostori max 0.519
    DoG 1.2 / 3.5                       genuini media 0.573   impostori max 0.454

Un po' piu' bassa sui genuini, piu' bassa sugli impostori, che e' il lato da
cui si sceglie la soglia. Presa quella.

### Il driver

Riscritto come `FpDevice`, non piu' `FpImageDevice`: quelli sanno essere
confrontati solo da bozorth3, e bozorth3 su questo sensore non ha abbastanza
minuzie. Ora enroll e verify sono scritti nel driver, il modello e' il disegno
delle creste filtrato e quantizzato a byte con segno (3990 byte per appoggio),
e il confronto e' la correlazione normalizzata migliore su tutti gli
scorrimenti fino a otto pixel.

Tre cose trovate scrivendolo:

- `blur()` aveva un passaggio verticale di troppo che leggeva la sorgente
  invece del risultato orizzontale. Trovato rileggendo, non dal compilatore:
  sarebbe stato un filtro sbagliato ma plausibile.
- GObject rifiuta un'istanza sopra i 65535 byte, e due array inline di 3990
  `gdouble` fanno 62 KB da soli. L'errore non arriva dal compilatore ma da
  `g_type_register_static_simple` a tempo di esecuzione, e si manifesta come un
  fallimento dei generatori di udev rules. Spostati sull'heap.
- Era rimasta una chiamata a una funzione da image device, residuo della forma
  precedente.

### La prova che il port sia fedele

`matchtest.c` include `egis057e.c` per intero -- le funzioni di calcolo sono
static, e includerlo e' l'unico modo di provare proprio il codice che gira
invece di una copia che puo' divergere -- e rifa' la stessa tabella sulle
stesse catture:

    Python DoG 1.2/3.5   genuino min 0.230   media 0.573   impostore max 0.454
    C dentro il driver   genuino min 0.241   media 0.565   impostore max 0.451

Il port e' fedele. Le differenze restanti vengono da come i due scelgono i
fotogrammi da mediare, non dal calcolo.

Nota sulla soglia: a 0.50 l'indice destro si ferma a 0.481 e verrebbe
rifiutato, con due soli appoggi iscritti. Non si abbassa la soglia per farci
stare questi dati -- sarebbe cucirla su cinque dita -- perche' la leva giusta e'
l'iscrizione a venti appoggi, che e' quella che alza i genuini. Se dopo una
iscrizione vera il rifiuto resta, allora si ritara con dati veri.

---

## 19/08/2026, 13:40-15:45 — il sensore autentica davvero

Fino a ieri il driver era una cosa che compilava. Oggi ha girato sul ferro, ed
e' successo quello che succede sempre: la prima esecuzione ha trovato tre
difetti che nessuna quantita' di rilettura del codice avrebbe trovato.

### 13:41 — il driver muore all'avvio

    libfprint-device:ERROR:../libfprint/fp-device.c:171:fp_device_constructed:
    assertion failed: (cls->features != FP_DEVICE_FEATURE_NONE)

Un `FpDevice` deve dichiarare cosa sa fare. Passando da `FpImageDevice` a
`FpDevice` questo pezzo era rimasto scoperto: `FpImageDevice` lo compila da solo
nella propria class_init (`fp-image-device.c:225`), un `FpDevice` no.

Messo `FP_DEVICE_FEATURE_VERIFY`, e solo quello:

- niente `CAPTURE`, perche' non si consegna mai un'immagine a chi chiama;
- niente `STORAGE`, perche' i modelli tornano a fprintd come blob;
- niente `IDENTIFY`, perche' il margine misurato fra dita diverse non regge un
  confronto uno-contro-molti.

Vale la pena notare *come* si e' visto: il crash e' arrivato al primo avvio
reale, non dal compilatore. Un driver che compila pulito e passa un test di
calcolo puo' ancora non costruirsi nemmeno.

### 13:42 — il nome sul bus se lo prende il servizio di sistema

Corretto il difetto, il driver viene riconosciuto:

    Device EgisTec EH57E scan type changed to 'press'
    Device EgisTec EH57E enroll stages changed to 20
    Device reported probe completion (error: none)

Ma subito dopo:

    Failed to get name: net.reactivated.Fprint

`net.reactivated.Fprint` e' un nome solo, e `fprintd.service` si accende da solo
appena qualcuno chiede il servizio. La nostra copia arrivava seconda e restava
fuori. Lo script `fprintd-nostro.sh` adesso ferma il servizio, **aspetta che il
processo sia davvero sparito** (systemctl torna prima) e solo allora lancia la
nostra copia.

Scelta: fermare, non disabilitare. Chiudendo il processo la macchina torna com'era
senza altri interventi. Con SELinux in Enforcing questo evita anche di puntare un
servizio confinato a una libreria sotto `/home`.

### 13:42 — prende il nome e muore

Terzo difetto: fprintd esce dopo mezzo minuto di inattivita' e il nome torna al
servizio di sistema. Serve `-t`.

Tre difetti in tre minuti, tutti invisibili alla lettura del codice, tutti fatali.

### 15:30 — la prima iscrizione si ferma a sei su venti

Primo tentativo di `fprintd-enroll`: sei stadi passati fra le 15:31:04 e le
15:31:15, poi piu' niente. Gianluca ha appoggiato il dito una cinquantina di
volte senza che ne venisse contata una.

La macchina a stati continuava a girare a novanta fotogrammi al secondo, quindi
il sensore non si era fermato: era una delle due soglie a non scattare piu'. Ma
*quale* non si poteva dedurre, e non si potevano chiedere altre cinquanta
appoggiate al buio.

**Errore di metodo, mio:** avevo scritto un driver che decide in base a una
quantita' che non stampa mai. Aggiunta una traccia, una riga ogni mezzo secondo
con fase e distanza. Ridotto anche `G_MESSAGES_DEBUG` da `all` ai soli domini
del driver e del dispositivo: a novanta fotogrammi al secondo la macchina a
stati produceva due megabyte di log al minuto, in cui le righe che contano non
si trovavano piu'.

### 15:34 — con la traccia, l'iscrizione arriva in fondo

    traccia: fase 2 distanza 4.0 soglia 15     <- sensore libero
    traccia: fase 3 distanza 125.7 soglia 15   <- dito
    Device reported enroll progress, reported 2 of 20 have been completed

Fondo sano, soglia ben in mezzo, venti stadi in poco piu' di un minuto:

    Enroll result: enroll-completed

Impronta su disco: `/var/lib/fprint/gianlucameneghetti/egis057e/0/7`, **79957
byte** = 20 modelli x 3990 pixel piu' l'involucro GVariant. Il conto torna.

**Onesta': non so perche' il primo tentativo si sia fermato e il secondo no.**
Fra i due sono cambiate due cose, la traccia e la riduzione del log. Nessuna
delle due tocca la logica. Resta un sospetto non dimostrato sul volume di
scrittura del log; sospetto, non conclusione.

### 15:35 — verify-match

    Verify result: verify-match (done)
    Device reported verify result (result: FPI_MATCH_SUCCESS, error: none)

Il sensore dentro il tasto di accensione del Samsung autentica su Linux. Zero
successi documentati su 118 macchine, e adesso ce n'e' uno.

### 15:35 — e subito il difetto vero

Tre appoggi di verifica: **0.625, 0.595, 0.358**. Uno sotto la soglia di 0.50,
cioe' un rifiuto su tre. Gianluca lo ha descritto da solo, senza vedere i
numeri: "un po' troppo rigido, se non e' preciso non va".

Due ipotesi, tutte e due misurate invece che discusse.

**Prima: allargare lo scorrimento massimo.** Se il dito atterra dieci pixel piu'
in la', un confronto limitato a otto pixel di scorrimento non lo ritrova.
Rifatta la tabella su `matchtest`:

    scorrimento  8   genuino peggiore 0.241   impostore migliore 0.451
    scorrimento 12   genuino peggiore 0.317   impostore migliore 0.600
    scorrimento 16   genuino peggiore 0.439   impostore migliore 0.611

**Peggiora.** Alza i genuini ma alza di piu' gli impostori, perche' le creste
sono righe quasi parallele e con piu' liberta' si allineano con chiunque.
Rimesso a 8. Questa e' esattamente la modifica che avrei fatto "a naso", e i
dati l'hanno bocciata.

**Seconda: il dito viene campionato mentre sta ancora atterrando.** Il driver
prende i primi 40 fotogrammi dopo il tocco, quattro decimi di secondo in cui la
pressione sale e la pelle si appiattisce. Ipotesi mia, e sbagliata: `atterraggio.py`
confronta l'inizio di ogni appoggio con il suo centro e la sua fine, contro
modelli costruiti dagli altri appoggi, e la differenza media e' **0.015**. Rumore.

**Quello che invece si vede nei dati** e' che sullo stesso dito appoggi diversi
danno 0.816, 0.229 e 0.703 contro gli stessi modelli. Non e' *quando* tocchi,
e' **quale pezzo di polpastrello** tocca. Con quindici millimetri quadri di
finestra, due millimetri di spostamento sono un'altra parte del dito.

Conferma quello che era gia' emerso il 18/08 e che allora sembrava un dettaglio:
conta solo il numero di appoggi **distinti** (uno 0.143, due 0.288), mentre
quadruplicare i fotogrammi dello stesso appoggio non cambia niente.

Quindi: **stadi di iscrizione da 20 a 30**. Non si abbassa la soglia, perche'
0.358 sta sotto il tetto degli impostori misurato (0.451): abbassarla per far
entrare quel valore aprirebbe la porta a dita altrui.

Da misurare ancora, con dati veri e non per deduzione: se a trenta appoggi il
rifiuto resti. E gli impostori vanno rimisurati a trenta modelli, perche' piu'
modelli vogliono dire anche piu' occasioni di somigliare a qualcun altro.

### Documentazione

README rifatto: banner e figure generate da `docs/figure.py` a partire dalle
catture vere di `set-*.bin`, non da illustrazioni. Compresa quella che mostra i
tre appoggi dello stesso dito uno accanto all'altro, che rende evidente in un
colpo d'occhio perche' servono trenta iscrizioni e non venti.
