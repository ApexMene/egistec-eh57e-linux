#!/usr/bin/env python3
"""Figures for the README.

The numbers are real: the score figures come out of the driver's own log, and
matrix.png and threshold.png out of data/set-*.bin, frames that actually left
the sensor.

The fingerprints are not. Every figure that shows ridges - the banner,
sensor.png, placements.png, features.png - is drawn on a synthetic print built
by synthetic_finger() below, and says so. A fingerprint cannot be changed like
a password, so the owner's does not belong in a public repository; it was
there until 2026-11-12 and was removed from the history.

Regenerate with `python3 docs/figures.py`.
"""

import ctypes
import os
import subprocess
import tempfile

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
MUTED = "#898781"
GRID = "#21262d"
# The two series of the score figures. Checked on this background for
# lightness, chroma, contrast and colour-blind separation (worst pair 26.8).
ENROLLED = "#3987e5"
IMPOSTOR = "#d95926"

# Best score over the 30 enrolled placements, read from the driver's own log
# on 2026-11-12 (CHANGELOG.md has the session). The finger was declared before
# each series; verifications without a declared finger are not here.
SCORES_INDEX = [4859, 7118, 8782, 8907, 10640, 11904, 15505, 15636, 16016,
                16953, 24104]
SCORES_MIDDLE = [2340, 2639, 2658, 2763, 2960, 3083, 3145, 3761, 4669, 4898]
THRESHOLD = 6000

# Share of genuine comparisons scoring above the best impostor, offline, on
# data/g01-* (two fingers, three placements each, same-placement pairs
# excluded). Same source.
MATCHERS = [
    ("feature matcher\non averaged, background-free frames", 75),
    ("shifted correlation\n(the matcher until 2026-11-12)", 61),
    ("feature matcher\non raw frames", 41),
]

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


