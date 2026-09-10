# -*- coding: utf-8 -*-
"""Alliance Groupe — cartographie 4D de l'infrastructure et de la mécanique d'audit.

Application de démonstration (interface Streamlit) : elle montre à des experts
comment fonctionne Alliance Groupe — dépôt GitHub synchronisé avec le repo local,
intégration continue, site en production, audit web **AG-Audit** et audit expert
**AG-Kali** sous Kali Linux — sous forme d'un graphe 4D (trois axes + la couche en
couleur) et d'un rejeu animé, la « vidéo » de toutes les interactions.

Tout vient du modèle éditable `alliance_modele.py`. Aucun système n'est scanné en
direct : c'est la mécanique qui est cartographiée, pas des données réelles.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import alliance_modele as m

RACINE_OUTIL = os.path.dirname(os.path.abspath(__file__))
VERSION_OUTIL = "1.1.0"
try:
    with open(os.path.join(RACINE_OUTIL, "VERSION"), encoding="utf-8") as _f:
        VERSION_OUTIL = _f.read().strip() or VERSION_OUTIL
except OSError:  # pragma: no cover
    pass

COULEURS_NATURE = {"sync": "#3498db", "flux": "#7f8c8d", "audit": "#e74c3c", "livrable": "#9b59b6"}
NOMS_NATURE = {"sync": "Synchronisation", "flux": "Déploiement / données", "audit": "Audit (scan)", "livrable": "Livrable"}


def positions(seed: int = 7) -> Dict[str, Tuple[float, float, float]]:
    """Position 3D de chaque nœud : x, y par disposition de ressorts ; z = couche (le graphe est stratifié)."""
    import networkx as nx

    g = nx.DiGraph()
    for n in m.NOEUDS:
        g.add_node(n["id"])
    for s, d, _, _ in m.ARETES:
        g.add_edge(s, d)
    plat = nx.spring_layout(g, seed=seed, k=1.5, dim=2)
    couche_de = {n["id"]: m.COUCHES.index(n["couche"]) for n in m.NOEUDS}
    pos: Dict[str, Tuple[float, float, float]] = {}
    for nid, (x, y) in plat.items():
        pos[nid] = (float(x) * 6.0, float(y) * 6.0, float(couche_de[nid]) * 2.2)
    return pos


def _segments(couples: Sequence[Tuple[str, str]], pos: Dict[str, Tuple[float, float, float]]):
    xs: List[Optional[float]] = []
    ys: List[Optional[float]] = []
    zs: List[Optional[float]] = []
    for s, d in couples:
        if s in pos and d in pos:
            (x0, y0, z0), (x1, y1, z1) = pos[s], pos[d]
            xs += [x0, x1, None]
            ys += [y0, y1, None]
            zs += [z0, z1, None]
    return xs, ys, zs


def _trace_noeuds(ids: Sequence[str], pos, go, taille_min: int = 8):
    ids = [i for i in ids if i in pos]
    x = [pos[i][0] for i in ids]
    y = [pos[i][1] for i in ids]
    z = [pos[i][2] for i in ids]
    couleurs = [m.COULEURS[m.noeud(i)["couche"]] for i in ids]
    tailles = [taille_min + 4 * m.noeud(i)["poids"] for i in ids]
    textes = [m.noeud(i)["nom"] for i in ids]
    survol = [f"<b>{m.noeud(i)['nom']}</b><br>{m.noeud(i)['couche']}<br>{m.noeud(i)['detail']}" for i in ids]
    return go.Scatter3d(x=x, y=y, z=z, mode="markers+text", text=textes, textposition="top center",
                        textfont=dict(size=10), hovertext=survol, hoverinfo="text", name="nœuds",
                        marker=dict(size=tailles, color=couleurs, opacity=0.95, line=dict(width=1, color="#2c3e50")),
                        showlegend=False)


def figure_complete():
    """Carte 4D complète, tout allumé : nœuds par couche, interactions par nature."""
    import plotly.graph_objects as go

    pos = positions()
    fig = go.Figure()
    # Interactions, une trace par nature (pour la légende).
    for nature, nom in NOMS_NATURE.items():
        couples = [(s, d) for s, d, _, nat in m.ARETES if nat == nature]
        xs, ys, zs = _segments(couples, pos)
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", name=nom,
                                   line=dict(color=COULEURS_NATURE[nature], width=4 if nature != "flux" else 2),
                                   opacity=0.55, hoverinfo="skip"))
    # Nœuds, une trace par couche (pour la légende des couleurs).
    for couche in m.COUCHES:
        ids = [n["id"] for n in m.NOEUDS if n["couche"] == couche]
        if not ids:
            continue
        t = _trace_noeuds(ids, pos, go)
        t.update(name=couche, showlegend=True, legendgroup=couche)
        fig.add_trace(t)
    _mise_en_page(fig, "Infrastructure complète — nœuds colorés par couche, liens par nature")
    return fig


def figure_etape(k: int, hauteur: int = 620):
    """Une étape de la mécanique mise en avant ; le reste est estompé."""
    import plotly.graph_objects as go

    pos = positions()
    etapes = m.SEQUENCE
    k = max(0, min(k, len(etapes) - 1))
    actifs_n = set(etapes[k]["noeuds"])
    actives_a = set(etapes[k]["aretes"])
    fig = go.Figure()
    # Fond estompé : toutes les interactions et tous les nœuds, très pâles.
    xs, ys, zs = _segments([(s, d) for s, d, _, _ in m.ARETES], pos)
    fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color="#bdc3c7", width=1),
                               opacity=0.2, hoverinfo="skip", showlegend=False))
    fond = _trace_noeuds([n["id"] for n in m.NOEUDS], pos, go)
    fond.marker.opacity = 0.18
    fond.mode = "markers"
    fond.update(showlegend=False)
    fig.add_trace(fond)
    # Interactions actives, colorées par nature.
    nature_de = {(s, d): nat for s, d, _, nat in m.ARETES}
    for nature in NOMS_NATURE:
        couples = [(s, d) for (s, d) in actives_a if nature_de.get((s, d)) == nature]
        if not couples:
            continue
        xs, ys, zs = _segments(couples, pos)
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color=COULEURS_NATURE[nature], width=6),
                                   opacity=0.95, hoverinfo="skip", showlegend=False))
    # Nœuds actifs.
    fig.add_trace(_trace_noeuds(sorted(actifs_n), pos, go, taille_min=12))
    _mise_en_page(fig, f"{etapes[k]['titre']} — {etapes[k]['acteur']}", hauteur=hauteur)
    return fig


def figure_rejeu():
    """Rejeu animé (la « vidéo ») : la mécanique se révèle étape par étape, du push à la remédiation."""
    import plotly.graph_objects as go

    pos = positions()
    etapes = m.SEQUENCE
    # Fond permanent, très pâle.
    fig = go.Figure()
    xs, ys, zs = _segments([(s, d) for s, d, _, _ in m.ARETES], pos)
    fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color="#bdc3c7", width=1),
                               opacity=0.15, hoverinfo="skip", showlegend=False))     # trace 0 (fixe)
    fond = _trace_noeuds([n["id"] for n in m.NOEUDS], pos, go)
    fond.marker.opacity = 0.12
    fond.mode = "markers"
    fond.update(showlegend=False)
    fig.add_trace(fond)                                                               # trace 1 (fixe)
    # Traces animées : interactions révélées (2) et nœuds révélés (3).
    fig.add_trace(go.Scatter3d(x=[], y=[], z=[], mode="lines", line=dict(color="#e74c3c", width=5),
                               opacity=0.9, hoverinfo="skip", showlegend=False))       # trace 2
    fig.add_trace(_trace_noeuds(list(etapes[0]["noeuds"]), pos, go, taille_min=12))    # trace 3

    images = []
    cumul_n: List[str] = []
    cumul_a: List[Tuple[str, str]] = []
    for k, e in enumerate(etapes):
        for nid in e["noeuds"]:
            if nid not in cumul_n:
                cumul_n.append(nid)
        for a in e["aretes"]:
            if a not in cumul_a:
                cumul_a.append(a)
        xs, ys, zs = _segments(cumul_a, pos)
        aretes_trace = go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color="#e74c3c", width=5), opacity=0.9, hoverinfo="skip")
        noeuds_trace = _trace_noeuds(list(cumul_n), pos, go, taille_min=12)
        images.append(go.Frame(data=[aretes_trace, noeuds_trace], traces=[2, 3], name=str(k),
                               layout=go.Layout(title=dict(text=f"{e['titre']} — {e['acteur']}"))))
    fig.frames = images
    fig.update_layout(
        updatemenus=[dict(type="buttons", showactive=False, x=0.02, y=0.98, buttons=[
            dict(label="▶ Lire", method="animate",
                 args=[None, dict(frame=dict(duration=1100, redraw=True), fromcurrent=True, transition=dict(duration=300))]),
            dict(label="Pause", method="animate",
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=0, pad=dict(t=30), currentvalue=dict(prefix="étape "),
                      steps=[dict(method="animate", label=str(k + 1),
                                  args=[[str(k)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                             for k in range(len(etapes))])])
    _mise_en_page(fig, f"{etapes[0]['titre']} — {etapes[0]['acteur']}")
    return fig


def _mise_en_page(fig, titre: str, hauteur: int = 620) -> None:
    fig.update_layout(
        title=dict(text=titre, font=dict(size=15)),
        height=hauteur, margin=dict(l=0, r=0, t=44, b=0), legend=dict(x=0.0, y=0.99, bgcolor="rgba(255,255,255,0.6)"),
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False),
                   zaxis=dict(title="couche", tickvals=[i * 2.2 for i in range(len(m.COUCHES))],
                              ticktext=list(m.COUCHES), tickfont=dict(size=9)),
                   aspectmode="manual", aspectratio=dict(x=1.2, y=1.2, z=1.0)))


def registre_interactions() -> pd.DataFrame:
    return pd.DataFrame([{"De": m.noeud(s)["nom"], "Vers": m.noeud(d)["nom"], "Relation": rel, "Nature": NOMS_NATURE[nat]}
                         for s, d, rel, nat in m.ARETES])


def _vue_presentation(st) -> None:  # pragma: no cover - interface graphique
    """Mode présentation plein écran : la carte se raconte étape par étape, pour pitcher devant des experts."""
    etapes = m.sequence()
    n = len(etapes)
    if "presentation_i" not in st.session_state:
        st.session_state["presentation_i"] = 0
    i = max(0, min(st.session_state["presentation_i"], n - 1))

    st.write(f"### 🎬 {etapes[i]['titre']}")
    st.progress((i + 1) / n, text=f"Étape {i + 1} / {n} — la mécanique complète d'Alliance Groupe")

    st.plotly_chart(figure_etape(i, hauteur=560), width="stretch", key=f"presentation_fig_{i}")

    st.info(f"**🎙️ {etapes[i]['acteur']} —** {etapes[i]['description']}")

    prec, milieu, suiv = st.columns([1, 2, 1])
    with prec:
        if st.button("◀ Précédent", key="presentation_prec", width="stretch", disabled=(i == 0)):
            st.session_state["presentation_i"] = max(0, i - 1)
            st.rerun()
    with milieu:
        if st.button("↺ Recommencer", key="presentation_reset", width="stretch"):
            st.session_state["presentation_i"] = 0
            st.rerun()
    with suiv:
        if st.button("Suivant ▶", key="presentation_suiv", width="stretch", disabled=(i == n - 1)):
            st.session_state["presentation_i"] = min(n - 1, i + 1)
            st.rerun()

    with st.expander("🗒️ Le scénario complet (pour préparer ton pitch)"):
        for k, e in enumerate(etapes):
            marque = "**➤ " if k == i else "· "
            fin = "**" if k == i else ""
            st.markdown(f"{marque}{e['titre']} — *{e['acteur']}*{fin}  \n<span style='color:#7f8c8d'>{e['description']}</span>",
                        unsafe_allow_html=True)


def lancer_interface() -> None:  # pragma: no cover - interface graphique
    import streamlit as st

    st.set_page_config(layout="wide", page_title="Alliance Groupe — Cartographie 4D")
    st.title("🛰️ Alliance Groupe — Cartographie 4D de l'infrastructure")
    st.subheader("Mécanique complète, audit web AG-Audit et audit expert AG-Kali, en un graphe animé")
    probs = m.valider()
    if probs:
        st.error("Modèle incohérent : " + " ; ".join(probs))
    st.caption("Démonstration : ce graphe est un **modèle éditable** de la mécanique d'Alliance Groupe, pour la montrer à des "
               "experts. Rien n'est scanné en direct — la structure et les interactions se modifient dans `alliance_modele.py`.")
    st.markdown("---")

    with st.sidebar:
        st.header("🗺️ Vue")
        vue = st.radio("Affichage",
                       ["Présentation (plein écran)", "Carte complète (4D)", "Rejeu animé (vidéo)", "Parcours étape par étape"],
                       key="vue")
        st.markdown("---")
        st.header("🎨 Couches")
        for couche in m.COUCHES:
            st.markdown(f"<span style='color:{m.COULEURS[couche]}'>●</span> {couche}", unsafe_allow_html=True)
        st.markdown("---")
        st.header("🔗 Interactions")
        for nat, nom in NOMS_NATURE.items():
            st.markdown(f"<span style='color:{COULEURS_NATURE[nat]}'>▬</span> {nom}", unsafe_allow_html=True)
        st.markdown("---")
        st.caption(f"Alliance Groupe · Cartographie version {VERSION_OUTIL}")

    if vue.startswith("Présentation"):
        _vue_presentation(st)
        return

    col_g, col_d = st.columns([3, 2])
    with col_g:
        if vue.startswith("Carte"):
            st.write("### 🛰️ Infrastructure complète")
            st.plotly_chart(figure_complete(), width="stretch")
        elif vue.startswith("Rejeu"):
            st.write("### 🎥 Rejeu de la mécanique — la « vidéo » des interactions")
            st.caption("Appuie sur ▶ : le push, la CI, la mise en ligne, AG-Audit, AG-Kali, le rapport, puis la boucle de remédiation.")
            st.plotly_chart(figure_rejeu(), width="stretch")
        else:
            etapes = m.sequence()
            i = st.slider("Étape", 1, len(etapes), 1, key="etape_slider") - 1
            st.write(f"### 🎬 {etapes[i]['titre']}")
            st.info(f"**{etapes[i]['acteur']} :** {etapes[i]['description']}")
            st.plotly_chart(figure_etape(i), width="stretch")

    with col_d:
        st.write("### 🔁 Synchronisation GitHub ⇆ local")
        st.markdown("Le **repo local** et le **dépôt GitHub** s'alignent en continu (`git push` / `pull`). GitHub déclenche la "
                    "**CI** (tests + lanceurs sur trois systèmes), qui autorise le **déploiement** du site. Toute correction "
                    "issue d'un audit revient dans le repo local, est poussée, et le cycle recommence.")
        st.write("### 🧩 Les deux audits")
        st.markdown("**AG-Audit** — audit web guidé : exploration du site, en-têtes et TLS, puis rapport DOCX brandé et devis. "
                    "Rapide, cadré, reproductible.\n\n"
                    "**AG-Kali** — audit expert sous Kali Linux : la chaîne d'outils complète, en profondeur, ci-dessous.")
        st.write("### 🐉 Chaîne d'outils Kali (AG-Kali)")
        st.dataframe(pd.DataFrame(m.outils_kali()).rename(columns={"phase": "Phase", "outil": "Outil", "but": "But", "revele": "Ce que ça révèle"}),
                     width="stretch", hide_index=True)
        st.caption("Audit défensif sur les propres actifs d'Alliance Groupe. sqlmap tourne en détection seule, sans extraction.")

    st.markdown("---")
    st.write("### 📋 Toutes les interactions")
    st.dataframe(registre_interactions(), width="stretch", hide_index=True)
    with st.expander("🔎 Détail d'un composant"):
        choix = st.selectbox("Composant", [n["nom"] for n in m.NOEUDS], key="detail_noeud")
        n = next(x for x in m.NOEUDS if x["nom"] == choix)
        st.markdown(f"**{n['nom']}** · couche *{n['couche']}*\n\n{n['detail']}")


if __name__ == "__main__":  # pragma: no cover
    lancer_interface()
