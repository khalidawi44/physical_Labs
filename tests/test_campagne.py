"""Tests du mode campagne : l'outil analyse seul un dossier de runs et rend des verdicts calculés."""
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import anemone_master as am  # noqa: E402
import anemone_campagne as ac  # noqa: E402


def _fond(rng, n):
    return pd.DataFrame({
        "Energie_MeV": rng.normal(4.0, 0.4, n),
        "Temps_ns": rng.uniform(0, 100, n),
        "Angle_diffusion": rng.normal(0, 1.0, n),
        "Temperature_C": rng.normal(20.0, 0.3, n),
    })


def _run_signal(rng, n=1200, n_ano=40):
    """Anomalies en énergie seulement, réparties sur tout le run, température normale : signal propre."""
    df = _fond(rng, n)
    ano = _fond(rng, n_ano)
    ano["Energie_MeV"] = rng.uniform(9.0, 15.0, n_ano)
    return pd.concat([df, ano], ignore_index=True)


@pytest.fixture(scope="module")
def dossier_runs(tmp_path_factory):
    d = tmp_path_factory.mktemp("runs")
    rng = np.random.default_rng(7)
    _run_signal(rng).to_csv(d / "run_signal.csv", index=False)
    am.generer_donnees_demo(seed=3).to_csv(d / "run_biais_thermique.csv", index=False)   # anomalies corrélées à la température
    _fond(rng, 1200).to_csv(d / "run_fond_seul.csv", index=False)
    _fond(rng, 40).to_csv(d / "run_minuscule.csv", index=False)
    (d / "run_corrompu.csv").write_text("ceci n'est pas une matrice\n;;;\n")
    (d / ".cache.csv").write_text("a,b\n1,2\n")  # caché : ignoré
    (d / "notes.txt.bak").write_text("x")       # extension non admise
    _fond(np.random.default_rng(99), 1500).to_csv(d / "reference_calibration.csv", index=False)
    return d


def test_lister_fichiers_ignore_caches_et_extensions(dossier_runs):
    noms = [os.path.basename(c) for c in ac.lister_fichiers(str(dossier_runs))]
    assert ".cache.csv" not in noms and "notes.txt.bak" not in noms
    assert "run_signal.csv" in noms and "reference_calibration.csv" in noms
    assert noms == sorted(noms)


def test_verdicts_calcules(dossier_runs):
    chemins = [str(dossier_runs / n) for n in
               ("run_signal.csv", "run_biais_thermique.csv", "run_fond_seul.csv", "run_minuscule.csv", "run_corrompu.csv")]
    res = ac.analyser_campagne(chemins, contamination=0.03, seed=42)
    par_nom = {r.fichier: r for r in res}

    s = par_nom["run_signal.csv"]
    assert s.verdict == "solide", s.motifs
    assert s.dominante == "Energie_MeV" and s.p_value < 1e-3 and abs(s.d_cohen) >= 1
    assert s.stabilite >= ac.SEUIL_STABILITE and s.dominante_stable
    assert s.exces_fond >= ac.SEUIL_EXCES_FOND
    assert len(s.sha256) == 64 and s.n_evenements == 1240

    b = par_nom["run_biais_thermique.csv"]
    assert b.verdict == "suspect_biais", b.motifs
    # la démo concentre ses anomalies dans une fenêtre temporelle (25–75 ns sur 0–100) : épisode transitoire
    assert b.correlation_suspecte is not None or b.fraction_fenetre_temporelle < ac.SEUIL_TRANSITOIRE

    f = par_nom["run_fond_seul.csv"]
    assert f.verdict in ("queues_du_fond", "faible", "fragile"), f.motifs
    assert f.verdict != "solide"

    m = par_nom["run_minuscule.csv"]
    assert m.verdict == "insuffisant"

    c = par_nom["run_corrompu.csv"]
    assert c.verdict == "erreur" and c.erreur

    # classement : solide d'abord, erreur en dernier
    assert res[0].fichier == "run_signal.csv"
    assert res[-1].fichier == "run_corrompu.csv"
    assert [r.verdict for r in res] == sorted((r.verdict for r in res), key=lambda v: ac.PRIORITE[v])


