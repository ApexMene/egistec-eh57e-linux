# Piano — far funzionare EgisTec EH57E (1c7a:057e) su Fedora 44

Obiettivo: sblocco con impronta (GDM + `sudo`) sul Samsung Galaxy Book Pro.

Strategia: **non** partire da reverse engineering da zero. Il sensore è un Egis
Match-on-Chip della stessa famiglia dei `1c7a:0582/0584/05a5` già supportati dal fork
`egismoc`. Ipotesi: stesso protocollo, endpoint diversi. Si verifica in 15 minuti.

---

## FASE 0 — Setup ambiente (~10 min)

Serve la tua password una volta sola.

```bash
sudo dnf install -y python3-pyusb python3-docopt wireshark-cli \
                    meson ninja-build gcc glib2-devel libgusb-devel \
                    nss-devel libgudev-devel gtk-doc cairo-devel \
                    gobject-introspection-devel pixman-devel systemd-devel
sudo modprobe usbmon
```

Regola udev per non dover girare tutto da root:

```
# /etc/udev/rules.d/60-egis-fingerprint.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="1c7a", ATTRS{idProduct}=="057e", MODE="0660", TAG+="uaccess"
```

**Esito atteso:** `python3 -c "import usb"` senza errori.

---

## FASE 1 — Il momento della verità (~20 min) ⭐

Adattare il PoC di Grisham al nostro device: cambiare `idProduct` a `0x057e` e gli
endpoint a `OUT 0x01 / IN 0x82`, poi mandare il comando `info`.

```bash
python3 egismoc-057e.py info
```

**Cosa guardiamo:** se la risposta inizia con `SIGE\x00\x00\x00\x01`.

| Risposta | Significato | Dove si va |
|---|---|---|
| Prefisso `SIGE` valido | Stesso protocollo. **Grande.** | → Fase 2 |
| Byte diversi ma risposta presente | Protocollo variante, RE mirato fattibile | → Fase 2b |
| Timeout / pipe error | Init sequence diversa | → Fase 4 |

Se il device risponde, **stasera si arriva in fondo**.

### Fase 2b — variante protocollo
Fuzzing controllato dei type/subtype byte + confronto con le sequenze note dei fratelli
`0582`/`0584`/`05a5`. Sniffare in parallelo con `usbmon` per vedere cosa risponde davvero.

---

## FASE 2 — Enroll via PoC Python (~20 min)

```bash
python3 egismoc-057e.py enroll   # 10 tocchi
python3 egismoc-057e.py verify
```

Conferma che enroll+match funzionano prima di toccare libfprint. Isola i problemi.

---

## FASE 3 — Portare in libfprint (~40 min)

Il fork è già clonato e già patchato (`libfprint-egismoc-sdcp/`, modifiche non committate).

1. Committare la patch `057e` su un branch dedicato.
2. Correggere gli endpoint **per-device** (non globalmente — l'attuale patch rompe gli altri modelli):
   usare un flag `driver_data` tipo `EGISMOC_DRIVER_ALT_ENDPOINTS`.
3. Build:
   ```bash
   meson setup builddir && meson compile -C builddir
   sudo ./builddir/examples/enroll        # test diretto, senza fprintd
   ```
4. Se ok → `sudo meson install`, poi fprintd con debug:
   ```bash
   sudo systemctl edit fprintd.service   # Environment=G_MESSAGES_DEBUG=all
   fprintd-enroll -f right-index-finger
   ```
5. PAM: `sudo authselect enable-feature with-fingerprint`

**Attenzione persistenza:** un `dnf update` di `libfprint` sovrascrive di nuovo la build
manuale (già successo l'11/08). Soluzione: `sudo dnf versionlock add libfprint` oppure
pacchettizzare la build in un RPM locale. Da decidere a fine serata.

---

## FASE 4 — Fallback: reverse engineering vero (se Fase 1 fallisce)

Solo se il sensore non parla il protocollo Egis noto.

1. VM Windows in QEMU/KVM (`/dev/kvm` OK, `qemu-kvm` e `virt-manager` già installati),
   USB passthrough del device `1c7a:057e`.
2. Installare il driver Samsung originale (**CanvasBio**) dentro la VM.
3. Enroll reale in Windows Hello mentre `usbmon` + `tshark` catturano dall'host.
4. Analisi pcapng → estrarre init sequence, comandi, checksum.
5. Riscrivere il PoC Python sulla sequenza reale → poi Fase 3.

Costo realistico: non una serata. Ma diventa necessario solo nello scenario peggiore.

---

## Rischi

- **Nessun rischio di brick**: il sensore è MoC, si comunica solo via bulk USB. Al massimo
  non risponde e si stacca/riattacca via USB reset.
- Build libfprint installata a mano può rompere l'autenticazione **se PAM viene configurato
  male** → non toccare PAM finché `fprintd-enroll` non funziona, e tenere un terminale root
  aperto durante i test.
- `authselect` va cambiato solo a fine, con rollback pronto (`authselect disable-feature`).
</content>
</invoke>
