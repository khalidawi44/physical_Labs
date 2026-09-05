# -*- coding: utf-8 -*-
"""Chasse aux bosses : retrouve un pic injecté, ne déclare rien à 5 σ sur un fond lisse, fusionne, teste une fenêtre fixe."""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import anemone_bosse as ab  # noqa: E402
import anemone_master as am  # noqa: E402


def _fond(rng, n=100000):
    return rng.exponential(10.0, n) + 1.0


def test_pic_injecte_retrouve_a_cinq_sigma():
    rng = np.random.default_rng(1)
    x = np.r_[_fond(rng), rng.normal(42.0, 0.6, 400)]
    bosses = ab.chasser(x, "x")
    assert bosses and bosses[0].p_global < ab.P_CINQ_SIGMA
    assert abs(bosses[0].centre - 42.0) < 1.0
    assert bosses[0].observe > bosses[0].attendu
    assert not bosses[0].au_bord
    assert ab.largeur_relative(bosses[0]) < 0.12


def test_fond_lisse_rien_a_cinq_sigma():
    rng = np.random.default_rng(0)
    fausses = [b for _ in range(10) for b in ab.chasser(_fond(rng), "x") if b.p_global < ab.P_CINQ_SIGMA]
    assert fausses == []


def test_fenetres_contigues_fusionnees_et_centre_pondere():
    rng = np.random.default_rng(2)
    x = np.r_[_fond(rng), rng.normal(30.0, 1.2, 3000)]          # pic large : plusieurs classes
    bosses = ab.chasser(x, "x")
    principales = [b for b in bosses if b.bord_bas < 30.0 < b.bord_haut]
    assert len(principales) == 1                                 # une seule bosse, pas deux moitiés
    assert abs(principales[0].centre - 30.0) < 1.5


def test_fenetre_fixe_et_moities():
    rng = np.random.default_rng(3)
    x = np.r_[_fond(rng), rng.normal(42.0, 0.6, 400)]
    rng.shuffle(x)
    b = ab.chasser(x, "x")[0]
    bords, _ = ab.classes(x)
    r1 = ab.exces_dans_fenetre(x[: len(x) // 2], bords, b.i_debut, b.i_fin)
    r2 = ab.exces_dans_fenetre(x[len(x) // 2:], bords, b.i_debut, b.i_fin)
    assert r1["testable"] and r2["testable"]
    assert r1["p_local"] < 1e-3 and r2["p_local"] < 1e-3          # le pic tient dans chaque moitié
    i0, i1 = ab.fenetre_autour(bords, 42.0, 1.0)
    assert bords[i0] <= 41.0 and bords[i1] >= 43.0


def test_variables_angulaires_exclues():
    rng = np.random.default_rng(4)
    df = pd.DataFrame({"M": np.r_[_fond(rng, 20000), rng.normal(42.0, 0.6, 300)],
                       "eta1": np.r_[rng.normal(0, 1, 20000), rng.normal(0.8, 0.02, 300)]})
    assert ab.colonnes_spectrales(["M", "eta1", "phi2", "pt1"]) == ["M", "pt1"]
    bosses = ab.chasser_matrice(df, ["M", "eta1"])
    assert {b.variable for b in bosses} == {"M"}


def test_grandeurs_derivees_masse_invariante():
    # deux objets de masse nulle : E = |p| ; paire dos à dos dans le plan transverse
    df = pd.DataFrame({"E1": [10.0], "px1": [10.0], "py1": [0.0], "pz1": [0.0],
                       "E2": [10.0], "px2": [-10.0], "py2": [0.0], "pz2": [0.0]})
    d, ajoutees = am.grandeurs_derivees(df)
    assert ajoutees == ["M_paire"] and abs(d["M_paire"][0] - 20.0) < 1e-9
    # même paire en coordonnées cylindriques : pt = 10, eta = 0, Δφ = π → M² = 2·10·10·(1 − (−1)) = 400
    df2 = pd.DataFrame({"pt1": [10.0], "eta1": [0.0], "phi1": [0.0], "pt2": [10.0], "eta2": [0.0], "phi2": [np.pi]})
    d2, aj2 = am.grandeurs_derivees(df2)
    assert aj2 == ["M_paire"] and abs(d2["M_paire"][0] - 20.0) < 1e-9
    # une masse déjà présente : rien n'est ajouté
    df3 = df.assign(M=[20.0])
    assert am.grandeurs_derivees(df3)[1] == []


def test_colonnes_analysables_masses_d_abord_charges_en_dernier():
    cols = ["Run", "Event", "type1", "E1", "px1", "py1", "pz1", "pt1", "eta1", "phi1", "Q1", "M"]
    ordre = am.colonnes_analysables(cols)
    assert ordre[0] == "M" and ordre[1] == "pt1" and ordre[-1] == "Q1"
    assert "Run" not in ordre and "Event" not in ordre
