"""Génère presets/Lumineux_Punchy.cube, un LUT 3D (33 points) qui reproduit
approximativement le preset Lightroom Lumineux_Punchy.xmp.

Le LUT ne couvre que la couleur et la tonalité. Texture, clarté, netteté et
réduction du bruit ne peuvent pas tenir dans un LUT.

Usage :
    python3 outils/generer_lut.py                  # écrit le .cube
    python3 outils/generer_lut.py photo.jpg out.jpg  # applique aussi le rendu à une photo
"""
import sys
from pathlib import Path

import numpy as np

TAILLE = 33
RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "presets" / "Lumineux_Punchy.cube"

# Réglages (mêmes valeurs que le .xmp)
EXPOSITION = 0.40
CONTRASTE = 15
HAUTES_LUMIERES = -20
OMBRES = 10
BLANCS = 25
NOIRS = -15
VIBRANCE = 20
SATURATION = 5
# TSL : (teinte, saturation, luminance) par couleur, centre de teinte en degrés
TSL = {
    "rouge":   (0,   (0, 0, 0)),
    "orange":  (30,  (0, 10, 10)),
    "jaune":   (60,  (-5, 5, 5)),
    "vert":    (120, (0, -20, 0)),
    "aqua":    (180, (-5, 10, 0)),
    "bleu":    (225, (-5, 30 + 15, -5)),  # +15 : étalonnage primaire bleu
    "violet":  (270, (0, -10, 0)),
    "magenta": (315, (0, -10, 0)),
}
OMBRES_TEINTE, OMBRES_SAT = 220, 8
HL_TEINTE, HL_SAT = 45, 8
COURBE = [(0, 0), (60, 55), (128, 130), (192, 198), (255, 255)]


def srgb_vers_lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_vers_srgb(x):
    x = np.clip(x, 0, None)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def luma(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def courbe_monotone(points):
    """Interpolation monotone (Fritsch-Carlson) des points de la courbe des tons."""
    xs = np.array([p[0] for p in points], float) / 255
    ys = np.array([p[1] for p in points], float) / 255
    d = np.diff(ys) / np.diff(xs)
    m = np.zeros_like(xs)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xs) - 1):
        m[i] = 0 if d[i - 1] * d[i] <= 0 else 2 / (1 / d[i - 1] + 1 / d[i])

    def f(x):
        x = np.clip(x, 0, 1)
        i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1])
    return f


def tonalite(y):
    """Courbe appliquée à la luminance (valeurs gamma sRGB 0..1)."""
    # Blancs / noirs : déplacement des points extrêmes
    noir = -NOIRS / 100 * 0.10
    blanc = 1 - BLANCS / 100 * 0.08
    y = np.clip((y - noir) / (blanc - noir), 0, 1.2)
    # Ombres : relève les tons autour de 0.2
    y = y + OMBRES / 100 * 0.35 * y * (1 - np.clip(y, 0, 1)) ** 3
    # Hautes lumières : compression douce au-dessus de 0.75
    k = 0.75
    force = -HAUTES_LUMIERES / 100
    haut = y > k
    comp = k + (1 - k) * np.tanh((y - k) / (1 - k))
    y = np.where(haut, (1 - force) * np.minimum(y, 1) + force * comp, y)
    # Contraste : courbe en S autour de 0.5
    yc = np.clip(y, 0, 1)
    s = yc * yc * (3 - 2 * yc)
    y = yc + CONTRASTE / 100 * 0.6 * (s - yc)
    # Courbe des tons personnalisée
    return courbe_monotone(COURBE)(y)


def tonalite_norm(y):
    """Tonalité recalée pour que le blanc pur reste à 1."""
    return tonalite(y) / tonalite(np.array(1.0))