def synthetic_finger(ox=0.0, oy=0.0, seed=7, w=W, h=H):
    """A window onto a fingerprint that belongs to nobody.

    Ridges are the cosine of a phase: concentric arcs around a point below the
    window, at the 8-pixel period measured on this sensor, bent by a few slow
    sinusoids. Each arctangent term added to the phase is a dislocation, which
    in a ridge pattern is a minutia - an ending or a bifurcation.

    The finger is defined over the whole plane and (ox, oy) chooses which part
    of it the window sees, so three offsets are three placements of the same
    finger. Seeded, so the figures are reproducible.

    Returns the ridge signal alone, roughly in [-1, 1].
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    x = x + ox
    y = y + oy

    def warp():
        out = np.zeros_like(x)
        for _ in range(4):
            kx, ky = rng.uniform(-0.012, 0.012, 2)
            out += rng.uniform(3, 7) * np.sin(2 * np.pi * (kx * x + ky * y)
                                              + rng.uniform(0, 6.28))
        return out

    phase = 2 * np.pi / 8.0 * np.hypot(x - 25 + warp(), y - 120 + warp())
    for _ in range(14):
        mx, my = rng.uniform(-40, 110), rng.uniform(-40, 100)
        phase += rng.choice((-1, 1)) * np.arctan2(y - my, x - mx)
    return np.cos(phase)


def synthetic_frame(ridges, seed=1):
    """One frame as the sensor would deliver it, minus the background: the
    ridges, a pressure gradient across the window, and noise."""
    rng = np.random.default_rng(seed)
    h, w = ridges.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    pressure = 14 * np.sin(x / w * 2.1 + 0.4) * np.cos(y / h * 1.7)
    return 38 * ridges + pressure + rng.normal(0, 6, (h, w))


def fig_banner():
    """README header, on a synthetic print."""
    p = synthetic_finger(w=W * 6, h=H * 2)
    p = (p - p.min()) / (p.max() - p.min())

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.imshow(p, cmap="bone", interpolation="bilinear",
              aspect="auto", alpha=0.30)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    ax.text(0.5, 0.60, "egis057e", transform=ax.transAxes, ha="center",
            va="center", fontsize=46, color="#ffffff", family="monospace",
            weight="bold")
    ax.text(0.5, 0.30, "libfprint driver for EgisTec EH57E  \u00b7  1c7a:057e",
            transform=ax.transAxes, ha="center", va="center", fontsize=13,
            color=ACCENT, family="monospace")

    fig.tight_layout(pad=0)
    fig.savefig(f"{HERE}/banner.png", dpi=150, facecolor=BG)
    plt.close(fig)


def fig_sensor():
    """What the sensor sees: nothing, a finger, and the finger band-passed."""
    raw = synthetic_frame(synthetic_finger())

    fig, ax = plt.subplots(1, 3, figsize=(9, 2.8))
    for a, img, title in (
            (ax[0], np.zeros((H, W)), "idle sensor\n(difference from background)"),
            (ax[1], raw, "finger resting\n(difference from background)"),
            (ax[2], bandpass(raw), "after the band-pass\n(ridges remain)")):
        a.imshow(img, cmap="bone", interpolation="nearest", aspect="equal")
        a.set_title(title, fontsize=8)
        a.set_xticks([])
        a.set_yticks([])

    fig.suptitle("70 x 57 pixels = 4.3 x 3.6 mm of fingertip, about 400 dpi"
                 "  \u00b7  synthetic fingerprint",
                 fontsize=9, color=ACCENT, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(f"{HERE}/sensor.png", dpi=160, facecolor=BG)
    plt.close(fig)


def fig_placements():
    """Three placements of one finger: how much the view changes."""
    fig, ax = plt.subplots(1, 3, figsize=(9, 2.8))
    for i, (ox, oy) in enumerate(((0, 0), (31, -12), (-9, 26))):
        frame = synthetic_frame(synthetic_finger(ox, oy), seed=i)
        ax[i].imshow(bandpass(frame), cmap="bone",
                     interpolation="nearest", aspect="equal")
        ax[i].set_title(f"placement {i + 1}", fontsize=8)
        ax[i].set_xticks([])
        ax[i].set_yticks([])

    fig.suptitle("One finger, three placements, two millimetres apart"
                 "  \u00b7  synthetic fingerprint"
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


def fig_scores():
    """The two fingers on hardware: where each placement scored."""
    fig, ax = plt.subplots(figsize=(8.6, 3.0))

    for y, scores, colour in ((1, SCORES_INDEX, ENROLLED),
                              (0, SCORES_MIDDLE, IMPOSTOR)):
        # Neighbouring scores are nudged apart vertically so that no dot
        # hides another; the horizontal position is the measurement.
        last, lift = -1e9, 0
        for v in sorted(scores):
            lift = (lift + 1) % 3 if v - last < 420 else 0
            ax.plot(v, y + (lift - 1) * 0.16 * (lift > 0) + 0.16 * (lift == 1),
                    "o", ms=9, color=colour, mec=BG, mew=2, zorder=3)
            last = v

    ax.axvline(THRESHOLD, color=INK, lw=1.2, zorder=2)
    ax.text(THRESHOLD + 250, 1.62, f"threshold {THRESHOLD}", fontsize=8,
            color=INK, va="center")
    ax.annotate("4898\nbest impostor", (4898, 0), (4898, -0.72), fontsize=7.5,
                color=MUTED, ha="center", va="top",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.annotate("4859\nthe one rejected", (4859, 1), (2900, 1.42), fontsize=7.5,
                color=MUTED, ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    ax.set_yticks([1, 0])
    ax.set_yticklabels(["right index\nenrolled · 11 placements",
                        "right middle\nnot enrolled · 10 placements"],
                       fontsize=8)
    ax.set_ylim(-1.25, 1.85)
    ax.set_xlim(0, 25500)
    ax.set_xlabel("best score over the 30 enrolled placements")
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_title("On hardware: 10 of 11 genuine placements accepted, "
                 "0 of 10 impostor placements", fontsize=9, color=ACCENT)
    fig.tight_layout()
    fig.savefig(f"{HERE}/scores.png", dpi=160, facecolor=BG)
    plt.close(fig)


def fig_matchers():
    """Offline comparison of the three ways of scoring the same captures."""
    fig, ax = plt.subplots(figsize=(8.6, 2.5))
    names = [m[0] for m in MATCHERS][::-1]
    values = [m[1] for m in MATCHERS][::-1]

    ax.barh(range(len(values)), values, height=0.42, color=ENROLLED)
    for i, v in enumerate(values):
        ax.text(v + 1.2, i, f"{v}%", va="center", fontsize=9, color=INK)

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("genuine comparisons scoring above the best impostor")
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_title("Same captures, three matchers: the gain is in the pairing",
                 fontsize=9, color=ACCENT)
    fig.tight_layout()
    fig.savefig(f"{HERE}/matchers.png", dpi=160, facecolor=BG)
    plt.close(fig)


class _Feature(ctypes.Structure):
    _fields_ = [("x", ctypes.c_uint16), ("y", ctypes.c_uint16),
                ("orient", ctypes.c_uint8), ("bucket", ctypes.c_uint8),
                ("polarity", ctypes.c_uint8), ("angle", ctypes.c_uint16),
                ("desc", ctypes.c_uint8 * 64)]


class _FeatureSet(ctypes.Structure):
    _fields_ = [("n", ctypes.c_int), ("f", _Feature * 512),
                ("chan_w", ctypes.c_int), ("chan_h", ctypes.c_int),
                ("chan_sm", ctypes.c_void_p), ("chan_ix", ctypes.c_void_p),
                ("chan_iy", ctypes.c_void_p)]


def driver_features(image):
    """Interest points of an 8-bit image, from the driver's own matcher.

    driver/egis057e-matcher.c is compiled as it is into a throwaway shared
    object and called directly, so the figure shows what the driver computes
    and not a Python lookalike of it.
    """
    with tempfile.TemporaryDirectory() as tmp:
        so = os.path.join(tmp, "matcher.so")
        subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", so,
                        os.path.join(ROOT, "driver", "egis057e-matcher.c"),
                        "-lm"], check=True)
        lib = ctypes.CDLL(so)
        fs = _FeatureSet()
        buf = (ctypes.c_uint8 * (W * H)).from_buffer_copy(image.tobytes())
        lib.egis057e_m_extract(buf, W, H, ctypes.byref(fs))
        sx, sy = W / fs.chan_w, H / fs.chan_h
        pts = [(fs.f[i].x * sx, fs.f[i].y * sy, fs.f[i].angle)
               for i in range(fs.n)]
        lib.egis057e_m_feature_set_clear(ctypes.byref(fs))
    return pts


def fig_features():
    """What the matcher is given and what it finds - on a synthetic print.

    The one figure here that is not a capture: a real placement with its
    interest points drawn on it is a fingerprint published with its own
    template. The points are still computed by the driver's matcher.
    """
    ridges = synthetic_finger()
    avg = 38 * ridges
    raw = 110 + synthetic_frame(ridges)

    # What make_image() does in the driver once the frames are averaged and
    # the background is gone: mean 128 and deviation 40, eight bits.
    img = np.clip(np.rint((avg - avg.mean()) / avg.std() * 40 + 128), 0, 255)
    img = img.astype(np.uint8)
    pts = driver_features(img)

    fig, ax = plt.subplots(1, 3, figsize=(9, 3.0))
    ax[0].imshow(raw, cmap="bone", interpolation="nearest", vmin=0, vmax=255)
    ax[0].set_title("one raw frame", fontsize=8)
    ax[1].imshow(img, cmap="bone", interpolation="nearest", vmin=0, vmax=255)
    ax[1].set_title("frames averaged,\nbackground removed, level fixed",
                    fontsize=8)
    ax[2].imshow(img, cmap="bone", interpolation="nearest", vmin=0, vmax=255,
                 alpha=0.55)
    for x, y, ang in pts:
        t = np.deg2rad(ang)
        ax[2].plot([x, x + 2.2 * np.cos(t)], [y, y + 2.2 * np.sin(t)],
                   color=ENROLLED, lw=0.8, alpha=0.9)
    ax[2].plot([p[0] for p in pts], [p[1] for p in pts], "o", ms=2.2,
               color=ENROLLED, mec="none")
    ax[2].set_title(f"{len(pts)} interest points,\neach with its orientation",
                    fontsize=8)
    for a_ in ax:
        a_.set_xlim(-0.5, W - 0.5)
        a_.set_ylim(H - 0.5, -0.5)
        a_.set_xticks([])
        a_.set_yticks([])

    fig.suptitle("What the matcher is given, and what it finds in 15 mm² of "
                 "skin  ·  synthetic fingerprint, real matcher",
                 fontsize=9, color=ACCENT, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(f"{HERE}/features.png", dpi=160, facecolor=BG)
    plt.close(fig)


def main():
    bg = background()
    fig_banner()
    fig_sensor()
    fig_placements()
    fig_matrix()
    fig_threshold(bg)
    fig_scores()
    fig_matchers()
    fig_features()
    print("wrote banner.png, sensor.png, placements.png, matrix.png, "
          "threshold.png, scores.png, matchers.png, features.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
