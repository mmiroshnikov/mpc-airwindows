#!/usr/bin/env python3
"""Cosmic backdrops for the Airwindows ports: acrylic-pour nebula, stars, glitter and (some) a wireframe.

    tools/aw_backdrop.py NAME -o out.png          one 1280x628 backdrop
    tools/aw_backdrop.py --all -o dir/            one per ports/*/ (plus Galactic)

Each plugin gets its own palette (PALETTES, picked by name) and its own random seed, so a rebuild draws the
same picture. Needs numpy and Pillow.
"""
import argparse
import math
import os
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1280, 628
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (deep, mid, light, sparkle) RGB; deep is the near-black base, light the brightest pour veins
PALETTES = {
    "indigo":   ((6, 8, 20), (52, 66, 128), (184, 196, 238), (255, 214, 140)),
    "teal":     ((3, 12, 16), (30, 96, 112), (150, 220, 222), (190, 240, 255)),
    "violet":   ((10, 6, 20), (86, 52, 140), (214, 184, 246), (255, 200, 240)),
    "gold":     ((8, 9, 16), (54, 64, 92), (150, 164, 196), (255, 186, 90)),
    "magenta":  ((16, 4, 14), (130, 36, 104), (246, 170, 214), (255, 220, 160)),
    "emerald":  ((3, 12, 9), (26, 100, 74), (150, 230, 190), (220, 255, 200)),
    "crimson":  ((16, 4, 6), (128, 34, 44), (238, 166, 150), (255, 200, 120)),
    "steel":    ((8, 9, 12), (62, 70, 88), (168, 176, 196), (210, 230, 255)),
    "cobalt":   ((2, 6, 22), (24, 62, 160), (150, 190, 255), (255, 255, 255)),
    "amber":    ((14, 8, 4), (120, 72, 30), (246, 204, 150), (255, 230, 170)),
    "aurora":   ((3, 10, 16), (34, 110, 120), (180, 160, 240), (180, 255, 210)),
    "rose":     ((14, 6, 12), (120, 64, 96), (240, 196, 216), (255, 240, 220)),
}
ORDER = list(PALETTES)
# fixed picks so neighbours in the plugin list don't share a colour; anything else hashes into ORDER
PICK = {
    "kAlienSpaceship": "aurora", "kCosmos": "violet", "kCathedral5": "gold", "Galactic": "indigo",
    "Galactic2": "cobalt", "Galactic3": "magenta", "GalacticVibe": "teal", "Infinity2": "steel",
    "MatrixVerb": "emerald", "Verbity2": "rose", "Chamber2": "amber", "PitchDelay": "crimson",
    "TapeDelay2": "amber", "ChorusEnsemble": "aurora", "Air3": "teal", "ButterComp2": "gold",
    "Console7Channel": "steel", "Density2": "crimson", "ToVinyl4": "rose", "ZAcidLowpass": "emerald",
    "ZLowpass2": "cobalt",
}
WIREFRAME = {"kAlienSpaceship": "tunnel", "kCosmos": "sphere", "Galactic": "sphere", "Galactic2": "tunnel",
             "Galactic3": "grid", "GalacticVibe": "sphere", "Infinity2": "tunnel", "ZAcidLowpass": "grid"}


def palette_for(name):
    return PALETTES[PICK.get(name) or ORDER[zlib.crc32(name.encode()) % len(ORDER)]]


