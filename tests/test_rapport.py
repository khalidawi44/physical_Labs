# -*- coding: utf-8 -*-
"""Rapport de démonstration Alliance : constats triés, devis chiffré, document Word, vue Streamlit."""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

import alliance_modele as m  # noqa: E402
import rapport_demo as rd  # noqa: E402


def test_findings_tries_par_gravite():
    tries = rd.findings_tries()
    assert len(tries) == len(m.FINDINGS_DEMO)
    ordres = [m.GRAVITES.index(f["gravite"]) for f in tries]
    assert ordres == sorted(ordres)                       # du plus grave au moins grave
    assert tries[0]["gravite"] == "Critique"              # F1 (injection SQL) en tête


def test_compte_et_synthese():
    compte = rd.compte_par_gravite()
    assert set(compte) == set(m.GRAVITES)
    assert sum(compte.values()) == len(m.FINDINGS_DEMO)
    synth = rd.synthese()
    assert str(m.total_devis()) in synth                  # le total chiffré apparaît


def test_tableau_devis_total_coherent():
    tab = rd.tableau_devis()
    montants = list(tab["Montant (€ HT)"])
    # la dernière ligne est le total = somme des postes
    assert montants[-1] == sum(montants[:-1]) == m.total_devis()
    assert tab.iloc[-1]["Poste"] == "Total"


def test_document_docx_est_un_vrai_docx():
    octets = rd.document_docx()
    assert isinstance(octets, (bytes, bytearray)) and len(octets) > 2000
    assert octets[:2] == b"PK"                             # un .docx est une archive zip
    # relecture : la marque et un constat doivent s'y trouver
    from io import BytesIO
    from docx import Document
    doc = Document(BytesIO(octets))
    texte = "\n".join(p.text for p in doc.paragraphs)
    assert m.MARQUE in texte
    assert "Exemple fictif" in texte or "exemple" in texte.lower()


def test_modele_rapport_coherent():
    assert m.valider() == []
    assert m.total_devis() == sum(int(d["montant"]) for d in m.DEVIS_DEMO)
    assert all(f["gravite"] in m.GRAVITES for f in m.FINDINGS_DEMO)


def test_vue_rapport_dans_interface(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest

    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "alliance_cartographie.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    at.radio(key="vue").set_value("Rapport d'exemple (livrable)").run()
    assert not at.exception, at.exception
    assert any("livrable" in mk.value for mk in at.markdown)
    assert any("Constats" in mk.value for mk in at.markdown)
    # le bouton de téléchargement du .docx est présent
    assert at.download_button(key="dl_rapport") is not None
