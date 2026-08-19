#!/usr/bin/env python3
"""Figures for the README, generated from the real captures.

Nothing here is an illustration: every image comes out of data/set-*.bin, that
is, out of frames that actually left the sensor. Regenerate with
`python3 docs/figures.py`.
"""

import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

W, H = 70, 57
FINGERS = ["indice-dx", "medio-dx", "anulare-dx", "pollice-dx", "indice-sx"]
LABELS = ["R index", "R middle", "R ring", "R thumb", "L index"]

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

INK = "#e6e6e6"
BG = "#0d1117"
ACCENT = "#58a6ff"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.edgecolor": "#30363d",
    "font.size": 9,
})


def background():
    return np.fromfile(f"{DATA}/set-fondo.bin",
                       dtype=np.uint8).astype(np.float64).reshape(H, W)


def placement(finger, n, bg, threshold=25.0):
    a = np.fromfile(f"{DATA}/set-{finger}-{n}.bin", dtype=np.uint8)
    f = a[:len(a) // (W * H) * (W * H)].reshape(-1, H, W).astype(np.float64) - bg
    return f[np.abs(f).mean(axis=(1, 2)) > threshold]


def bandpass(p):
    """The driver's band: centred on 0.125 cycles/pixel, the ridge period
    measured on this sensor."""
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.fftfreq(W)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    band = np.exp(-((r - 0.125) ** 2) / (2 * 0.045 ** 2))
    return np.fft.ifft2(np.fft.fft2(p - p.mean()) * band).real


def fig_banner(bg):
    """README header.

    The backdrop is a real placement, tiled: it is the finger that made this
    work, not a texture from somewhere else.
    """
    f = placement("indice-dx", 1, bg)
    p = bandpass(f[len(f) // 2])
    p = (p - p.min()) / (p.max() - p.min())

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.imshow(np.tile(p, (2, 6)), cmap="bone", interpolation="bilinear",
              aspect="auto", alpha=0.30)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    ax.text(0.5, 0.60, "egis057e", transform=ax.transAxes, ha="center",
            va="center", fontsize=46, color="#ffffff", family="monospace",
            weight="bold")
    ax.text(0.5, 0.30, "libfprint driver for EgisTec EH57E  ·  1c7a:057e",
            transform=ax.transAxes, ha="center", va="center", fontsize=13,
            color=ACCENT, family="monospace")

    fig.tight_layout(pad=0)
    fig.savefig(f"{HERE}/banner.png", dpi=150, facecolor=BG)
    plt.close(fig)


def fig_sensor(bg):
    """What the sensor sees: nothing, a finger, and the finger band-passed."""
    f = placement("indice-dx", 1, bg)
    raw = f[len(f) // 2]

    fig, ax = plt.subplots(1, 3, figsize=(9, 2.8))
    for a, img, title in (
            (ax[0], np.zeros((H, W)), "idle sensor\n(difference from background)"),
            (ax[1], raw, "finger resting\n(difference from background)"),
            (ax[2], bandpass(raw), "after the band-pass\n(ridges remain)")):
        a.imshow(img, cmap="bone", interpolation="nearest", aspect="equal")
        a.set_title(title, fontsize=8)
        a.set_xticks([])
        a.set_yticks([])

    fig.suptitle("70 x 57 pixels = 4.3 x 3.6 mm of fingertip, about 400 dpi",
                 fontsize=9, color=ACCENT, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(f"{HERE}/sensor.png", dpi=160, facecolor=BG)
    plt.close(fig)


def fig_placements(bg):
    """Three placements of one finger: how much the view changes."""
    fig, ax = plt.subplots(1, 3, figsize=(9, 2.8))
    for i, n in enumerate((1, 2, 3)):
        f = placement("anulare-dx", n, bg)
        ax[i].imshow(bandpass(f[len(f) // 2]), cmap="bone",
                     interpolation="nearest", aspect="equal")
        ax[i].set_title(f"placement {n}", fontsize=8)
        ax[i].set_xticks([])
        ax[i].set_yticks([])

    fig.suptitle("One finger, three placements, scoring 0.816 / 0.229 / 0.703."
                 "\nThe finger does not change; which part of it touches does.",
                 fontsize=9, color=ACCENT, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.savefig(f"{HERE}/placements.png", dpi=160, facecolor=BG)
    plt.close(fig)


def fig_matrix():
    """The measured score matrix: the diagonal is the same finger."""
    m = np.array([
        [0.481, 0.451, 0.221, 0.173, 0.260],
        [0.355, 0.608, 0.446, 0.131, 0.264],
        [0.158, 0.435, 0.767, 0.131, 0.373],
        [0.070, 0.077, 0.141, 0.729, 0.065],
        [0.324, 0.109, 0.347, 0.268, 0.241],
    ])

    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(m, cmap="magma", vmin=0, vmax=0.8)

    ax.set_xticks(range(5), LABELS, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(5), LABELS, fontsize=8)
    ax.set_xlabel("finger presented")
    ax.set_ylabel("finger enrolled")

    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if m[i, j] < 0.5 else "black",
                    weight="bold" if i == j else "normal")

    ax.set_title("Correlation, enrolling two placements and verifying with the third",
                 fontsize=9, color=ACCENT, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(f"{HERE}/matrix.png", dpi=160, facecolor=BG)
    plt.close(fig)


def fig_threshold(bg):
    """Finger against idle sensor: why the presence threshold sits at 15."""
    idle, finger = [], []
    for d in FINGERS:
        for n in (1, 2, 3):
            a = np.fromfile(f"{DATA}/set-{d}-{n}.bin", dtype=np.uint8)
            f = a[:len(a) // (W * H) * (W * H)]
            f = f.reshape(-1, H, W).astype(np.float64) - bg
            dist = np.abs(f).mean(axis=(1, 2))
            idle += list(dist[dist <= 25])
            finger += list(dist[dist > 25])

    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    ax.hist(idle, bins=60, range=(0, 140), color="#7d8590", label="idle sensor")
    ax.hist(finger, bins=60, range=(0, 140), color=ACCENT, label="finger resting")
    ax.axvline(15, color="#f85149", lw=2, label="driver threshold (15)")
    ax.set_xlabel("mean absolute distance from background, per pixel")
    ax.set_ylabel("frames")
    ax.legend(fontsize=8, facecolor=BG, edgecolor="#30363d", labelcolor=INK)
    ax.set_title("Finger detection: two populations that do not touch",
                 fontsize=9, color=ACCENT)
    fig.tight_layout()
    fig.savefig(f"{HERE}/threshold.png", dpi=160, facecolor=BG)
    plt.close(fig)


def main():
    bg = background()
    fig_banner(bg)
    fig_sensor(bg)
    fig_placements(bg)
    fig_matrix()
    fig_threshold(bg)
    print("wrote banner.png, sensor.png, placements.png, matrix.png, threshold.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
