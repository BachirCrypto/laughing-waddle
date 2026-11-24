# Réglages de retouche « Lumineux Punchy »

Ces réglages reproduisent la retouche de la photo de référence (orateur en costume
bleu rayé devant les rideaux bleus et blancs).

> **À savoir :** la photo reçue ne contient aucune donnée de retouche (pas d'EXIF ni
> de XMP). Les réglages ci-dessous ont donc été **reconstitués en mesurant l'image**
> (tons, couleurs de la peau, des rideaux, des murs et du costume). Ils donnent le
> même rendu, mais ce ne sont pas les valeurs d'origine du retoucheur.

## Ce que montre la photo

- Image très claire : murs et sol presque blancs, sans être brûlés.
- Noirs profonds (cheveux, costume) avec une légère dominante bleue dans les ombres.
- Bleus très saturés (rideaux, marqueur).
- Peau orangée, lumineuse et saturée (surtout les paumes).
- Hautes lumières légèrement chaudes (murs crème).
- Image nette et détaillée (rayures du costume, texture de la peau).
- Pas de vignettage, pas de grain.

## Valeurs à saisir

### Lumière
| Réglage | Valeur |
|---|---|
| Exposition | **+0,40** |
| Contraste | **+15** |
| Hautes lumières | **-20** |
| Ombres | **+10** |
| Blancs | **+25** |
| Noirs | **-15** |

Courbe des tonalités (canal RVB, légère courbe en S) :
`0→0` · `60→55` · `128→130` · `192→198` · `255→255`

### Présence
| Réglage | Valeur |
|---|---|
| Texture | **+15** |
| Clarté | **+10** |
| Correction du voile | **+5** |
| Vibrance | **+20** |
| Saturation | **+5** |

### Mélangeur de couleurs (TSL)
| Couleur | Teinte | Saturation | Luminance |
|---|---|---|---|
| Rouge | 0 | 0 | 0 |
| Orange | 0 | **+10** | **+10** |
| Jaune | **-5** | **+5** | **+5** |
| Vert | 0 | **-20** | 0 |
| Bleu-vert (Aqua) | **-5** | **+10** | 0 |
| Bleu | **-5** | **+30** | **-5** |
| Violet | 0 | **-10** | 0 |
| Magenta | 0 | **-10** | 0 |

### Étalonnage des couleurs (Color Grading)
| Zone | Teinte | Saturation |
|---|---|---|
| Ombres | **220** (bleu) | **8** |
| Tons moyens | 0 | 0 |
| Hautes lumières | **45** (orange doré) | **8** |

Fusion **50**, Balance **0**.

### Détail
| Réglage | Valeur |
|---|---|
| Netteté | **50** |
| Rayon | **1,0** |
| Détail | **25** |
| Masquage | **30** |
| Réduction du bruit (luminance) | **10** |
| Réduction du bruit (couleur) | **25** |

### Optique et effets
- Supprimer l'aberration chromatique : **activé**
- Corrections de profil d'objectif : **activé**
- Vignettage : **0** · Grain : **0**

### Calibrage
- Primaire bleue, saturation : **+15** (tout le reste à 0)

### Balance des blancs (non incluse dans le preset)
À régler photo par photo : le mur doit rester **crème** (ni jaune, ni gris) et la
nappe **blanche**. Sur la référence, la balance est neutre avec une très légère
pointe de magenta (Teinte ≈ +5).

## Installer les fichiers

Fichiers fournis dans `presets/` :
- `Lumineux_Punchy.xmp` : preset Lightroom / Camera Raw (tous les réglages ci-dessus)
- `Lumineux_Punchy.cube` : LUT 3D (couleurs et tons uniquement)

**Lightroom (mobile, ordinateur)** : panneau *Paramètres prédéfinis* → menu `…` →
*Importer des paramètres prédéfinis* → choisir `Lumineux_Punchy.xmp`. Il apparaît
dans le groupe « Copie Retouche ».

**Lightroom Classic** : module Développement → panneau *Paramètres prédéfinis* →
`+` → *Importer des paramètres prédéfinis…* → `Lumineux_Punchy.xmp`.

**Photoshop / Camera Raw** : Camera Raw → onglet *Paramètres prédéfinis* → `…` →
*Importer des profils et des paramètres* → `Lumineux_Punchy.xmp`.

**LUT `.cube`** (Photoshop *Correspondance de couleurs*, Premiere, DaVinci,
CapCut…) : reproduit les couleurs et la lumière, mais pas la texture, la clarté ni
la netteté (un LUT ne peut pas les contenir). À utiliser sur des photos non
retouchées.

## Conseils

- Après application, ajuste d'abord **l'exposition** et **la balance des blancs**
  selon chaque photo : le reste du preset donne le style.
- Si une photo est déjà très claire, baisse l'exposition vers +0,10 pour ne pas
  brûler les murs.
- Le LUT peut être régénéré ou appliqué à une photo avec
  `python3 outils/generer_lut.py photo.jpg photo_retouchee.jpg`.
- Pour appliquer **tout** le preset (couleurs + texture, clarté, netteté) à une
  photo : `python3 outils/appliquer_preset.py photo.jpg sortie.jpg --exposition -0.4 --temperature -25`
  (`--exposition`, `--temperature` et `--teinte` = corrections propres à la photo).

## Photos retouchées

| Photo | Corrections propres à la photo | Résultat |
|---|---|---|
| IMG_2553 | Exposition -0,40 (soit 0 au total), température -25 (plus froide, nappe blanche) | `retouches/IMG_2553_Lumineux_Punchy.jpg` |
