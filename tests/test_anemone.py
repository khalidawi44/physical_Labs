# -*- coding: utf-8 -*-
"""Tests du cœur A.N.E.M.O.N.E : lecture .csv/.root, isolation, graphe, Architecte, interface."""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import anemone_master as am  # noqa: E402


@pytest.fixture(scope="module")
def matrice_demo():
    df, rapport = am.nettoyer_matrice(am.generer_donnees_demo())
    return df


# ----------------------------------------------------------------- lecture

def test_lecture_csv_exemple():
    chemin = os.path.join(RACINE, "exemples", "detecteur_demo.csv")
    df, rapport = am.analyser_fichier_physique(chemin, "detecteur_demo.csv")
    assert rapport["format"] == "csv"
    assert rapport["n_evenements"] == 1240
    assert set(df.columns) == {"Energie_MeV", "Temps_ns", "Angle_diffusion", "Temperature_C"}


def test_lecture_csv_depuis_octets_avec_colonnes_non_numeriques():
    texte = "run,detecteur,E,t\n1,A,4.1,10\n2,B,4.3,20\n3,A,,30\n4,C,12.0,40\n"
    df, rapport = am.analyser_fichier_physique(texte.encode(), "mesures.csv")
    assert rapport["colonnes_non_numeriques"] == ["detecteur"]
    assert rapport["lignes_retirees"] == 1
    assert list(df.columns) == ["run", "E", "t"]


def test_lecture_tsv_separateur_auto():
    texte = "E\tt\n4.1\t10\n4.2\t20\n9.0\t30\n"
    df, _ = am.analyser_fichier_physique(texte.encode(), "mesures.tsv")
    assert df.shape == (3, 2)


def test_format_inconnu():
    with pytest.raises(ValueError):
        am.analyser_fichier_physique(b"x", "mesures.xlsx")


@pytest.mark.skipif(not am.UPROOT_DISPONIBLE, reason="uproot absent")
def test_lecture_root_ttree(tmp_path):
    import uproot

    chemin = tmp_path / "run.root"
    rng = np.random.default_rng(0)
    with uproot.recreate(chemin) as f:
        # TTree classique (mktree) + RNTuple (affectation directe, format par défaut d'uproot ≥ 5.7).
        arbre = f.mktree("events", {"E": np.float64, "t": np.float64, "nhits": np.int32})
        arbre.extend({
            "E": rng.normal(4, 0.4, 500),
            "t": np.arange(500, dtype=np.float64),
            "nhits": rng.integers(0, 50, 500).astype(np.int32),
        })
        f["autre"] = {"x": rng.normal(size=10)}
    assert sorted(am.lister_arbres_root(str(chemin))) == ["autre", "events"]
    df_rn, _ = am.analyser_fichier_physique(str(chemin), "run.root", arbre="autre")
    assert df_rn.shape == (10, 1)
    df, rapport = am.analyser_fichier_physique(str(chemin), "run.root", arbre="events")
    assert rapport["format"] == "root" and rapport["arbre"] == "events"
    assert df.shape == (500, 3)
    # Lecture depuis des octets (cas du téléversement) + limitation d'événements.
    df2, _ = am.analyser_fichier_physique(chemin.read_bytes(), "run.root", arbre="events", max_evenements=100)
    assert len(df2) == 100
    with pytest.raises(ValueError):
        am.analyser_fichier_physique(str(chemin), "run.root", arbre="inexistant")


# ----------------------------------------------------------------- isolation + diagnostic

def test_isolation_retrouve_les_anomalies_injectees(matrice_demo):
    res = am.detecter_inconnu(matrice_demo, matrice_demo.columns, contamination=0.03)
    assert set(res["Inconnu"].unique()) == {-1, 1}
    anomalies = res[res["Inconnu"] == -1]
    # Les 40 événements injectés ont une énergie > 9 MeV ; la forêt doit les isoler en majorité.
    assert (anomalies["Energie_MeV"] > 9).mean() > 0.8
    assert (res["Score_anomalie"][res["Inconnu"] == -1].mean()) > (res["Score_anomalie"][res["Inconnu"] == 1].mean())


def test_diagnostic_chiffres_calcules(matrice_demo):
    res = am.detecter_inconnu(matrice_demo, matrice_demo.columns)
    diag = am.diagnostiquer(res, matrice_demo.columns)
    assert not diag["insuffisant"]
    assert am.variable_dominante(diag) in ("Energie_MeV", "Temperature_C")
    v = diag["variables"]["Energie_MeV"]
    assert v["p_value"] < 1e-3 and abs(v["d_cohen"]) > 1
    assert 0 <= diag["geometrie"]["variance_expliquee_axe1"] <= 1
    assert diag["roles"] == {"temps": "Temps_ns", "energie": "Energie_MeV", "temperature": "Temperature_C"}


def test_diagnostic_insuffisant():
    df = pd.DataFrame({"a": np.arange(5.0), "b": np.arange(5.0) ** 2})
    res = df.copy(); res["Inconnu"] = [1, 1, 1, 1, -1]; res["Score_anomalie"] = 0.0
    assert am.diagnostiquer(res, ["a", "b"])["insuffisant"] is True


# ----------------------------------------------------------------- graphe