def test_reference_ajoute_derive_et_exces(dossier_runs):
    ref = ac.charger_reference(str(dossier_runs / "reference_calibration.csv"))
    r = ac.analyser_un_fichier(str(dossier_runs / "run_signal.csv"), reference=ref, balayage=False)
    assert "Energie_MeV" in r.derive_reference
    assert r.derive_reference["Energie_MeV"]["p_value"] <= 1.0
    assert np.isfinite(r.exces_reference) and r.exces_reference > 1.0
    assert any("référence" in m for m in r.motifs)


def test_rapport_et_graphe(dossier_runs, tmp_path):
    chemins = [str(dossier_runs / n) for n in ("run_signal.csv", "run_minuscule.csv")]
    params = {"contamination": 0.03, "seed": 42, "variables": None}
    res = ac.analyser_campagne(chemins, balayage=False)
    dossier = ac.ecrire_rapport(res, str(tmp_path / "rapports"), params)
    assert os.path.isfile(os.path.join(dossier, "rapport.md"))
    assert os.path.isfile(os.path.join(dossier, "resultats.csv"))
    with open(os.path.join(dossier, "resultats.json"), encoding="utf-8") as f:
        data = json.load(f)
    assert data["provenance"]["outil"].startswith("A.N.E.M.O.N.E")
    assert data["provenance"]["seuils"]["p_verrou"] == am.Architecte.SEUIL_P_VERROU
    assert {r["fichier"] for r in data["resultats"]} == {"run_signal.csv", "run_minuscule.csv"}
    assert all(len(r["sha256"]) == 64 for r in data["resultats"])
    texte = open(os.path.join(dossier, "rapport.md"), encoding="utf-8").read()
    assert "À regarder en premier" in texte and "run_signal.csv" in texte and "Provenance" in texte

    g = am.GrapheConnaissances()
    ident = ac.consigner_dans_graphe(g, res, params, dossier)
    assert g.noeud(ident)["type"] == "campagne"
    verdicts = g.par_type("verdict")
    assert len(verdicts) == 2
    assert all(any(rel == "issu_de" and autre == ident for rel, autre, _ in g.voisins(v["id"])) for v in verdicts)
    g.sauvegarder(str(tmp_path / "g.json"))
    assert am.GrapheConnaissances.charger(str(tmp_path / "g.json")).statistiques()["campagne"] == 1


def test_ligne_de_commande(dossier_runs, tmp_path):
    graphe = tmp_path / "graphe.json"
    r = subprocess.run(
        [sys.executable, os.path.join(RACINE, "anemone_campagne.py"), str(dossier_runs),
         "--sans-balayage", "--sortie", str(tmp_path / "rapports"), "--graphe", str(graphe),
         "--reference", str(dossier_runs / "reference_calibration.csv")],
        capture_output=True, text=True, timeout=600, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Rapport :" in r.stdout and "run_signal.csv" in r.stdout
    assert graphe.exists()
    g = am.GrapheConnaissances.charger(str(graphe))
    assert g.statistiques()["campagne"] == 1 and g.statistiques()["verdict"] >= 5


def test_interface_campagne(dossier_runs, tmp_path, monkeypatch):
    """La section campagne de l'application analyse un dossier et affiche les verdicts."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    at.text_input(key="campagne_dossier").set_value(str(dossier_runs)).run()
    at.checkbox(key="campagne_balayage").set_value(False).run()
    at.button(key="campagne_lancer").click().run()
    assert not at.exception, at.exception
    assert "campagne_resultats" in at.session_state
    verdicts = {r["fichier"]: r["verdict"] for r in at.session_state["campagne_resultats"]}
    assert verdicts["run_signal.csv"] == "solide"
    assert verdicts["run_corrompu.csv"] == "erreur"
    g = am.GrapheConnaissances.from_dict(at.session_state["graphe"])
    assert g.statistiques()["campagne"] == 1
    assert os.path.isdir(tmp_path / "rapports")
