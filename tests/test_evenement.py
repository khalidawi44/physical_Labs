# -*- coding: utf-8 -*-
"""Vidéo d'un événement : particules reconnues, hélices selon la charge, animation, sélection depuis une bosse."""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import anemone_evenement as ae  # noqa: E402


def _ligne_cartesienne():
    return pd.Series({"Run": 1, "Event": 7, "E1": 50.0, "px1": 30.0, "py1": 0.0, "pz1": 40.0, "Q1": 1,
                      "E2": 50.0, "px2": -30.0, "py2": 0.0, "pz2": -40.0, "Q2": -1, "type2": "G", "M": 100.0})


def test_particules_cartesiennes_et_cylindriques():
    parts = ae.particules(_ligne_cartesienne())
    assert [p.charge for p in parts] == [1, -1]
    assert abs(parts[0].pt - 30.0) < 1e-9 and abs(parts[0].phi) < 1e-9 and abs(parts[0].eta - np.arcsinh(40 / 30)) < 1e-9
    assert parts[1].nom.startswith("G") and parts[1].energie == 50.0
    l2 = pd.Series({"pt1": 20.0, "eta1": 0.5, "phi1": 1.0, "pt2": 15.0, "eta2": -0.5, "phi2": -2.0})
    parts2 = ae.particules(l2)
    assert len(parts2) == 2 and all(p.charge == 0 for p in parts2)          # charge inconnue
    assert ae.particules(pd.Series({"Energie_MeV": 4.0, "Temps_ns": 1.0})) == []
    assert ae.peut_afficher(["px1", "py1", "pz1"]) and not ae.peut_afficher(["E1", "M"])


def test_helice_rayon_et_sens_de_la_charge():
    p_plus = ae.Particule("a", 10.0, 0.0, 0.0, +1)
    p_moins = ae.Particule("b", 10.0, 0.0, 0.0, -1)
    R = 10.0 / (0.3 * ae.CHAMP_TESLA)
    tp, tm = ae.trajectoire(p_plus), ae.trajectoire(p_moins)
    assert np.allclose(tp[0], 0) and np.allclose(tm[0], 0)                 # départ au vertex
    assert tp[1, 0] > 0 and tm[1, 0] > 0                                    # les deux partent vers +x (φ = 0)
    assert tp[-1, 1] * tm[-1, 1] < 0                                        # et s'enroulent en sens opposés
    # rayon : la distance au centre de courbure (0, ∓R) reste R
    centre = np.array([0.0, -R])                                            # pour q = +1, centre à (−q R sin φ, q R cos φ)... φ = 0 → (0, R·q)
    d = np.hypot(tp[:, 0] - 0.0, tp[:, 1] - R)
    assert np.allclose(d, R, rtol=1e-6) or np.allclose(np.hypot(tp[:, 0], tp[:, 1] + R), R, rtol=1e-6)
    assert np.all(np.hypot(tp[:, 0], tp[:, 1]) <= ae.RAYON_MAX + 1e-9)     # s'arrête au bord du schéma
    droite = ae.trajectoire(ae.Particule("c", 10.0, 1.0, 0.3, 0))
    assert np.allclose(droite[1:, 1] / droite[1:, 0], np.tan(0.3), atol=1e-6)                    # ligne droite
    assert np.all(np.abs(droite[:, 2]) <= ae.LONGUEUR_MAX + 1e-9)


def test_figure_animee_et_energie_manquante():
    fig = ae.figure_evenement(_ligne_cartesienne())
    assert len(fig.frames) == ae.N_IMAGES
    assert any("particule 1" in (t.name or "") for t in fig.data)
    w = pd.Series({"pt": 30.0, "eta": 0.1, "phi": 1.0, "Q": -1, "MET": 28.0, "phiMET": -2.0})
    fig_w = ae.figure_evenement(w)
    assert ae.energie_manquante(w) == {"met": 28.0, "phi": -2.0}
    assert any("manquante" in (t.name or "") for t in fig_w.data)


def test_evenements_d_une_bosse():
    df = pd.DataFrame({"M": [1.0, 90.0, 91.5, 200.0], "pt1": [1, 2, 3, 4]})
    assert list(ae.evenements_dans_fenetre(df, "M", 88.0, 93.5).index) == [1, 2]
    assert ae.evenements_dans_fenetre(df, "absente", 0, 1).empty


def test_interface_video_evenement(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    rng = np.random.default_rng(5)
    n = 600
    df = pd.DataFrame({"Run": 1, "Event": np.arange(n),
                       "E1": rng.uniform(20, 80, n), "px1": rng.normal(0, 20, n), "py1": rng.normal(0, 20, n), "pz1": rng.normal(0, 30, n), "Q1": rng.choice([-1, 1], n),
                       "E2": rng.uniform(20, 80, n), "px2": rng.normal(0, 20, n), "py2": rng.normal(0, 20, n), "pz2": rng.normal(0, 30, n), "Q2": rng.choice([-1, 1], n)})
    chemin = tmp_path / "paires.csv"
    df.to_csv(chemin, index=False)
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=300)
    at.run()
    at.sidebar.radio(key="mode_source").set_value("Chemin local").run()
    at.sidebar.text_input(key="chemin_local").set_value(str(chemin)).run()
    assert not at.exception, at.exception
    assert any("Événement de collision" in m.value for m in at.markdown)
    assert at.radio(key="evt_source").value.startswith("Isolés")
    assert any(c.value.startswith("Ligne ") for c in at.caption)           # un événement est affiché avec ses particules
    at.radio(key="evt_source").set_value("Tous les événements").run()
    at.number_input(key="evt_numero").set_value(3).run()
    assert not at.exception, at.exception
    assert any(c.value.startswith("Ligne 2 ") for c in at.caption)         # 3e événement = ligne 2
