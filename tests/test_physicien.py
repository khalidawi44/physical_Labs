"""Tests d'Albert : apprentissage des relations, base de connaissances, débat, recherche autonome, modes."""
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
import anemone_physicien as ap  # noqa: E402


def _cinematique(rng, n=3000, n_ano=90, masse=0.106):
    """Un « muon » : E² = px² + py² + pz² + m², pt² = px² + py². Anomalies : muons à très haute impulsion
    transverse (≈ 3 % des événements, comme le taux de contamination). Fond à pseudo-rapidité modérée,
    sinon ses queues en énergie (cosh η) sont aussi extrêmes que le signal et le verdict, à juste titre,
    n'est pas « solide »."""
    def muon(k, pt_lo, pt_hi):
        pt = rng.uniform(pt_lo, pt_hi, k)
        phi = rng.uniform(-np.pi, np.pi, k)
        eta = rng.normal(0, 0.5, k)
        px, py, pz = pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
        e = np.sqrt(px ** 2 + py ** 2 + pz ** 2 + masse ** 2)
        return {"E": e, "px": px, "py": py, "pz": pz, "pt": pt, "eta": eta, "phi": phi}
    fond = muon(n, 2.0, 12.0)
    ano = muon(n_ano, 40.0, 60.0)
    df = pd.DataFrame({"Run": 1, "Event": np.arange(n + n_ano)})
    for k in ("E", "px", "py", "pz", "pt", "eta", "phi"):
        df[f"{k}1"] = np.concatenate([fond[k], ano[k]])
    df["Temperature_C"] = rng.normal(20, 0.3, n + n_ano)
    df["iso1"] = rng.uniform(0, 1, n + n_ano)   # 9ᵉ grandeur : la stratégie « toutes les grandeurs » existe
    return df


def _biais_thermique(rng, n=1200, n_ano=40):
    df = pd.DataFrame({"Energie_MeV": rng.normal(4.0, 0.4, n), "Temps_ns": rng.uniform(0, 100, n),
                       "Angle": rng.normal(0, 1, n), "Temperature_C": rng.normal(20.0, 0.3, n)})
    t = rng.uniform(26, 40, n_ano)
    ano = pd.DataFrame({"Energie_MeV": 4.0 + 0.5 * (t - 20) + rng.normal(0, 0.3, n_ano), "Temps_ns": rng.uniform(0, 100, n_ano),
                        "Angle": rng.normal(0, 1, n_ano), "Temperature_C": t})
    return pd.concat([df, ano], ignore_index=True)


# ----------------------------------------------------------------- apprentissage depuis les données

def test_relations_fonctionnelles_retrouve_les_identites():
    df = _cinematique(np.random.default_rng(1))
    rels = ap.relations_fonctionnelles(df)
    ensembles = [set(r["variables"]) for r in rels]
    # E² = px² + py² + pz² + m², ou sa forme équivalente E² = pt² + pz² + m² (les deux sont exactes)
    assert {"E1", "px1", "py1", "pz1"} in ensembles or {"E1", "pt1", "pz1"} in ensembles, ensembles
    assert {"pt1", "px1", "py1"} in ensembles                  # pt² = px² + py²
    assert all(r["r2"] >= ap.SEUIL_R2 for r in rels)
    cibles = {frozenset(r["variables"]): r["cible"] for r in rels}
    assert cibles.get(frozenset({"pt1", "px1", "py1"})) == "pt1"                       # la grandeur composée
    assert cibles.get(frozenset({"E1", "px1", "py1", "pz1"}), cibles.get(frozenset({"E1", "pt1", "pz1"}))) == "E1"
    assert all("Run" not in r["variables"] and "Event" not in r["variables"] for r in rels)
    assert not any("Temperature_C" in r["variables"] for r in rels)   # indépendante : aucune relation inventée


def test_colonnes_csv_nettoyees(tmp_path):
    (tmp_path / "x.csv").write_text("Run,Event,px1 ,E1\n1,1,2.0,3.0\n1,2,4.0,5.0\n")
    m, _ = am.analyser_fichier_physique(str(tmp_path / "x.csv"), "x.csv")
    assert "px1" in m.columns and "px1 " not in m.columns


def test_relations_fonctionnelles_rien_sur_du_bruit():
    rng = np.random.default_rng(2)
    df = pd.DataFrame({c: rng.normal(size=2000) for c in ("a", "b", "c", "d")})
    assert ap.relations_fonctionnelles(df) == []
    assert ap.variables_apparentees(df) == []


