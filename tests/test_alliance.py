# -*- coding: utf-8 -*-
"""Cartographie Alliance Groupe : modèle cohérent, positions, figures 4D, rejeu animé, interface."""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import alliance_modele as m  # noqa: E402
import alliance_cartographie as ac  # noqa: E402


def test_modele_coherent():
    assert m.valider() == []
    ids = {n["id"] for n in m.NOEUDS}
    assert {"local", "github", "sync", "site", "ag_audit", "ag_kali", "findings", "rapport"} <= ids
    assert all(n["couche"] in m.COUCHES for n in m.NOEUDS)
    assert all(m.COULEURS.get(c) for c in m.COUCHES)                 # une couleur par couche
    # la synchronisation GitHub ⇆ local est bien bidirectionnelle
    couples = {(s, d) for s, d, _, _ in m.ARETES}
    assert ("local", "github") in couples and ("sync", "local") in couples


def test_positions_stratifiees_par_couche():
    pos = ac.positions()
    assert len(pos) == len(m.NOEUDS)
    z_local = pos["local"][2]
    z_kali = pos["nmap"][2]
    assert z_kali > z_local                                          # les couches montent (z croît)
    # deux nœuds de la même couche partagent la même hauteur
    assert pos["nmap"][2] == pos["wpscan"][2]


def test_figure_complete():
    fig = ac.figure_complete()
    noms = {t.name for t in fig.data}
    assert set(m.COUCHES) <= noms                                   # une trace-légende par couche
    assert any((t.name or "").startswith("Synchronisation") for t in fig.data)


def test_figure_rejeu_animee():
    fig = ac.figure_rejeu()
    assert len(fig.frames) == len(m.SEQUENCE)
    assert fig.frames[0].name == "0" and fig.frames[-1].name == str(len(m.SEQUENCE) - 1)
    # révélation cumulative : la dernière image montre plus de nœuds que la première
    n0 = len(fig.frames[0].data[1].x)
    nfin = len(fig.frames[-1].data[1].x)
    assert nfin > n0
    assert fig.layout.updatemenus and fig.layout.sliders                # boutons Lire/Pause + curseur


def test_figure_etape_met_en_avant():
    fig = ac.figure_etape(4)                                          # 5 · Audit expert AG-Kali
    assert "AG-Kali" in fig.layout.title.text
    assert len(fig.data) >= 3


def test_registre_et_outils_kali():
    reg = ac.registre_interactions()
    assert len(reg) == len(m.ARETES) and set(reg.columns) == {"De", "Vers", "Relation", "Nature"}
    outils = m.outils_kali()
    assert {o["outil"] for o in outils} >= {"nmap", "WPScan", "sslscan"}
    assert all(o["phase"] and o["but"] and o["revele"] for o in outils)


def test_interface(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "alliance_cartographie.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert any("Alliance Groupe" in mk.value for mk in at.title)
    # vue par défaut = présentation plein écran : narration + navigation
    assert at.radio(key="vue").value.startswith("Présentation")
    assert any("Synchronisation" in mk.value for mk in at.markdown)      # titre de l'étape 1
    assert any("Git" in nfo.value for nfo in at.info)                    # narration de l'étape 1
    at.button(key="presentation_suiv").click().run()
    assert not at.exception, at.exception
    assert any("Intégration continue" in mk.value for mk in at.markdown)  # avance à l'étape 2

    at.radio(key="vue").set_value("Carte complète (4D)").run()
    assert not at.exception, at.exception
    assert any("Chaîne d'outils Kali" in mk.value for mk in at.markdown)
    assert any("AG-Kali" in mk.value for mk in at.markdown)

    at.radio(key="vue").set_value("Rejeu animé (vidéo)").run()
    assert not at.exception, at.exception
    assert any("vidéo" in mk.value for mk in at.markdown)

    at.radio(key="vue").set_value("Parcours étape par étape").run()
    at.slider(key="etape_slider").set_value(5).run()
    assert not at.exception, at.exception
    assert any("AG-Kali" in i.value for i in at.info)                 # étape 5 = audit expert

    at.selectbox(key="detail_noeud").set_value("AG-Kali").run()
    assert not at.exception, at.exception
