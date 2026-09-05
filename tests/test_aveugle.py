# -*- coding: utf-8 -*-
"""Analyse à l'aveugle : scellement, intégrité, masquage, fond attendu sans regarder, levée unique et irréversible."""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import anemone_aveugle as av  # noqa: E402
import anemone_bosse as ab  # noqa: E402


def _fichier(tmp_path, rng, pic=400, nom="run.csv"):
    x = np.r_[rng.exponential(10.0, 60000) + 1.0, rng.normal(42.0, 0.6, pic)] if pic else rng.exponential(10.0, 60000) + 1.0
    rng.shuffle(x)
    chemin = tmp_path / nom
    pd.DataFrame({"Run": 1, "Event": np.arange(len(x)), "M": x}).to_csv(chemin, index=False)
    return str(chemin)


def test_sceller_masquer_fond_lever_et_refuser(tmp_path):
    rng = np.random.default_rng(3)
    chemin = _fichier(tmp_path, rng)
    dossier = str(tmp_path / "prot")
    p = av.sceller("M", 40.5, 43.5, "résonance vers 42 ?", "Fabrice", [chemin], dossier_protocoles=dossier)
    assert p.etat == "scelle" and av.integre(p) and p.fichiers[0]["fichier"] == "run.csv"
    assert os.path.isfile(p.chemin)
    df = pd.read_csv(chemin)
    masquee, masques = av.masquer(df, av.scelles(dossier))
    assert masques[0]["n_masques"] == int(((df.M >= 40.5) & (df.M < 43.5)).sum()) > 0
    assert len(masquee) + masques[0]["n_masques"] == len(df)
    assert not ((masquee.M >= 40.5) & (masquee.M < 43.5)).any()
    fa = av.fond_attendu(p, df)
    assert fa["testable"] and fa["attendu"] > 0 and "observ" not in fa["detail"].lower()   # jamais l'observé avant la levée
    p = av.lever(p, df, [chemin])
    assert p.etat == "leve" and p.resultat["decouverte"] is True and p.resultat["observe"] > p.resultat["attendu"]
    assert p.resultat["donnees_conformes_au_protocole"] is True and p.resultat["deux_moities"] is True
    assert "5 σ" in p.resultat["verdict"]
    assert os.path.isfile(os.path.splitext(p.chemin)[0] + ".md")
    with pytest.raises(RuntimeError):
        av.lever(p, df, [chemin])                                     # jamais deux fois
    rechargee = av.lister(dossier)[0]
    assert rechargee.etat == "leve" and rechargee.resultat["observe"] == p.resultat["observe"]
    assert av.masquer(df, av.lister(dossier))[1] == []                 # levé : plus rien n'est masqué


def test_protocole_altere_est_refuse(tmp_path):
    rng = np.random.default_rng(4)
    chemin = _fichier(tmp_path, rng)
    dossier = str(tmp_path / "prot")
    p = av.sceller("M", 40.5, 43.5, "", "", [chemin], dossier_protocoles=dossier)
    d = json.load(open(p.chemin, encoding="utf-8"))
    d["haut"] = 60.0                                                   # quelqu'un élargit la fenêtre après coup
    json.dump(d, open(p.chemin, "w", encoding="utf-8"))
    altere = av.lister(dossier)[0]
    assert not av.integre(altere)
    with pytest.raises(RuntimeError):
        av.lever(altere, pd.read_csv(chemin), [chemin])


def test_donnees_differentes_et_hypothese_non_soutenue(tmp_path):
    rng = np.random.default_rng(5)
    engage = _fichier(tmp_path, rng, pic=400, nom="engage.csv")
    autre = _fichier(tmp_path, rng, pic=0, nom="autre.csv")
    dossier = str(tmp_path / "prot")
    p = av.sceller("M", 40.5, 43.5, "", "", [engage], dossier_protocoles=dossier)
    p = av.lever(p, pd.read_csv(autre), [autre])                        # fond lisse, et pas le fichier engagé
    assert p.resultat["decouverte"] is False and p.resultat["donnees_conformes_au_protocole"] is False
    assert "non soutenue" in p.resultat["verdict"] or "indice" in p.resultat["verdict"]


def test_ligne_de_commande(tmp_path, capsys):
    rng = np.random.default_rng(6)
    chemin = _fichier(tmp_path, rng)
    dossier = str(tmp_path / "prot")
    assert av.main(["sceller", "--variable", "M", "--bas", "40.5", "--haut", "43.5", "--hypothese", "test", chemin, "--protocoles", dossier]) == 0
    ident = av.lister(dossier)[0].identifiant
    assert av.main(["lever", ident, chemin, "--protocoles", dossier]) == 2          # sans --oui : refus
    assert av.main(["lever", ident, chemin, "--protocoles", dossier, "--oui"]) == 0
    assert "5 σ" in capsys.readouterr().out


def test_interface_aveugle(tmp_path, monkeypatch):
    """Sceller depuis l'interface masque la fenêtre partout ; lever demande confirmation et n'arrive qu'une fois."""
    from streamlit.testing.v1 import AppTest

    rng = np.random.default_rng(7)
    chemin = _fichier(tmp_path, rng)
    n_total = 60400
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=300)
    at.run()
    at.sidebar.radio(key="mode_source").set_value("Chemin local").run()
    at.sidebar.text_input(key="chemin_local").set_value(chemin).run()
    assert int(at.metric[0].value) == n_total
    at.selectbox(key="aveugle_variable").set_value("M")
    at.number_input(key="aveugle_bas").set_value(40.5)
    at.number_input(key="aveugle_haut").set_value(43.5)
    at.text_input(key="aveugle_hypothese").set_value("résonance vers 42")
    at.button(key="FormSubmitter:aveugle_sceller_form-🔒 Sceller le protocole").click().run()
    assert not at.exception, at.exception
    protocoles = av.lister(str(tmp_path / "theses" / "protocoles"))
    assert len(protocoles) == 1 and protocoles[0].etat == "scelle" and protocoles[0].fichiers[0]["fichier"] == "run.csv"
    assert int(at.metric[0].value) < n_total                            # la fenêtre est masquée dans l'analyse
    assert any("masqués" in w.value for w in at.warning)
    ident = protocoles[0].identifiant
    assert at.button(key=f"aveugle_lever_{ident}").disabled                # tant que la case n'est pas cochée
    at.checkbox(key=f"aveugle_confirme_{ident}").check().run()
    at.button(key=f"aveugle_lever_{ident}").click().run()
    assert not at.exception, at.exception
    p = av.lister(str(tmp_path / "theses" / "protocoles"))[0]
    assert p.etat == "leve" and p.resultat["decouverte"] is True
    assert int(at.metric[0].value) == n_total                           # levé : plus de masque
    assert not any(b.key == f"aveugle_lever_{ident}" for b in at.button)  # plus de bouton : c'était unique