def test_graphe_persistance_json(tmp_path):
    g = am.GrapheConnaissances()
    a = g.ajouter_noeud("observation", "pic à 12 MeV")
    b = g.ajouter_noeud("objection", "effet thermique ?")
    g.ajouter_arete(b, a, "conteste")
    with pytest.raises(KeyError):
        g.ajouter_arete(b, "inconnu-0000", "x")
    with pytest.raises(ValueError):
        g.ajouter_noeud("blague", "…")
    chemin = tmp_path / "g.json"
    g.sauvegarder(str(chemin))
    g2 = am.GrapheConnaissances.charger(str(chemin))
    assert g2.to_dict() == g.to_dict()
    assert g2.voisins(a) == [("conteste", b, "entrante")]
    assert g2.statistiques()["aretes"] == 1
    assert g2.vers_networkx().number_of_edges() == 1
    # Aller-retour par dict (forme stockée dans st.session_state).
    assert am.GrapheConnaissances.from_dict(json.loads(g.to_json())).dernier("objection")["id"] == b


# ----------------------------------------------------------------- architecte

def test_architecte_relie_ses_repliques_et_verrouille(matrice_demo):
    res = am.detecter_inconnu(matrice_demo, matrice_demo.columns)
    diag = am.diagnostiquer(res, matrice_demo.columns)
    g = am.GrapheConnaissances()
    arch = am.Architecte(g, diag, physicien="Frédéric")

    obs = arch.enregistrer_observation("Je vois un neutrino stérile à 12 MeV.")
    texte_obj = arch.objection(obs)
    assert "OBJECTION" in texte_obj and "Frédéric" in texte_obj
    assert texte_obj.count("94%") == 0  # aucun chiffre inventé : tout vient du diagnostic
    texte_hyp = arch.hypothese(obs)
    assert "HYPOTHÈSE" in texte_hyp
    texte_def, verrou = arch.defense()
    assert verrou is True and "verrouillée" in texte_def
    arch.refutation("En retirant la température, l'isolement persiste : ta thèse tient, mais pas ton objection.")

    st = g.statistiques()
    assert st["observation"] == 1 and st["objection"] == 1 and st["hypothese"] == 1
    assert st["defense"] == 1 and st["refutation"] == 1 and st["anomalies"] == 1
    relations = {(a["relation"], g.noeud(a["source"])["type"], g.noeud(a["cible"])["type"]) for a in g.aretes}
    assert ("conteste", "objection", "observation") in relations
    assert ("defend", "defense", "hypothese") in relations
    assert ("refute", "refutation", "defense") in relations
    assert ("porte_sur", "observation", "anomalies") in relations
    # Le nœud « anomalies » est partagé tant que le diagnostic ne change pas.
    assert len(g.par_type("anomalies")) == 1


def test_architecte_cede_sans_preuve():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(size=300), "b": rng.normal(size=300)})
    res = am.detecter_inconnu(df, ["a", "b"], contamination=0.05)
    # On brouille les étiquettes pour qu'aucune séparation ne subsiste.
    res["Inconnu"] = rng.choice([1, -1], size=300, p=[0.9, 0.1])
    diag = am.diagnostiquer(res, ["a", "b"])
    g = am.GrapheConnaissances()
    texte, verrou = am.Architecte(g, diag).defense()
    assert verrou is False and "je cède" in texte


# ----------------------------------------------------------------- interface (AppTest Streamlit)

def test_interface_demo_debat_et_graphe(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)  # la sauvegarde auto écrit anemone_graphe.json ici
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=120)
    at.run()
    assert not at.exception
    at.sidebar.radio[0].set_value("Démo synthétique (aucune valeur physique)").run()
    assert not at.exception
    assert any("SYNTHÉTIQUES" in w.value for w in at.warning)
    assert int(at.metric[1].value) > 0

    at.text_input(key="saisie_debat").set_value("Je pense que le pic d'énergie isole un neutrino stérile.")
    at.button(key="FormSubmitter:debat-⚠️ Objection").click().run()
    assert not at.exception
    graphe = am.GrapheConnaissances.from_dict(at.session_state["graphe"])
    stats = graphe.statistiques()
    assert stats["observation"] == 1 and stats["objection"] == 1 and stats["jeu_de_donnees"] == 1
    assert os.path.exists(tmp_path / "anemone_graphe.json")

    at.button(key="FormSubmitter:debat-🛡️ Preuves").click().run()  # → verrouillage
    assert at.session_state["verrou"] is True
    assert any("VERROUILLÉ" in e.value for e in at.error)
    at.text_area(key="saisie_refutation").set_value("Réfutation : p = 0.4 une fois la température retirée.")
    at.button(key="FormSubmitter:refutation-🔓 Soumettre la réfutation").click().run()
    assert at.session_state["verrou"] is False
    graphe = am.GrapheConnaissances.from_dict(at.session_state["graphe"])
    assert graphe.statistiques()["refutation"] == 1


@pytest.mark.skipif(not am.UPROOT_DISPONIBLE, reason="uproot absent")
def test_interface_chemin_local_root(tmp_path, monkeypatch):
    import uproot
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)
    rng = np.random.default_rng(3)
    chemin = tmp_path / "run_42.root"
    n = 400
    with uproot.recreate(chemin) as f:
        f["events"] = {
            "energy_MeV": np.concatenate([rng.normal(4, 0.4, n - 20), rng.uniform(9, 15, 20)]),
            "time_ns": rng.uniform(0, 100, n),
            "temperature_C": np.concatenate([rng.normal(20, 0.3, n - 20), rng.uniform(27, 43, 20)]),
        }
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value("Chemin local").run()
    at.sidebar.text_input[1].set_value(str(chemin)).run()
    assert not at.exception, at.exception
    assert at.sidebar.selectbox[0].value == "events"
    assert int(at.metric[0].value) == n
    assert at.metric[2].value in ("energy_MeV", "temperature_C")
    graphe = am.GrapheConnaissances.from_dict(at.session_state["graphe"])
    jeu = graphe.dernier("jeu_de_donnees")
    assert jeu["meta"]["format"] == "root" and jeu["meta"]["arbre"] == "events"
