# -*- coding: utf-8 -*-
"""Chasse aux bosses (bump hunt) : une résonance est un excès localisé sur un fond lisse.

Isolation Forest repère des événements rares ; une particule nouvelle se voit
autrement : une accumulation d'événements dans une étroite fenêtre d'une
variable (typiquement une masse invariante), au-dessus de ce que prédit le fond
lisse alentour. C'est ce que fait ce module, sans aucune hypothèse physique :

1. histogramme de la variable (classes logarithmiques si le spectre s'y prête,
   linéaires sinon) ;
2. pour chaque fenêtre (position × largeur), le fond attendu dans la fenêtre est
   prédit par un ajustement quadratique robuste du log-comptage des classes
   voisines (bandes latérales) ; une fenêtre dont les bandes ne sont pas bien
   décrites par ce fond (χ² réduit trop grand : seuil de déclenchement, bord)
   n'est pas testée plutôt que de produire une fausse bosse ;
3. probabilité locale (Poisson) d'observer au moins le comptage vu, puis
   correction du nombre de fenêtres testées (Bonferroni, conservatrice) ;
4. seules les bosses dont la probabilité globale passe le seuil sont retenues,
   sans chevauchement, et deux fenêtres contiguës d'un même pic sont fusionnées.

Rien ici ne dit « boson Z » ou « J/ψ » : le module rend une position, une
largeur, un comptage observé, un comptage attendu et des probabilités. La
lecture physique appartient au physicien.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

N_CLASSES = 150
LARGEURS = (1, 2, 3, 4, 6, 8)        # largeur des fenêtres, en classes
BANDE = 2                            # bandes latérales : BANDE × largeur de chaque côté
SEUIL_P_GLOBAL = 1e-3                # bosse retenue (« indice ») si p_global < seuil
P_CINQ_SIGMA = 2.867e-7              # p unilatéral pour 5 σ : le seuil de découverte en physique des particules
MIN_ATTENDU = 3.0                    # fond attendu minimal pour tester une fenêtre
MIN_VALEURS_DISTINCTES = 30
RAPPORT_LOG = 20.0                   # max/min au-delà duquel les classes sont logarithmiques
MAX_CHI2_BANDES = 3.0                # au-delà, le fond lisse ne décrit pas les bandes latérales : fenêtre non testée
MOTIFS_ANGULAIRES = ("eta", "phi", "theta", "angle", "rapid", "cos")


@dataclass
class Bosse:
    variable: str
    centre: float
    bord_bas: float
    bord_haut: float
    observe: int
    attendu: float
    z_local: float
    p_local: float
    p_global: float
    n_tests: int
    echelle: str                      # "log" ou "lineaire"
    au_bord: bool = False             # fenêtre dans les 5 % extrêmes du spectre : seuil ou bord, à prendre avec prudence
    i_debut: int = 0                  # indices de classes (dans les bords de l'échantillon complet)
    i_fin: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classes(valeurs: Sequence[float], n_classes: int = N_CLASSES) -> Tuple[np.ndarray, str]:
    """Bords des classes et échelle. Log si le spectre est positif et étalé."""
    x = np.asarray(valeurs, dtype=float)
    x = x[np.isfinite(x)]
    bas, haut = np.percentile(x, 0.2), np.percentile(x, 99.8)
    if bas > 0 and haut / bas > RAPPORT_LOG:
        return np.exp(np.linspace(np.log(bas), np.log(haut), n_classes + 1)), "log"
    if haut <= bas:
        haut = bas + 1.0
    return np.linspace(bas, haut, n_classes + 1), "lineaire"


def _fond_attendu(comptes: np.ndarray, debut: int, largeur: int) -> Optional[float]:
    """Fond attendu dans [debut, debut+largeur) : ajustement quadratique robuste du log-comptage des bandes latérales."""
    coefs = _ajuster_fond(comptes, debut, largeur)
    if coefs is None:
        return None
    fen = np.arange(debut, debut + largeur)
    return float(np.sum(np.exp(np.polyval(coefs, fen - debut)) - 0.5).clip(min=0.0))


def _ajuster_fond(comptes: np.ndarray, debut: int, largeur: int, bande: int = BANDE) -> Optional[np.ndarray]:
    """Coefficients du fond lisse (quadratique en log-comptage, origine à `debut`), ou None si les bandes ne s'y prêtent pas."""
    n = len(comptes)
    g0, g1 = max(0, debut - bande * largeur), debut
    d0, d1 = debut + largeur, min(n, debut + largeur + bande * largeur)
    if (g1 - g0) < bande * largeur or (d1 - d0) < bande * largeur:
        return None
    idx = np.r_[np.arange(g0, g1), np.arange(d0, d1)]
    if len(idx) < 6:
        return None
    garde = np.ones(len(idx), dtype=bool)
    coefs = None
    for _ in range(3):                                   # les classes en excès (queue d'un pic voisin, autre bosse)
        y = np.log(comptes[idx[garde]] + 0.5)            # sont écartées des bandes ; les déficits sont conservés
        coefs = np.polyfit(idx[garde] - debut, y, 2)
        ajuste = np.exp(np.polyval(coefs, idx - debut)) - 0.5
        tirage = (comptes[idx] - ajuste) / np.sqrt(np.maximum(ajuste, 1.0))
        nouveau = garde & ~(tirage > 3.0)
        if nouveau.sum() < max(6, int(0.7 * len(idx))) or nouveau.sum() == garde.sum():
            break
        garde = nouveau
    ajuste = np.exp(np.polyval(coefs, idx - debut)) - 0.5
    chi2 = float(np.sum((comptes[idx[garde]] - ajuste[garde]) ** 2 / np.maximum(ajuste[garde], 1.0)) / max(garde.sum() - 3, 1))
    if chi2 > MAX_CHI2_BANDES:
        return None
    return coefs