def rgb_vers_hsv(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dd = np.where(d > 1e-6, d, 1)
    h = np.select([mx == r, mx == g], [((g - b) / dd) % 6, (b - r) / dd + 2], (r - g) / dd + 4)
    h = np.where(d > 1e-6, h * 60, 0)
    return h, s, mx


def hsv_vers_rgb(h, s, v):
    h = (h % 360) / 60
    c = v * s
    x = c * (1 - np.abs(h % 2 - 1))
    z = np.zeros_like(h)
    i = np.floor(h).astype(int) % 6
    choix = [np.stack(t, -1) for t in [(c, x, z), (x, c, z), (z, c, x), (z, x, c), (x, z, c), (c, z, x)]]
    out = np.select([(i == k)[..., None] for k in range(6)], choix)
    return out + (v - c)[..., None]


def poids_teinte(h):
    """Poids de chaque plage TSL (triangulaires entre centres voisins)."""
    centres = [v[0] for v in TSL.values()]
    poids = []
    for j, c in enumerate(centres):
        g = centres[j - 1]
        dr = centres[(j + 1) % len(centres)]
        larg_g = (c - g) % 360
        larg_d = (dr - c) % 360
        diff = (h - c + 180) % 360 - 180
        w = np.where(diff < 0, 1 + diff / larg_g, 1 - diff / larg_d)
        poids.append(np.clip(w, 0, 1))
    return poids


def rendu(rgb):
    rgb = np.clip(rgb, 0, 1)
    # 1. Exposition (en linéaire), avec épaule douce pour ne pas brûler
    lin = srgb_vers_lin(rgb) * 2 ** EXPOSITION
    k = 0.6
    epaule = lambda x: np.where(x > k, k + (1 - k) * np.tanh((x - k) / (1 - k)), x)
    lin = epaule(lin) / epaule(np.array(2 ** EXPOSITION))  # le blanc pur reste blanc
    rgb = lin_vers_srgb(lin)

    # 2. Tonalité appliquée à la luminance en gardant les teintes
    y = luma(rgb)
    y2 = tonalite_norm(y)
    ratio = np.where(y > 1e-4, y2 / np.maximum(y, 1e-4), 1)
    rgb_ratio = rgb * ratio[..., None]
    rgb_canal = np.stack([tonalite_norm(rgb[..., c]) for c in range(3)], -1)
    rgb = np.clip(0.5 * rgb_ratio + 0.5 * rgb_canal, 0, 1)

    # 3. TSL par couleur
    h, s, v = rgb_vers_hsv(rgb)
    dh = np.zeros_like(h)
    fs = np.zeros_like(h)
    fl = np.zeros_like(h)
    for w, (_, (th, ts, tl)) in zip(poids_teinte(h), TSL.values()):
        dh += w * th * 0.3
        fs += w * ts / 100
        fl += w * tl / 100
    h = h + dh
    s = np.clip(s * (1 + fs), 0, 1)
    v = np.clip(v * (1 + 0.25 * fl * s), 0, 1)

    # 4. Vibrance (renforce surtout les couleurs peu saturées) puis saturation
    s = np.clip(s + VIBRANCE / 100 * 0.6 * s * (1 - s), 0, 1)
    s = np.clip(s * (1 + SATURATION / 100), 0, 1)
    rgb = hsv_vers_rgb(h, s, v)

    # 5. Étalonnage : ombres bleutées, hautes lumières chaudes
    def teinte(hue):
        c = hsv_vers_rgb(np.array(float(hue)), np.array(1.0), np.array(1.0))
        return c - luma(c)
    y = luma(rgb)[..., None]
    # (le noir pur et le blanc pur restent neutres)
    w_ombres = (1 - y) ** 2 * np.clip(y * 8, 0, 1)
    w_hl = y ** 2 * np.clip((1 - y) * 8, 0, 1)
    rgb = rgb + teinte(OMBRES_TEINTE) * OMBRES_SAT / 100 * 0.35 * w_ombres
    rgb = rgb + teinte(HL_TEINTE) * HL_SAT / 100 * 0.35 * w_hl
    return np.clip(rgb, 0, 1)


def ecrire_cube(chemin):
    g = np.linspace(0, 1, TAILLE)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")  # rouge varie le plus vite
    entree = np.stack([r, gg, b], -1).reshape(-1, 3)
    sortie = rendu(entree)
    lignes = ['TITLE "Lumineux Punchy"', f"LUT_3D_SIZE {TAILLE}",
              "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    lignes += [f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}" for p in sortie]
    chemin.write_text("\n".join(lignes) + "\n")
    return sortie.reshape(TAILLE, TAILLE, TAILLE, 3)


def appliquer(lut, src, dst):
    from PIL import Image
    img = np.asarray(Image.open(src).convert("RGB")).astype(np.float64) / 255
    n = TAILLE - 1
    p = img * n
    i0 = np.clip(np.floor(p).astype(int), 0, n - 1)
    f = p - i0
    out = np.zeros_like(img)
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = ((f[..., 0] if dr else 1 - f[..., 0]) * (f[..., 1] if dg else 1 - f[..., 1])
                     * (f[..., 2] if db else 1 - f[..., 2]))
                out += w[..., None] * lut[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, quality=95)


if __name__ == "__main__":
    lut = ecrire_cube(SORTIE)
    print(f"LUT écrit : {SORTIE}")
    if len(sys.argv) == 3:
        appliquer(lut, sys.argv[1], sys.argv[2])
        print(f"Photo retouchée : {sys.argv[2]}")
