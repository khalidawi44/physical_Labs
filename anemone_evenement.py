# -*- coding: utf-8 -*-
"""Affichage d'un événement de collision : trajectoires des particules dans le détecteur, animées.

À partir d'une ligne de la matrice (un événement), le module reconnaît les
particules décrites par leurs impulsions, soit en cartésien (E, px, py, pz),
soit en cylindrique (pt, eta, phi), avec une charge Q facultative, et trace
leur trajectoire depuis le point de collision :

- particule chargée dans le champ magnétique axial B : hélice de rayon
  R = pt / (0,3 · B) (R en mètres, pt en GeV/c, B en teslas), enroulée dans le
  sens donné par le signe de la charge, et de pas fixé par pz / pt ;
- charge inconnue ou nulle : ligne droite.

Le détecteur est un schéma indicatif (cylindres emboîtés : trajectographe,
calorimètres, chambres à muons) aux dimensions de CMS ; rien ici n'est une
simulation du détecteur, seulement la cinématique des particules mesurées.
L'animation fait avancer les trajectoires depuis le vertex : c'est la « vidéo »
de l'événement, image par image, à partir des mesures réelles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

CHAMP_TESLA = 3.8                     # champ du solénoïde de CMS
# Rayons (m) et demi-longueurs (m) des couches du schéma, dimensions approximatives de CMS.
COUCHES = (("trajectographe", 1.2, 2.8, "#3498db"), ("calorimètres", 2.95, 5.5, "#f1c40f"), ("chambres à muons", 7.4, 10.8, "#95a5a6"))
RAYON_MAX, LONGUEUR_MAX = 7.4, 10.8
N_IMAGES = 30
COULEURS = ("#e74c3c", "#2ecc71", "#9b59b6", "#e67e22", "#1abc9c", "#34495e")


@dataclass
class Particule:
    nom: str
    pt: float
    eta: float
    phi: float
    charge: int                       # −1, 0 (inconnue) ou +1
    energie: Optional[float] = None
    points: Optional[np.ndarray] = None   # trajectoire (N × 3) en mètres, du vertex vers l'extérieur

    def description(self) -> str:
        q = {1: "+", -1: "−", 0: "?"}[self.charge]
        e = f", E = {self.energie:.1f}" if self.energie is not None else ""
        return f"{self.nom} (q {q}) : pt = {self.pt:.1f}, η = {self.eta:.2f}, φ = {self.phi:.2f}{e}"


def _val(ligne: pd.Series, *noms: str) -> Optional[float]:
    for n in noms:
        if n in ligne.index:
            try:
                v = float(ligne[n])
            except (TypeError, ValueError):
                continue
            if np.isfinite(v):
                return v
    return None


def indices_particules(colonnes: Sequence[str]) -> List[str]:
    """Suffixes des particules présentes : "1", "2", … ou "" (une seule, colonnes sans numéro)."""
    cols = set(colonnes)
    suffixes: List[str] = []
    for s in [""] + [str(i) for i in range(1, 10)]:
        if ({f"px{s}", f"py{s}", f"pz{s}"} <= cols) or ({f"pt{s}", f"eta{s}", f"phi{s}"} <= cols):
            suffixes.append(s)
    return suffixes


def particules(ligne: pd.Series) -> List[Particule]:
    """Les particules d'un événement, reconnues par leurs colonnes d'impulsion."""
    liste: List[Particule] = []
    for s in indices_particules(list(ligne.index)):
        px, py, pz = _val(ligne, f"px{s}"), _val(ligne, f"py{s}"), _val(ligne, f"pz{s}")
        if px is not None and py is not None and pz is not None:
            pt = float(np.hypot(px, py))
            phi = float(np.arctan2(py, px))
            eta = float(np.arcsinh(pz / pt)) if pt > 0 else 0.0
        else:
            pt, eta, phi = _val(ligne, f"pt{s}"), _val(ligne, f"eta{s}"), _val(ligne, f"phi{s}")
            if pt is None or eta is None or phi is None:
                continue
        q = _val(ligne, f"Q{s}", f"q{s}", f"charge{s}")
        charge = 0 if q is None or q == 0 else (1 if q > 0 else -1)
        nom = f"particule {s}" if s else "particule"
        type_ = ligne.get(f"type{s}", ligne.get(f"Type{s}"))
        if isinstance(type_, str) and type_.strip():
            nom = f"{type_.strip()} {s}".strip()
        liste.append(Particule(nom, float(pt), float(eta), float(phi), charge, _val(ligne, f"E{s}")))
    return liste


def trajectoire(p: Particule, champ: float = CHAMP_TESLA, n_points: int = 120) -> np.ndarray:
    """Points (m) de la trajectoire depuis le vertex jusqu'à la sortie du schéma de détecteur."""
    if p.pt <= 0:
        return np.zeros((2, 3))
    tan_lambda = float(np.sinh(p.eta))                      # pz / pt
    if p.charge == 0 or champ <= 0:
        s = np.linspace(0.0, 4 * RAYON_MAX, n_points)       # abscisse transverse (m)
        x, y, z = s * np.cos(p.phi), s * np.sin(p.phi), s * tan_lambda
    else:
        R = p.pt / (0.3 * champ)                            # rayon de courbure (m)
        q = p.charge
        theta = np.linspace(0.0, min(np.pi, 4 * RAYON_MAX / R), n_points)
        x = q * R * (np.sin(p.phi + q * theta) - np.sin(p.phi))
        y = -q * R * (np.cos(p.phi + q * theta) - np.cos(p.phi))
        z = R * theta * tan_lambda
    dedans = (np.hypot(x, y) <= RAYON_MAX) & (np.abs(z) <= LONGUEUR_MAX)
    k = int(np.argmin(dedans)) if not dedans.all() else len(x)
    k = max(k, 2)
    return np.c_[x[:k], y[:k], z[:k]]