def octave(rng, res, w=W, h=H):
    """One layer of smooth value noise: a random res-wide grid scaled up bicubically, 0..1."""
    rh = max(2, int(res * h / w))
    g = (rng.random((rh, res)) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0


def fbm(rng, base=3, octaves=6, gain=0.55, w=W, h=H):
    out, amp, tot = np.zeros((h, w), np.float32), 1.0, 0.0
    for o in range(octaves):
        out += amp * octave(rng, base * 2 ** o, w, h)
        tot += amp
        amp *= gain
    return out / tot


def reflect(v, n):
    v = np.mod(v, 2 * (n - 1))
    return np.where(v > n - 1, 2 * (n - 1) - v, v)


def sample(img, x, y):
    """Bilinear lookup of img at float pixel coords, mirrored at the edges (no smeared borders)."""
    h, w = img.shape
    x = np.minimum(reflect(x, w), w - 1.001)
    y = np.minimum(reflect(y, h), h - 1.001)
    x0, y0 = x.astype(np.int32), y.astype(np.int32)
    fx, fy = x - x0, y - y0
    a, b = img[y0, x0], img[y0, x0 + 1]
    c, d = img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def lerp3(a, b, t):
    a, b = np.array(a, np.float32), np.array(b, np.float32)
    return a + (b - a) * t[..., None]


def pour(rng, pal):
    """Nested domain warping (f(p + fbm(p + fbm(p)))): swirling bands with thin bright veins, like an acrylic pour."""
    deep, mid, light, _ = pal
    w, h = W // 2, H // 2   # the fluid is smooth: work at half size, scale up at the end
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s = w * 0.30            # warp strength in (half-size) pixels
    n = [fbm(rng, 2, 5, 0.42, w, h) for _ in range(5)]
    qx, qy = n[0] - 0.5, n[1] - 0.5
    rx = sample(n[2], xx + 4 * s * qx, yy + 4 * s * qy) - 0.5
    ry = sample(n[3], xx + 4 * s * qx + 37, yy + 4 * s * qy + 91) - 0.5
    f = sample(n[4], xx + 4 * s * rx, yy + 4 * s * ry)
    stripes = 0.5 + 0.5 * np.sin((f * 5.0 + np.hypot(rx, ry) * 6.0) * math.pi * 2)   # pour bands
    veins = np.clip(1 - np.abs(np.sin((f * 11.0 + rx * 3) * math.pi)) * 7, 0, 1) ** 2   # thin bright lines
    paint = np.clip((f - np.quantile(f, 0.32)) * 3.2, 0, 1)                                              # dark space vs paint
    t = paint * (0.35 + 0.65 * stripes)
    col = lerp3(deep, mid, np.clip(t * 1.3, 0, 1))
    col = col + (np.array(light, np.float32) - col) * (np.clip(t - 0.55, 0, 1) * 1.8 * paint)[..., None]
    col = col + (np.array(light, np.float32) - col) * (veins * paint * 0.55)[..., None]
    big = lambda a: np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                               np.float32)
    col = np.dstack([big(col[..., c]) for c in range(3)])
    paint = big(paint * 255) / 255.0
    # cells: a sparse sprinkle of round dark holes and pale dots on the paint
    cells = np.asarray(Image.fromarray((octave(rng, 300) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)),
                       np.float32) / 255.0
    cells = (cells - cells.mean()) / (cells.std() * 6) + 0.5
    holes = np.clip((cells - 0.86) * 20, 0, 1) * paint
    dots = np.clip((0.12 - cells) * 20, 0, 1) * paint
    col = col * (1 - holes[..., None] * 0.7)
    col = col + (np.array(light, np.float32) - col) * (dots * 0.6)[..., None]
    lum = col @ np.array([0.3, 0.55, 0.15], np.float32)
    col = col * float(np.clip(205.0 / max(np.quantile(lum, 0.97), 1), 0.7, 2.2))   # same brightness for every palette
    return col, paint


