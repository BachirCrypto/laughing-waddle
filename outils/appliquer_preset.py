"""Applique le preset « Lumineux Punchy » complet à une photo.

Couleurs et tons : même calcul que le LUT (generer_lut.rendu).
En plus du LUT : texture, clarté, correction du voile, netteté et
réduction du bruit, avec les valeurs du preset.

Usage :
    python3 outils/appliquer_preset.py photo.jpg sortie.jpg \
        [--exposition 0] [--temperature 0] [--teinte 0]

--exposition (en IL, en plus du +0,40 du preset), --temperature et --teinte
corrigent ce qui est propre à chaque photo, comme on le ferait dans Lightroom
après avoir appliqué le preset.
"""
import argparse
import io

import numpy as np
from PIL import Image, ImageCms, ImageOps

import generer_lut as g

TEXTURE = 15
CLARTE = 10
VOILE = 5
NETTETE = 50          # rayon 1,0, détail 25, masquage 30
BRUIT_LUMINANCE = 10


def charger_srgb(chemin):
    """Ouvre la photo, la redresse et la convertit en sRGB (iPhone = Display P3)."""
    img = ImageOps.exif_transpose(Image.open(chemin))
    icc = img.info.get("icc_profile")
    img = img.convert("RGB")
    if icc:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        img = ImageCms.profileToProfile(img, src, dst, renderingIntent=0, outputMode="RGB")
    return img


def _boite(a, r, axe):
    """Flou boîte de rayon r le long d'un axe (bords répétés)."""
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axe] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axe)
    n = a.shape[axe]
    haut = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axe)
    bas = np.take(c, np.arange(0, n), axis=axe)
    return (haut - bas) / (2 * r + 1)


def flou(canal, rayon):
    """Flou gaussien approché par trois flous boîte successifs."""
    sigma = max(rayon, 0.01)
    r = int(round((np.sqrt(4 * sigma * sigma + 1) - 1) / 2))  # 3 boîtes ≈ gaussienne
    if r < 1:
        # petit rayon : noyau gaussien 3x3 explicite
        k = np.exp(-np.array([1.0, 0.0, 1.0]) / (2 * sigma * sigma))
        k /= k.sum()
        p = np.pad(canal, 1, mode="edge")
        a = k[0] * p[:-2] + k[1] * p[1:-1] + k[2] * p[2:]
        return k[0] * a[:, :-2] + k[1] * a[:, 1:-1] + k[2] * a[:, 2:]
    out = canal
    for _ in range(3):
        out = _boite(_boite(out, r, 0), r, 1)
    return out


def appliquer_luminance(rgb, nouvelle_l, l):
    """Remplace la luminance en gardant les couleurs."""
    ratio = np.where(l > 1e-4, nouvelle_l / np.maximum(l, 1e-4), 1)
    ratio = np.clip(ratio, 0, 4)
    return np.clip(rgb * ratio[..., None], 0, 1)


def details(rgb):
    h, w, _ = rgb.shape
    echelle = max(h, w) / 2000  # rayons pensés pour une image de ~2000 px
    l = g.luma(rgb)

    # Réduction du bruit luminance (légère)
    if BRUIT_LUMINANCE:
        lissee = flou(l, 0.8 * echelle)
        nl = l + BRUIT_LUMINANCE / 100 * 0.5 * (lissee - l)
        rgb, l = appliquer_luminance(rgb, nl, l), nl

    # Clarté : contraste local à grand rayon, surtout dans les tons moyens
    base = flou(l, 25 * echelle)
    masque_moyens = 1 - np.abs(2 * l - 1) ** 2
    nl = l + CLARTE / 100 * 0.6 * (l - base) * masque_moyens

    # Texture : détails moyens (peau, tissu) à rayon moyen
    moyen = flou(nl, 4 * echelle)
    nl = nl + TEXTURE / 100 * 0.8 * (nl - moyen)
    rgb, l = appliquer_luminance(rgb, np.clip(nl, 0, 1), l), np.clip(nl, 0, 1)

    # Correction du voile : abaisse légèrement le voile et renforce la saturation
    if VOILE:
        voile = np.percentile(l, 0.5)
        k = VOILE / 100
        nl = np.clip((l - k * voile) / (1 - k * voile), 0, 1)
        rgb = appliquer_luminance(rgb, nl, l)
        moy = g.luma(rgb)[..., None]
        rgb = np.clip(moy + (rgb - moy) * (1 + 0.5 * k), 0, 1)
        l = g.luma(rgb)

    # Netteté : masque flou rayon 1, seuil via masquage des zones lisses
    fin = flou(l, 1.0 * echelle)
    detail = l - fin
    contour = np.abs(l - flou(l, 2.5 * echelle))
    masque = np.clip((contour - 0.004) / 0.02, 0, 1)  # masquage 30 : épargne les aplats
    nl = l + NETTETE / 100 * 1.2 * detail * masque
    return appliquer_luminance(rgb, np.clip(nl, 0, 1), l)


def balance(rgb, exposition=0.0, temperature=0.0, teinte=0.0):
    """Corrections propres à la photo, faites en linéaire avant le preset.
    temperature < 0 : plus froid ; teinte > 0 : plus magenta (échelle ±100)."""
    if not (exposition or temperature or teinte):
        return rgb
    gain = np.array([2 ** (temperature / 100 * 0.4),
                     2 ** (-teinte / 100 * 0.3),
                     2 ** (-temperature / 100 * 0.4)])
    gain = gain / (gain @ np.array([0.2126, 0.7152, 0.0722]))  # garde la luminosité
    lin = g.srgb_vers_lin(rgb) * gain * 2 ** exposition
    return g.lin_vers_srgb(np.clip(lin, 0, 1))


def appliquer(src, dst, exposition=0.0, temperature=0.0, teinte=0.0):
    img = charger_srgb(src)
    rgb = np.asarray(img).astype(np.float64) / 255
    rgb = balance(rgb, exposition, temperature, teinte)
    rgb = g.rendu(rgb)
    rgb = details(rgb)
    out = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    out.save(dst, quality=95, subsampling=0, icc_profile=srgb)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("sortie")
    ap.add_argument("--exposition", type=float, default=0.0)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--teinte", type=float, default=0.0)
    a = ap.parse_args()
    appliquer(a.source, a.sortie, a.exposition, a.temperature, a.teinte)
    print(f"Photo retouchée : {a.sortie}")