def _resserrer(comptes: np.ndarray, bords: np.ndarray, b: Bosse) -> Bosse:
    """Ramène la fenêtre à la sous-fenêtre la plus significative qu'elle contient.

    Une résonance étroite retenue (ou fusionnée) dans une fenêtre large qui
    englobait ses queues retrouve ainsi sa vraie largeur : la sous-fenêtre
    étroite centrée sur le pic a la plus petite probabilité locale. Une structure
    large, elle, reste large. Chaque sous-fenêtre est jugée avec ses propres
    bandes latérales, comme dans la chasse.
    """
    meilleure = b
    largeur_max = b.i_fin - b.i_debut
    for largeur in LARGEURS:
        if largeur >= largeur_max:
            break
        for debut in range(b.i_debut, b.i_fin - largeur + 1):
            attendu = _fond_attendu(comptes, debut, largeur)
            if attendu is None or attendu < MIN_ATTENDU:
                continue
            observe = int(comptes[debut:debut + largeur].sum())
            if observe <= attendu:
                continue
            p_local, z_local = _p_z(observe, attendu)
            if p_local < meilleure.p_local:
                meilleure = Bosse(b.variable, 0.0, float(bords[debut]), float(bords[debut + largeur]), observe, attendu,
                                  z_local, p_local, min(1.0, p_local * b.n_tests), b.n_tests, b.echelle, False,
                                  debut, debut + largeur)
    return meilleure


def _p_z(observe: int, attendu: float) -> Tuple[float, float]:
    p_local = float(sp_stats.poisson.sf(observe - 1, attendu)) if observe > 0 else 1.0
    return p_local, float(sp_stats.norm.isf(max(p_local, 1e-300)))


