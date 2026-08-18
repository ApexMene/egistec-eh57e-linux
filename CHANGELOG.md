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

