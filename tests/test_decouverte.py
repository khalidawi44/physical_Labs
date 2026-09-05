# -*- coding: utf-8 -*-
"""Run de découverte : thèse seulement si une bosse étroite sur une masse passe toutes les épreuves et n'est pas connue."""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import anemone_decouverte as ad  # noqa: E402
import anemone_bosse as ab  # noqa: E402


def _run_csv(chemin, rng, pic=None, n=60000, masse="M"):
    x = rng.exponential(10.0, n) + 1.0
    if pic is not None:
        x = np.r_[x, rng.normal(pic[0], pic[1], pic[2])]
    rng.shuffle(x)
    pd.DataFrame({"Run": np.repeat([100, 200], [len(x) // 2, len(x) - len(x) // 2]), "Event": np.arange(len(x)),
                  masse: x, "pt1": rng.exponential(5, len(x))}).to_csv(chemin, index=False)
    return str(chemin)


def test_these_candidate_sur_un_pic_inconnu(tmp_path):
    rng = np.random.default_rng(10)
    chemin = _run_csv(tmp_path / "run_a.csv", rng, pic=(42.0, 0.6, 500))
    run = ad.lancer_run([chemin])
    assert run.conclusion == "these"
    c = run.candidats[0]
    assert c["verdict"] == "these" and c["bosse"]["variable"] == "M" and abs(c["bosse"]["centre"] - 42.0) < 1.0
    assert all(e["ok"] for nom, e in c["epreuves"].items() if nom != "reference")
    assert c["epreuves"]["reference"]["ok"] is None
    assert "THÈSE CANDIDATE" in run.resume
    texte = ad.rediger_these(run)
    assert "THÈSE CANDIDATE" in texte and "SHA-256" in texte and "À faire par le physicien" in texte
    chemin_these = ad.ecrire_these(run, str(tmp_path / "theses"))
    assert os.path.isfile(chemin_these) and os.path.isfile(chemin_these.replace(".md", ".json"))


def test_pic_connu_est_une_validation_pas_une_these(tmp_path):
    rng = np.random.default_rng(11)
    chemin = _run_csv(tmp_path / "run_y.csv", rng, pic=(9.4604, 0.12, 800))      # Υ(1S), masse PDG
    run = ad.lancer_run([chemin])
    assert run.conclusion == "connue"
    assert run.candidats[0]["verdict"] == "connue" and "Υ(1S)" in run.candidats[0]["connue"]


def test_pic_present_dans_la_reference_est_ecarte(tmp_path):
    rng = np.random.default_rng(12)
    chemin = _run_csv(tmp_path / "run_b.csv", rng, pic=(42.0, 0.6, 500))
    reference = _run_csv(tmp_path / "calibration.csv", rng, pic=(42.0, 0.6, 500))
    run = ad.lancer_run([chemin], reference=reference)
    assert run.conclusion != "these"
    c = run.candidats[0]
    assert c["verdict"] == "ecarte" and c["epreuves"]["reference"]["ok"] is False


def test_pic_sur_une_moitie_seulement_est_ecarte(tmp_path):
    rng = np.random.default_rng(13)
    x = rng.exponential(10.0, 60000) + 1.0
    pic = rng.normal(42.0, 0.6, 500)
    x = np.r_[pic, x]                                          # tout le pic dans la première moitié (Run 100)
    runs = np.r_[np.full(30500, 100), np.full(30000, 200)]
    chemin = tmp_path / "episode.csv"
    pd.DataFrame({"Run": runs, "Event": np.arange(len(x)), "M": x}).to_csv(chemin, index=False)
    run = ad.lancer_run([str(chemin)])
    assert run.conclusion != "these"
    c = [c for c in run.candidats if abs(c["bosse"]["centre"] - 42.0) < 1.0][0]
    assert c["epreuves"]["deux_moities"]["ok"] is False and c["verdict"] == "ecarte"


def test_rien_sur_un_fond_lisse_et_hypothese_non_soutenue(tmp_path):
    rng = np.random.default_rng(14)
    chemin = _run_csv(tmp_path / "plat.csv", rng)
    run = ad.lancer_run([chemin], ad.analyser_hypothese("M ~ 42 ± 1"))
    assert run.conclusion in ("rien", "indice")
    assert not any(c["verdict"] == "these" for c in run.candidats)
    assert run.tests_hypothese and run.tests_hypothese[0]["soutenue"] is False


def test_hypothese_localisee_soutenue_sans_facteur_d_essais(tmp_path):
    rng = np.random.default_rng(15)
    chemin = _run_csv(tmp_path / "run_h.csv", rng, pic=(42.0, 0.6, 500))
    h = ad.analyser_hypothese("Je pense à une résonance : M ~ 42 ± 1,5")
    assert h.variable == "M" and h.valeur == 42.0 and h.demi_largeur == 1.5
    run = ad.lancer_run([chemin], h)
    t = run.tests_hypothese[0]
    assert t["soutenue"] is True and t["p_local"] < ab.P_CINQ_SIGMA
    assert "Test de l'hypothèse" in ad.rediger_these(run)


def test_variable_hors_masse_donne_une_structure_pas_une_these(tmp_path):
    rng = np.random.default_rng(16)
    x = np.r_[rng.exponential(10.0, 60000) + 1.0, rng.normal(42.0, 0.6, 500)]
    rng.shuffle(x)
    chemin = tmp_path / "sans_masse.csv"
    pd.DataFrame({"Run": 1, "Event": np.arange(len(x)), "pt": x, "eta": rng.normal(size=len(x))}).to_csv(chemin, index=False)
    run = ad.lancer_run([str(chemin)])
    assert run.conclusion == "indice"
    assert run.candidats[0]["verdict"] == "structure" and run.candidats[0]["bosse"]["variable"] == "pt"


def test_ligne_de_commande(tmp_path, capsys):
    rng = np.random.default_rng(17)
    _run_csv(tmp_path / "d" / "r1.csv", rng, pic=(42.0, 0.6, 500)) if (tmp_path / "d").mkdir() is None else None
    code = ad.main([str(tmp_path / "d"), "--hypothese", "M ~ 42", "--sortie", str(tmp_path / "theses")])
    assert code == 0
    sortie = capsys.readouterr().out
    assert "THÈSE CANDIDATE" in sortie and "Thèse :" in sortie
    assert any(f.endswith(".json") for f in os.listdir(tmp_path / "theses"))


def test_interface_run_de_decouverte(tmp_path, monkeypatch):
    """Un clic : hypothèse, données chargées, run, thèse écrite et affichée, consignée dans le graphe."""
    from streamlit.testing.v1 import AppTest
    import anemone_master as am

    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    assert at.radio(key="run_source").options == ["Toutes les données réelles du CERN (téléchargement automatique, ~80 Mo)"]
    at.button(key="demarrage_demo").click().run()
    assert at.radio(key="run_source").options[0] == "Fichier chargé"
    at.text_input(key="run_hypothese").set_value("Energie_MeV ~ 12 ± 3").run()
    at.button(key="run_lancer").click().run()
    assert not at.exception, at.exception
    assert os.path.isdir(tmp_path / "theses") and any(f.endswith(".md") for f in os.listdir(tmp_path / "theses"))
    run = at.session_state["run_decouverte"]["run"]
    assert run["conclusion"] != "these"                          # la démo synthétique n'a pas de résonance
    assert run["tests_hypothese"] and run["tests_hypothese"][0]["variable"] == "Energie_MeV"
    g = am.GrapheConnaissances.from_dict(at.session_state["graphe"])
    assert any(n["texte"].startswith("Run de découverte") for n in g.par_type("verdict"))
    assert any(b.key == "run_telecharger" for b in at.get("download_button"))


def test_cumul_des_runs_revele_un_pic_invisible_run_par_run(tmp_path):
    rng = np.random.default_rng(21)
    chemins = []
    for i in range(6):
        x = np.r_[rng.exponential(10.0, 30000) + 1.0, rng.normal(42.0, 0.6, 45)]      # 45 événements : trop peu par run
        rng.shuffle(x)
        c = tmp_path / f"run_{i}.csv"
        pd.DataFrame({"Run": 100 + i, "Event": np.arange(len(x)), "M": x}).to_csv(c, index=False)
        chemins.append(str(c))
    run = ad.lancer_run(chemins)
    par_run = [c for c in run.candidats if c["fichier"].startswith("run_") and c["verdict"] == "these"]
    cumul = [c for c in run.candidats if c["fichier"].startswith("CUMUL") and abs(c["bosse"]["centre"] - 42.0) < 1.0]
    assert cumul and cumul[0]["verdict"] == "these"
    assert cumul[0]["cumul"] and len(cumul[0]["cumul"]) == 6
    z = [pt["z"] for pt in cumul[0]["cumul"]]
    assert z[-1] > z[0]                                                   # la significativité croît avec les runs
    assert len(par_run) < 6                                               # au moins un run seul ne suffisait pas
    assert "run après run" in ad.rediger_these(run)
    sans = ad.lancer_run(chemins, cumul=False)
    assert not any(c["fichier"].startswith("CUMUL") for c in sans.candidats)