def test_connaissances_persistance_questions_et_modes(tmp_path):
    c = ap.Connaissances()
    rel = c.ajouter_relation(["E1", "px1", "py1", "pz1"], "fonctionnelle", "E1² ≈ …", ap.Albert.NOM, "run.csv", cible="E1")
    assert rel and c.ajouter_relation(["pz1", "E1", "px1", "py1"], "fonctionnelle", "doublon", ap.Albert.NOM) is None
    assert frozenset(("E1", "pz1")) in c.paires_connues()
    assert c.paires_connues(sans_albert=True) == set()            # mode « Fred seul » : Albert ignoré
    q = c.ajouter_question(["pt1", "pz1"], "corrélées chez les isolés seulement", "run.csv")
    assert q["statut"] == "ouverte" and c.ajouter_question(["pz1", "pt1"], "encore", "x")["id"] == q["id"]
    c.repondre(q["id"], "relation_connue", "Fred")
    assert not c.questions_ouvertes() and frozenset(("pt1", "pz1")) in c.paires_connues(sans_albert=True)
    q2 = c.ajouter_question(["a", "b"], "?", None)
    c.repondre(q2["id"], "biais", "Fred")
    assert frozenset(("a", "b")) not in c.paires_connues()
    assert c.variables_deduites() == {"E1"}
    chemin = str(tmp_path / "connaissances.json")
    c.sauvegarder(chemin)
    c2 = ap.Connaissances.charger(chemin)
    assert c2.resume() == c.resume() and c2.paires_connues() == c.paires_connues()
    assert ap.Connaissances.charger(str(tmp_path / "absent.json")).resume()["relations"] == 0


# ----------------------------------------------------------------- l'outil apprend

def test_architecte_et_campagne_respectent_les_relations_connues():
    rng = np.random.default_rng(3)
    therm = _biais_thermique(rng)
    cols = list(therm.columns)
    res = am.detecter_inconnu(therm, cols, 0.03, 42)
    diag = am.diagnostiquer(res, cols)
    dom = am.variable_dominante(diag)
    connues = {frozenset(("Energie_MeV", "Temperature_C"))}
    fortes = am.correlations_fortes(diag, dom, connues=connues)
    assert fortes and fortes[0]["nature"] == "connue"
    texte = am.Architecte(am.GrapheConnaissances(), diag, paires_connues=connues).objection()
    assert "enseignée comme connue" in texte and "thermique" not in texte
    q = ac.qualifier(diag, None, None, paires_connues=connues)
    assert q["verdict"] != "suspect_biais" or q["fraction_fenetre_temporelle"] < ac.SEUIL_TRANSITOIRE
    assert any("relation connue" in m for m in q["motifs"])


# ----------------------------------------------------------------- Albert débat

def test_albert_apprend_refute_et_demande():
    rng = np.random.default_rng(4)
    c = ap.Connaissances()
    albert = ap.Albert(c)
    g = am.GrapheConnaissances()
    cine = _cinematique(rng)
    lecon = albert.entrainer(cine, am.colonnes_analysables(list(cine.columns))[:8], g, "cinematique.csv")
    assert lecon["relations_apprises"] and c.resume()["relations"] >= 2
    assert lecon["dominante"] in ("E1", "pt1", "px1", "py1", "pz1")
    assert not lecon["questions"]                                  # rien d'inexplicable : il ne dérange pas le physicien
    assert g.statistiques()["refutation"] == len(lecon["refutations"]) and g.statistiques()["observation"] == 1

    therm = _biais_thermique(rng)
    lecon2 = albert.entrainer(therm, list(therm.columns), g, "thermique.csv")
    assert lecon2["questions"] and c.questions_ouvertes()          # il ne tranche pas : il demande
    assert "thermique" in lecon2["objection"] and not lecon2["refutations"]
    assert "Leçon sur thermique.csv" in ap.resume_lecon(lecon2)

    # le physicien répond une fois : dès la leçon suivante, Albert réfute lui-même avec la relation connue
    c.repondre(c.questions_ouvertes()[0]["id"], "relation_connue", "Fred")
    lecon3 = albert.entrainer(therm, list(therm.columns), g, "thermique.csv")
    assert lecon3["refutations"] and not lecon3["questions"] and not c.questions_ouvertes()
    assert "relation connue" in lecon3["refutations"][0] and "enseignée comme connue" in lecon3["objection"]
    assert g.statistiques()["refutation"] == len(lecon["refutations"]) + len(lecon3["refutations"])