def chasser(valeurs: Sequence[float], variable: str, seuil_p_global: float = SEUIL_P_GLOBAL,
            n_classes: int = N_CLASSES) -> List[Bosse]:
    """Bosses significatives dans `valeurs`, triées par probabilité globale croissante."""
    x = np.asarray(valeurs, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 200 or len(np.unique(x)) < MIN_VALEURS_DISTINCTES:
        return []
    bords, echelle = classes(x, n_classes)
    comptes, _ = np.histogram(x, bins=bords)
    candidats: List[Bosse] = []
    n_tests = 0
    for largeur in LARGEURS:
        for debut in range(0, n_classes - largeur + 1):
            attendu = _fond_attendu(comptes, debut, largeur)
            if attendu is None or attendu < MIN_ATTENDU:
                continue
            n_tests += 1
            observe = int(comptes[debut:debut + largeur].sum())
            if observe <= attendu:
                continue
            p_local, z_local = _p_z(observe, attendu)
            candidats.append(Bosse(variable, 0.0, float(bords[debut]), float(bords[debut + largeur]),
                                   observe, attendu, z_local, p_local, 1.0, 0, echelle, False, debut, debut + largeur))
    if not candidats or n_tests == 0:
        return []
    retenues: List[Bosse] = []
    for b in sorted(candidats, key=lambda b: b.p_local):
        b.n_tests = n_tests
        b.p_global = min(1.0, b.p_local * n_tests)
        if b.p_global >= seuil_p_global:
            break
        if any(not (b.i_fin <= r.i_debut or b.i_debut >= r.i_fin) for r in retenues):
            continue                                                       # chevauche une bosse plus forte
        retenues.append(b)
    fusionnees = [_resserrer(comptes, bords, b) for b in _fusionner(retenues)]
    for b in fusionnees:
        b.centre = _centre_pondere(comptes, bords, b)
        b.au_bord = bool(b.i_debut <= int(0.05 * n_classes) or b.i_fin >= int(0.95 * n_classes))
    return sorted(fusionnees, key=lambda b: b.p_global)


def _centre_pondere(comptes: np.ndarray, bords: np.ndarray, b: Bosse) -> float:
    """Centre de la bosse : moyenne des centres de classes de la fenêtre, pondérée par les comptages."""
    c = comptes[b.i_debut:b.i_fin].astype(float)
    if b.echelle == "log" and bords[b.i_debut] > 0:
        milieux = np.sqrt(bords[b.i_debut:b.i_fin] * bords[b.i_debut + 1:b.i_fin + 1])
    else:
        milieux = (bords[b.i_debut:b.i_fin] + bords[b.i_debut + 1:b.i_fin + 1]) / 2
    return float(np.average(milieux, weights=c)) if c.sum() > 0 else float(milieux.mean())


def largeur_relative(b: Bosse) -> float:
    return float((b.bord_haut - b.bord_bas) / abs(b.centre)) if b.centre else float("inf")


def _fusionner(bosses: List[Bosse]) -> List[Bosse]:
    """Deux bosses de la même variable dont les fenêtres se touchent sont un seul pic coupé en deux."""
    fusion: List[Bosse] = []
    for b in sorted(bosses, key=lambda b: b.i_debut):
        if fusion and fusion[-1].variable == b.variable and fusion[-1].i_fin == b.i_debut:
            a = fusion[-1]
            observe, attendu = a.observe + b.observe, a.attendu + b.attendu
            p_local, z_local = _p_z(observe, attendu)
            fusion[-1] = Bosse(a.variable, 0.0, a.bord_bas, b.bord_haut, observe, attendu, z_local, p_local,
                               min(1.0, p_local * a.n_tests), a.n_tests, a.echelle, False, a.i_debut, b.i_fin)
        else:
            fusion.append(b)
    return fusion


def exces_dans_fenetre(valeurs: Sequence[float], bords: np.ndarray, i_debut: int, i_fin: int) -> Dict[str, Any]:
    """Excès dans une fenêtre FIXÉE (classes [i_debut, i_fin) de `bords`) : un seul test, sans facteur d'essais.

    Sert à revérifier une bosse sur une moitié de l'échantillon, sur un run de
    référence, ou à tester l'hypothèse d'un physicien à un endroit précis.
    """
    x = np.asarray(valeurs, dtype=float)
    x = x[np.isfinite(x)]
    comptes, _ = np.histogram(x, bins=bords)
    attendu = _fond_attendu(comptes, i_debut, i_fin - i_debut)
    observe = int(comptes[i_debut:i_fin].sum())
    if attendu is None or attendu < MIN_ATTENDU:
        return {"observe": observe, "attendu": attendu, "p_local": None, "z_local": None, "testable": False}
    p_local, z_local = _p_z(observe, attendu)
    return {"observe": observe, "attendu": float(attendu), "p_local": p_local, "z_local": z_local, "testable": True}


def fenetre_autour(bords: np.ndarray, valeur: float, demi_largeur: float) -> Tuple[int, int]:
    """Indices de classes couvrant [valeur − demi_largeur, valeur + demi_largeur] (au moins une classe)."""
    i0 = int(np.clip(np.searchsorted(bords, valeur - demi_largeur, side="right") - 1, 0, len(bords) - 2))
    i1 = int(np.clip(np.searchsorted(bords, valeur + demi_largeur, side="left"), i0 + 1, len(bords) - 1))
    return i0, i1


def est_angulaire(colonne: str) -> bool:
    """Variable angulaire ou de rapidité : sa forme reflète la géométrie et l'acceptance du détecteur, pas un spectre."""
    nom = colonne.lower()
    return any(m in nom for m in MOTIFS_ANGULAIRES)


def colonnes_spectrales(colonnes: Sequence[str]) -> List[str]:
    return [c for c in colonnes if not est_angulaire(c)]


def chasser_matrice(matrice: pd.DataFrame, colonnes: Optional[Sequence[str]] = None,
                    seuil_p_global: float = SEUIL_P_GLOBAL, exclure_angles: bool = True,
                    n_classes: int = N_CLASSES) -> List[Bosse]:
    """Chasse sur chaque colonne spectrale ; la correction du nombre de tests inclut le nombre de colonnes."""
    colonnes = list(colonnes or matrice.columns)
    if exclure_angles:
        colonnes = colonnes_spectrales(colonnes)
    toutes: List[Bosse] = []
    for c in colonnes:
        if c not in matrice.columns or not np.issubdtype(matrice[c].dtype, np.number):
            continue
        for b in chasser(matrice[c].to_numpy(float), c, seuil_p_global=1.0, n_classes=n_classes):
            b.n_tests = b.n_tests * len(colonnes)
            b.p_global = min(1.0, b.p_local * b.n_tests)
            if b.p_global < seuil_p_global:
                toutes.append(b)
    return sorted(toutes, key=lambda b: b.p_global)


def decrire(b: Bosse) -> str:
    return (f"{b.variable} ≈ {b.centre:.4g} (fenêtre {b.bord_bas:.4g} – {b.bord_haut:.4g}) : {b.observe} événements "
            f"observés pour {b.attendu:.1f} attendus du fond lisse, z local = {b.z_local:.1f}, "
            f"p global = {b.p_global:.2g} ({b.n_tests} fenêtres testées)")
