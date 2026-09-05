# -*- coding: utf-8 -*-
"""Mode découverte guidée : lecture en langage courant, calculée depuis le diagnostic, jamais inventée."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import anemone_master as am  # noqa: E402
import anemone_guide as ag  # noqa: E402


def _diag_demo():
    df, rapport = am.nettoyer_matrice(am.generer_donnees_demo())
    cols = list(df.columns)
    res = am.detecter_inconnu(df, cols, contamination=0.03, seed=42)
    return am.diagnostiquer(res, cols), {"fichier": "DÉMO", "format": "demo", "n_variables": len(cols)}


def test_niveau_tres_net_coincide_avec_le_verrou_de_l_architecte():
    diag, rapport = _diag_demo()
    assert ag.niveau_de_preuve(diag) == "tres_net"
    _, verrou = am.Architecte(am.GrapheConnaissances(), diag).defense()
    assert verrou is True                                   # mêmes seuils : « très net » ⇔ preuve verrouillée


def test_lecture_reprend_les_chiffres_du_diagnostic():
    diag, rapport = _diag_demo()
    lecture = ag.lecture_guidee(diag, rapport)
    texte = " ".join(lecture["resume"])
    assert str(diag["n_total"]) in texte and str(diag["n_anomalies"]) in texte
    dom = am.variable_dominante(diag)
    assert lecture["dominante"] == dom and dom in texte
    assert "écart-type" in lecture["chiffres"]["Écart (d)"]
    assert lecture["demo"] and any("synthétiques" in e for e in lecture["et_maintenant"])
    assert lecture["vigilance"] == []                       # la démo n'a pas de corrélation suspecte


def test_niveau_insuffisant_et_faible():
    diag_vide = {"n_total": 3, "n_anomalies": 1, "n_conformes": 2, "variables": {}, "roles": {}, "insuffisant": True}
    lecture = ag.lecture_guidee(diag_vide, {"fichier": "x.csv", "format": "csv", "n_variables": 2})
    assert lecture["niveau"] == "insuffisant" and lecture["chiffres"] == {}
    assert any("plus grand" in e for e in lecture["et_maintenant"])

    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(size=600), "b": rng.normal(size=600)})   # bruit pur : rien ne ressort
    res = am.detecter_inconnu(df, ["a", "b"], contamination=0.03, seed=1)
    diag = am.diagnostiquer(res, ["a", "b"])
    lecture = ag.lecture_guidee(diag, {"fichier": "bruit.csv", "format": "csv", "n_variables": 2})
    assert lecture["niveau"] in ("faible", "net")           # jamais « très net » sur du bruit
    assert lecture["niveau"] != "tres_net"


def test_vigilance_signale_une_correlation_suspecte_et_un_episode_temporel():
    diag, rapport = _diag_demo()
    dom = am.variable_dominante(diag)
    autre = next(c for c in diag["variables"] if c != dom)
    cle = f"{dom} ↔ {autre}" if f"{dom} ↔ {autre}" in diag["correlations_anomalies"] else f"{autre} ↔ {dom}"
    diag["correlations_anomalies"][cle] = 0.9               # lien fort chez les isolés seulement
    diag["correlations_conformes"][cle] = 0.05
    diag["geometrie"]["fraction_fenetre_temporelle"] = 0.1  # isolés concentrés sur 10 % de la durée
    lecture = ag.lecture_guidee(diag, {"fichier": "run.csv", "format": "csv", "n_variables": 4})
    assert len(lecture["vigilance"]) == 2
    assert autre in lecture["vigilance"][0] and "appareil" in lecture["vigilance"][0]
    assert "10 %" in lecture["vigilance"][1]
    assert any("physicien" in e for e in lecture["et_maintenant"])
    # la même paire déclarée connue n'est plus un point de vigilance
    lecture2 = ag.lecture_guidee(diag, {"fichier": "run.csv", "format": "csv", "n_variables": 4},
                                 paires_connues={frozenset((dom, autre))})
    assert len(lecture2["vigilance"]) == 1


def test_glossaire_complet():
    for mot in ("événement", "isolé (ou anomalie)", "p (p-value)", "d (taille d'effet)", "biais instrumental"):
        assert len(ag.GLOSSAIRE[mot]) > 40


def test_interface_mode_guide(tmp_path, monkeypatch):
    """Bouton « guide-moi », lecture guidée à la place du bureau, réglages repliés, bureau sur demande."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=120)
    at.run()
    assert at.sidebar.radio(key="niveau").value.startswith("🔬")            # expert par défaut
    at.button(key="demarrage_guide").click().run()
    assert not at.exception, at.exception
    assert at.session_state["niveau"].startswith("🧭")
    assert not any(b.key == "demarrage_guide" for b in at.button)          # déjà en mode guidé
    assert [e.label for e in at.sidebar.expander][0].startswith("⚙️")     # réglages avancés repliés

    at.button(key="demarrage_demo").click().run()
    assert not at.exception, at.exception
    assert any("Ce que l'outil a trouvé" in m.value for m in at.markdown)
    assert any("Niveau de preuve" in m.value for m in at.markdown)
    assert not any("Bureau de l'Architecte" in m.value for m in at.markdown)   # bureau masqué
    assert int(at.metric[0].value) == 1240                                     # la vue 4D et les métriques restent
    assert any("Tableau des événements isolés" in e.label for e in at.expander)

    at.checkbox(key="guide_bureau").check().run()
    assert not at.exception, at.exception
    assert any("Bureau de l'Architecte" in m.value for m in at.markdown)

    at.sidebar.radio(key="niveau").set_value("🔬 Expert (tous les réglages)").run()
    assert not at.exception, at.exception
    assert not any("Ce que l'outil a trouvé" in m.value for m in at.markdown)
    assert any("Registre des événements isolés" in m.value for m in at.markdown)