def stars(rng, img, pal, density):
    """Point stars everywhere, glitter clusters along the paint, a few glowing bright stars."""
    sparkle = np.array(pal[3], np.float32)
    glow = np.zeros((H, W, 3), np.float32)
    n = 1400
    xs, ys = rng.integers(0, W, n), rng.integers(0, H, n)
    br = rng.random(n) ** 3
    for x, y, b in zip(xs, ys, br):
        glow[y, x] += 255 * (0.25 + 0.75 * b)
    # glitter: dense specks weighted by where the paint is
    m = 4500
    gx, gy = rng.integers(0, W, m), rng.integers(0, H, m)
    keep = rng.random(m) < density[gy, gx] ** 1.5 * 0.9
    for x, y in zip(gx[keep], gy[keep]):
        glow[y, x] += sparkle * (0.4 + 0.6 * rng.random())
    soft = np.asarray(Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)),
                      np.float32)
    img = img + glow * 0.8 + soft * 1.6
    # a few big stars with halos and a cross flare
    big = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(big)
    for _ in range(int(rng.integers(5, 9))):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        c = tuple(int(v) for v in (sparkle * 0.5 + 255 * 0.5))
        r = int(rng.integers(1, 3))
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        L = int(rng.integers(8, 18))
        d.line([x - L, y, x + L, y], fill=tuple(v // 2 for v in c))
        d.line([x, y - L, x, y + L], fill=tuple(v // 2 for v in c))
    halo = np.asarray(big.filter(ImageFilter.GaussianBlur(4)), np.float32)
    return img + np.asarray(big, np.float32) + halo * 2.5


def wireframe(kind, rng, pal):
    """Thin white line art from the references: a perspective tunnel, a globe, or a receding floor grid."""
    layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(layer)
    cx, cy = int(W * (0.62 + rng.random() * 0.25)), int(H * (0.35 + rng.random() * 0.3))
    if kind == "tunnel":
        for i in range(1, 15):
            r = 300 * (1 - i / 15) ** 1.6 + 6
            d.ellipse([cx - r * 1.25, cy - r, cx + r * 1.25, cy + r], outline=150)
        for k in range(24):
            a = k / 24 * 2 * math.pi
            d.line([cx + 8 * math.cos(a), cy + 6 * math.sin(a), cx + 380 * math.cos(a), cy + 300 * math.sin(a)], fill=110)
    elif kind == "sphere":
        R = int(150 + rng.random() * 60)
        tilt = 0.35
        for lat in range(-75, 90, 15):
            y = cy - R * math.sin(math.radians(lat))
            rx = R * math.cos(math.radians(lat))
            d.ellipse([cx - rx, y - rx * tilt * 0.3, cx + rx, y + rx * tilt * 0.3], outline=140)
        for lon in range(0, 180, 15):
            rx = abs(R * math.cos(math.radians(lon)))
            d.ellipse([cx - rx, cy - R, cx + rx, cy + R], outline=140)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=180, width=2)
    else:   # floor grid receding to a horizon
        hy = int(H * 0.42)
        for i in range(-16, 17):
            d.line([W / 2 + i * 26, hy, W / 2 + i * 190, H], fill=110)
        for j in range(1, 12):
            y = hy + (H - hy) * (j / 12) ** 2.2
            d.line([0, y, W, y], fill=110)
    a = np.asarray(layer, np.float32) / 255.0
    a = a * 0.55 + np.asarray(layer.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255.0 * 0.6
    return a


def backdrop(name):
    rng = np.random.default_rng(zlib.crc32(("aw-backdrop-" + name).encode()))
    pal = palette_for(name)
    img, density = pour(rng, pal)
    img = stars(rng, img, pal, density)
    if name in WIREFRAME:
        a = wireframe(WIREFRAME[name], rng, pal)[..., None]
        img = img + (np.array([235, 240, 255], np.float32) - img) * np.clip(a, 0, 1) * 0.35
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = ((xx / W - 0.5) ** 2 * 1.2 + (yy / H - 0.5) ** 2 * 1.6)
    img = img * np.clip(1.08 - v * 1.1, 0.35, 1.0)[..., None]   # vignette
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def all_names():
    names = sorted(os.listdir(os.path.join(HERE, "ports")))
    return names + ["Galactic"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    if a.all:
        os.makedirs(a.o, exist_ok=True)
        for n in all_names():
            backdrop(n).save(os.path.join(a.o, n + ".png"))
            print(n, PICK.get(n), WIREFRAME.get(n, ""))
    elif a.name:
        backdrop(a.name).save(a.o)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