def energie_manquante(ligne: pd.Series) -> Optional[Dict[str, float]]:
    met, phi = _val(ligne, "MET", "met"), _val(ligne, "phiMET", "phi_met", "metphi")
    if met is None or phi is None:
        return None
    return {"met": met, "phi": phi}


def _cylindre(rayon: float, demi_longueur: float, couleur: str, nom: str):
    import plotly.graph_objects as go
    t = np.linspace(0, 2 * np.pi, 48)
    z = np.array([-demi_longueur, demi_longueur])
    T, Z = np.meshgrid(t, z)
    return go.Surface(x=rayon * np.cos(T), y=rayon * np.sin(T), z=Z, showscale=False, opacity=0.08,
                      colorscale=[[0, couleur], [1, couleur]], name=nom, hoverinfo="name", showlegend=True)


def figure_evenement(ligne: pd.Series, anime: bool = True, champ: float = CHAMP_TESLA, n_images: int = N_IMAGES,
                     titre: Optional[str] = None):
    """Figure plotly 3D de l'événement : détecteur schématique, trajectoires, animation depuis le vertex."""
    import plotly.graph_objects as go

    parts = particules(ligne)
    for p in parts:
        p.points = trajectoire(p, champ)
    fig = go.Figure()
    for nom, rayon, demi, couleur in COUCHES:
        fig.add_trace(_cylindre(rayon, demi, couleur, nom))
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode="markers", marker=dict(size=5, color="#f39c12"), name="vertex (collision)"))
    met = energie_manquante(ligne)
    for i, p in enumerate(parts):
        pts = p.points
        fig.add_trace(go.Scatter3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="lines", name=p.description(),
                                   line=dict(color=COULEURS[i % len(COULEURS)], width=6)))
    if met:
        L = min(RAYON_MAX, 0.05 * met["met"] + 0.5)
        fig.add_trace(go.Scatter3d(x=[0, L * np.cos(met["phi"])], y=[0, L * np.sin(met["phi"])], z=[0, 0], mode="lines",
                                   name=f"énergie transverse manquante (MET = {met['met']:.1f})",
                                   line=dict(color="#7f8c8d", width=4, dash="dash")))
    if anime and parts:
        n_fixes = len(COUCHES) + 1
        images = []
        for k in range(1, n_images + 1):
            f = k / n_images
            donnees = []
            for p in parts:
                pts = p.points
                m = max(2, int(round(f * len(pts))))
                donnees.append(go.Scatter3d(x=pts[:m, 0], y=pts[:m, 1], z=pts[:m, 2], mode="lines"))
            images.append(go.Frame(data=donnees, traces=list(range(n_fixes, n_fixes + len(parts))), name=str(k)))
        fig.frames = images
        fig.update_layout(updatemenus=[dict(type="buttons", showactive=False, x=0.02, y=0.98,
                                            buttons=[dict(label="▶ Lire", method="animate",
                                                          args=[None, dict(frame=dict(duration=60, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
                                                     dict(label="Pause", method="animate",
                                                          args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
                          sliders=[dict(active=n_images - 1, pad=dict(t=30), currentvalue=dict(prefix="image "),
                                        steps=[dict(method="animate", label=str(k), args=[[str(k)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                                               for k in range(1, n_images + 1)])])
    lim = RAYON_MAX * 1.05
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=40, b=0), legend=dict(x=0.7, y=0.98),
                      scene=dict(xaxis=dict(title="x (m)", range=[-lim, lim]), yaxis=dict(title="y (m)", range=[-lim, lim]),
                                 zaxis=dict(title="z (m), axe des faisceaux", range=[-LONGUEUR_MAX * 1.05, LONGUEUR_MAX * 1.05]),
                                 aspectmode="manual", aspectratio=dict(x=1, y=1, z=1.4)))
    if titre:
        fig.update_layout(title=titre)
    return fig


def evenements_dans_fenetre(matrice: pd.DataFrame, variable: str, bas: float, haut: float) -> pd.DataFrame:
    """Les événements d'une bosse : ceux dont `variable` tombe dans la fenêtre."""
    if variable not in matrice.columns:
        return matrice.iloc[0:0]
    v = matrice[variable]
    return matrice[(v >= bas) & (v < haut)]


def peut_afficher(colonnes: Sequence[str]) -> bool:
    return bool(indices_particules(colonnes))