def test_albert_cherche_seul_et_ecrit_son_cahier(tmp_path):
    rng = np.random.default_rng(5)
    dossier = tmp_path / "runs"
    dossier.mkdir()
    _cinematique(rng).to_csv(dossier / "run_signal.csv", index=False)
    _cinematique(rng, n_ano=0).to_csv(dossier / "run_fond.csv", index=False)
    _cinematique(np.random.default_rng(99), n=4000, n_ano=0).to_csv(tmp_path / "calibration.csv", index=False)
    (dossier / "cassé.csv").write_text("pas une matrice")
    c = ap.Connaissances()
    albert = ap.Albert(c)
    g = am.GrapheConnaissances()
    etapes = []
    cahier = albert.chercher(ac.lister_fichiers(str(dossier)), str(tmp_path / "calibration.csv"), g,
                             str(tmp_path / "cahier"), rappel=lambda *a: etapes.append(a[0]))
    assert os.path.isfile(cahier["chemin"]) and cahier["chemin"].endswith(".md")
    assert os.path.isfile(cahier["chemin"][:-3] + ".json")
    assert len(cahier["strategies"]) >= 2                          # défaut + primitives (relations apprises) au moins
    assert "run_signal.csv" in cahier["verdicts"] and "run_fond.csv" in cahier["verdicts"]
    assert any(l.get("erreur") for l in cahier["lecons"])          # le fichier cassé n'arrête pas Albert
    assert cahier["trouvailles"] and cahier["trouvailles"][0]["fichier"] == "run_signal.csv", cahier["verdicts"]
    assert all(t["fichier"] != "run_fond.csv" for t in cahier["trouvailles"])
    texte = open(cahier["chemin"], encoding="utf-8").read()
    assert "Cahier de laboratoire de Albert" in texte and "run_signal.csv" in texte and "Ce que j'ai tenté" in texte
    assert "leçon" in etapes and "stratégie" in etapes
    assert g.statistiques()["campagne"] == len(cahier["strategies"])
    assert c.lecons and c.lecons[-1]["type"] == "recherche"


def test_ligne_de_commande_albert(tmp_path):
    rng = np.random.default_rng(6)
    dossier = tmp_path / "runs"
    dossier.mkdir()
    _cinematique(rng, n=1500).to_csv(dossier / "a.csv", index=False)
    conn = tmp_path / "conn.json"
    r = subprocess.run([sys.executable, os.path.join(RACINE, "anemone_physicien.py"), "--chercher", str(dossier),
                        "--connaissances", str(conn), "--graphe", str(tmp_path / "g.json")],
                       capture_output=True, text=True, timeout=900, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[ALBERT]" in r.stdout and "Cahier :" in r.stdout
    assert conn.exists() and (tmp_path / "g.json").exists() and os.path.isdir(tmp_path / "cahier_albert")
    r2 = subprocess.run([sys.executable, os.path.join(RACINE, "anemone_physicien.py"), "--etat", "--connaissances", str(conn)],
                        capture_output=True, text=True, timeout=120)
    assert r2.returncode == 0 and "relation [fonctionnelle]" in r2.stdout


# ----------------------------------------------------------------- interface : deux modes

def test_interface_modes_et_albert(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ap, "FICHIER_CONNAISSANCES", str(tmp_path / "anemone_connaissances.json"))
    monkeypatch.setenv("ANEMONE_SANS_RESEAU", "1")
    chemin = tmp_path / "cine.csv"
    _cinematique(np.random.default_rng(7)).to_csv(chemin, index=False)

    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=600)
    at.run()
    assert not at.exception, at.exception
    assert at.sidebar.radio(key="mode_albert").value.startswith("🤝")
    at.sidebar.radio(key="mode_source").set_value("Chemin local").run()
    at.sidebar.text_input(key="chemin_local").set_value(str(chemin)).run()
    assert not at.exception, at.exception
    at.button(key="albert_apprendre").click().run()
    assert not at.exception, at.exception
    lecon = at.session_state["albert_derniere_lecon"]
    assert lecon["relations_apprises"]
    assert at.session_state["connaissances"]["relations"]
    # mode « Fred seul » : la section Albert disparaît, la base reste
    at.sidebar.radio(key="mode_albert").set_value("👤 Fred seul avec l'Architecte").run()
    assert not at.exception, at.exception
    assert not any(getattr(b, "key", None) == "albert_apprendre" for b in at.button)
    assert at.session_state["connaissances"]["relations"]


def test_albert_chasse_les_bosses_dans_sa_recherche(tmp_path):
    """Albert utilise le run de découverte : une bosse « thèse » devient une trouvaille, une connue une leçon."""
    rng = np.random.default_rng(31)
    dossier = tmp_path / "runs"
    dossier.mkdir()
    for i, pic in enumerate((42.0, 42.0)):
        x = np.r_[rng.exponential(10.0, 40000) + 1.0, rng.normal(pic, 0.6, 350)]
        rng.shuffle(x)
        pd.DataFrame({"Run": 100 + i, "Event": np.arange(len(x)), "M": x, "pt1": rng.exponential(5, len(x))}).to_csv(dossier / f"r{i}.csv", index=False)
    albert = ap.Albert(ap.Connaissances())
    cahier = albert.chercher([str(dossier / "r0.csv"), str(dossier / "r1.csv")], dossier_cahier=str(tmp_path / "cahier"))
    assert "bosses" in cahier and "erreur" not in cahier["bosses"]
    assert any(t["strategies"] == ["chasse aux bosses"] for t in cahier["trouvailles"])
    texte = open(cahier["chemin"], encoding="utf-8").read()
    assert "Chasse aux bosses" in texte
