#!/usr/bin/env python3
"""Le figure del README, generate dalle catture vere.

Niente illustrazioni: ogni immagine qui esce da set-*.bin, cioe' dai fotogrammi
usciti davvero dal sensore. Rigenerabile con `python3 docs/figure.py`.
"""

import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

W, H = 70, 57
DITA = ["indice-dx", "medio-dx", "anulare-dx", "pollice-dx", "indice-sx"]
QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
DATI = os.path.join(RADICE, "data")

INCHIOSTRO = "#e6e6e6"
FONDO = "#0d1117"
ACCENTO = "#58a6ff"

plt.rcParams.update({
    "figure.facecolor": FONDO,
    "axes.facecolor": FONDO,
    "text.color": INCHIOSTRO,
    "axes.labelcolor": INCHIOSTRO,
    "xtick.color": INCHIOSTRO,
    "ytick.color": INCHIOSTRO,
    "axes.edgecolor": "#30363d",
    "font.size": 9,
})


def fondo():
    return np.fromfile(f"{DATI}/set-fondo.bin",
                       dtype=np.uint8).astype(np.float64).reshape(H, W)


def appoggio(nome, n, bg, soglia=25.0):
    a = np.fromfile(f"{DATI}/set-{nome}-{n}.bin", dtype=np.uint8)
    f = a[:len(a) // (W * H) * (W * H)].reshape(-1, H, W).astype(np.float64) - bg
    return f[np.abs(f).mean(axis=(1, 2)) > soglia]


def passabanda(p):
    """Stessa banda del driver: attorno a 0.125 cicli/pixel, il periodo delle
    creste misurato su questo sensore."""
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.fftfreq(W)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    banda = np.exp(-((r - 0.125) ** 2) / (2 * 0.045 ** 2))
    return np.fft.ifft2(np.fft.fft2(p - p.mean()) * banda).real


def fig_sensore(bg):
    """Cosa vede il sensore: niente, un dito, e il dito dopo il passabanda."""
    f = appoggio("indice-dx", 1, bg)
    grezzo = f[len(f) // 2]
    filtrato = passabanda(grezzo)

    fig, ax = plt.subplots(1, 3, figsize=(9, 2.8))
    for a, img, tit in (
            (ax[0], np.zeros((H, W)), "sensore libero\n(differenza dal fondo)"),
            (ax[1], grezzo, "dito appoggiato\n(differenza dal fondo)"),
            (ax[2], filtrato, "dopo il passabanda\n(restano le creste)")):
        a.imshow(img, cmap="bone", interpolation="nearest", aspect="equal")
        a.set_title(tit, fontsize=8)
        a.set_xticks([])
        a.set_yticks([])

    fig.suptitle("70 x 57 pixel = 4.3 x 3.6 mm di polpastrello, circa 400 dpi",
                 fontsize=9, color=ACCENTO, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(f"{QUI}/sensore.png", dpi=160, facecolor=FONDO)
    plt.close(fig)


def fig_appoggi(bg):
    """Tre appoggi dello stesso dito: quanto cambia quello che si vede."""
    fig, ax = plt.subplots(1, 3, figsize=(9, 2.8))
    for i, n in enumerate((1, 2, 3)):
        f = appoggio("anulare-dx", n, bg)
        ax[i].imshow(passabanda(f[len(f) // 2]), cmap="bone",
                     interpolation="nearest", aspect="equal")
        ax[i].set_title(f"appoggio {n}", fontsize=8)
        ax[i].set_xticks([])
        ax[i].set_yticks([])

    fig.suptitle("Stesso dito, tre appoggi: 0.816 / 0.229 / 0.703 di "
                 "somiglianza.\nNon cambia il dito, cambia quale pezzo tocca.",
                 fontsize=9, color=ACCENTO, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.savefig(f"{QUI}/appoggi.png", dpi=160, facecolor=FONDO)
    plt.close(fig)


def fig_matrice():
    """La matrice dei punteggi misurata: diagonale = stesso dito."""
    m = np.array([
        [0.481, 0.451, 0.221, 0.173, 0.260],
        [0.355, 0.608, 0.446, 0.131, 0.264],
        [0.158, 0.435, 0.767, 0.131, 0.373],
        [0.070, 0.077, 0.141, 0.729, 0.065],
        [0.324, 0.109, 0.347, 0.268, 0.241],
    ])

    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(m, cmap="magma", vmin=0, vmax=0.8)

    ax.set_xticks(range(5), DITA, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(5), DITA, fontsize=8)
    ax.set_xlabel("dito presentato")
    ax.set_ylabel("dito iscritto")

    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center",
                    fontsize=8,
                    color="white" if m[i, j] < 0.5 else "black",
                    weight="bold" if i == j else "normal")

    ax.set_title("Correlazione, iscrivendo due appoggi e verificando col terzo",
                 fontsize=9, color=ACCENTO, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(f"{QUI}/matrice.png", dpi=160, facecolor=FONDO)
    plt.close(fig)


def fig_soglia(bg):
    """Dito contro sensore libero: perche' la soglia di presenza sta a 15."""
    libero, dito = [], []
    for d in DITA:
        for n in (1, 2, 3):
            a = np.fromfile(f"{DATI}/set-{d}-{n}.bin", dtype=np.uint8)
            f = a[:len(a) // (W * H) * (W * H)]
            f = f.reshape(-1, H, W).astype(np.float64) - bg
            dist = np.abs(f).mean(axis=(1, 2))
            libero += list(dist[dist <= 25])
            dito += list(dist[dist > 25])

    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    ax.hist(libero, bins=60, range=(0, 140), color="#7d8590",
            label="sensore libero")
    ax.hist(dito, bins=60, range=(0, 140), color=ACCENTO, label="dito appoggiato")
    ax.axvline(15, color="#f85149", lw=2, label="soglia del driver (15)")
    ax.set_xlabel("distanza media dal fondo, per pixel")
    ax.set_ylabel("fotogrammi")
    ax.legend(fontsize=8, facecolor=FONDO, edgecolor="#30363d",
              labelcolor=INCHIOSTRO)
    ax.set_title("Rilevamento del dito: due popolazioni che non si toccano",
                 fontsize=9, color=ACCENTO)
    fig.tight_layout()
    fig.savefig(f"{QUI}/soglia.png", dpi=160, facecolor=FONDO)
    plt.close(fig)


def fig_banner(bg):
    """Testata del README.

    Lo sfondo e' un appoggio vero ingrandito e affiancato a se stesso: e' il
    dito che ha fatto funzionare la cosa, non una texture presa altrove.
    """
    f = appoggio("indice-dx", 1, bg)
    p = passabanda(f[len(f) // 2])
    p = (p - p.min()) / (p.max() - p.min())
    tela = np.tile(p, (2, 6))

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.imshow(tela, cmap="bone", interpolation="bilinear", aspect="auto",
              alpha=0.30)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    ax.text(0.5, 0.60, "egis057e", transform=ax.transAxes, ha="center",
            va="center", fontsize=46, color="#ffffff", family="monospace",
            weight="bold")
    ax.text(0.5, 0.30, "driver libfprint per EgisTec EH57E  ·  1c7a:057e",
            transform=ax.transAxes, ha="center", va="center", fontsize=13,
            color=ACCENTO, family="monospace")

    fig.tight_layout(pad=0)
    fig.savefig(f"{QUI}/banner.png", dpi=150, facecolor=FONDO)
    plt.close(fig)


def main():
    bg = fondo()
    fig_banner(bg)
    fig_sensore(bg)
    fig_appoggi(bg)
    fig_matrice()
    fig_soglia(bg)
    print("scritte docs/sensore.png, appoggi.png, matrice.png, soglia.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
