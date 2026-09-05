"""Tests des données ouvertes (catalogue, téléchargement vérifié) et de l'exclusion des identifiants."""
import os
import subprocess
import sys
import zlib

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import anemone_master as am  # noqa: E402
from outils import donnees_ouvertes as do  # noqa: E402


def test_identifiants_ecartes_par_defaut():
    cols = ["Run", "Event", "E1", "px1", "pt1", "eta1", "phi1", "Q1", "M", "lumiBlock", "track_id"]
    assert am.est_identifiant("Run") and am.est_identifiant("Event") and am.est_identifiant("track_id")
    assert am.est_identifiant("lumiBlock")
    assert not am.est_identifiant("E1") and not am.est_identifiant("Energie_MeV") and not am.est_identifiant("pt1")
    # masses d'abord, puis pt, énergie, impulsion, le reste dans l'ordre du fichier, charges en dernier
    assert am.colonnes_analysables(cols) == ["M", "pt1", "E1", "px1", "eta1", "phi1", "Q1"]
    assert am.colonnes_physiques(cols) == ["E1", "px1", "pt1", "eta1", "phi1", "Q1", "M"]
    assert am.colonnes_analysables(["Run", "Event"]) == ["Run", "Event"]  # rien d'autre : on garde tout


def test_catalogue_instantane_coherent():
    entrees = do.catalogue(en_ligne=False)
    ids = [e.identifiant for e in entrees]
    assert len(ids) == len(set(ids)) >= 19
    for e in entrees:
        assert e.url.startswith("https://opendata.cern.ch/record/") and e.url.endswith(e.nom)
        assert len(e.adler32) == 8 and int(e.adler32, 16) >= 0
        assert e.taille > 0 and e.description and e.titre and e.page
    assert do.trouver("545/Zmumu.csv").record == 545
    assert do.trouver("MuRun2010B_3.csv").taille == 1514795
    with pytest.raises(KeyError):
        do.trouver("inexistant.csv")


def _faux_jeu(tmp_path, contenu: bytes, adler=None, taille=None):
    src = tmp_path / "source.csv"
    src.write_bytes(contenu)
    return do.JeuDeDonnees(identifiant="999/test.csv", record=999, nom="test.csv", titre="t", description="d",
                           taille=taille if taille is not None else len(contenu),
                           adler32=adler or f"{zlib.adler32(contenu) & 0xFFFFFFFF:08x}", licence="CC0", annee="2026",
                           url=src.as_uri(), page="https://example.invalid"), src


def test_telecharger_verifie_integrite(tmp_path):
    contenu = b"E1,pt1,M\n1,2,3\n4,5,6\n"
    entree, _ = _faux_jeu(tmp_path, contenu)
    dossier = str(tmp_path / "donnees")
    progres = []
    chemin = do.telecharger(entree, dossier, rappel=lambda r, t: progres.append((r, t)))
    assert os.path.isfile(chemin) and open(chemin, "rb").read() == contenu
    assert chemin == os.path.join(dossier, "999", "test.csv")
    assert progres and progres[-1] == (len(contenu), len(contenu))
    assert do.deja_present(entree, dossier)
    # second appel : pas de nouveau téléchargement (le rappel signale directement 100 %)
    progres.clear()
    assert do.telecharger(entree, dossier, rappel=lambda r, t: progres.append((r, t))) == chemin
    assert progres == [(len(contenu), len(contenu))]


def test_telecharger_rejette_fichier_corrompu(tmp_path):
    contenu = b"E1,pt1,M\n1,2,3\n"
    entree, _ = _faux_jeu(tmp_path, contenu, adler="00000000")
    with pytest.raises(ValueError, match="intégrité"):
        do.telecharger(entree, str(tmp_path / "donnees"))
    assert not os.path.exists(entree.chemin_local(str(tmp_path / "donnees")))
    assert not os.path.exists(entree.chemin_local(str(tmp_path / "donnees")) + ".partiel")


def test_telecharger_reprend_apres_coupure(tmp_path):
    """Un .partiel laissé par une coupure ne bloque pas : le téléchargement aboutit et le fichier est intègre."""
    contenu = b"E1,pt1,M\n" + b"1,2,3\n" * 500
    entree, _ = _faux_jeu(tmp_path, contenu)
    dossier = str(tmp_path / "donnees")
    partiel = entree.chemin_local(dossier) + ".partiel"
    os.makedirs(os.path.dirname(partiel))
    open(partiel, "wb").write(contenu[:100])  # reste d'une coupure (file:// ignore Range : on repart de zéro)
    chemin = do.telecharger(entree, dossier)
    assert open(chemin, "rb").read() == contenu and not os.path.exists(partiel)


def test_telecharger_abandonne_apres_tentatives(tmp_path):
    contenu = b"E1\n1\n"
    entree, src = _faux_jeu(tmp_path, contenu)
    src.unlink()  # source introuvable : chaque tentative échoue
    with pytest.raises(ConnectionError, match="tentatives"):
        do.telecharger(entree, str(tmp_path / "donnees"), tentatives=2)


def test_ligne_de_commande_liste():
    env = {**os.environ, "ANEMONE_SANS_RESEAU": "1"}
    r = subprocess.run([sys.executable, os.path.join(RACINE, "outils", "donnees_ouvertes.py"), "--liste"],
                       capture_output=True, text=True, timeout=60, env=env)
    assert r.returncode == 0, r.stderr
    assert "545/Zmumu.csv" in r.stdout and "700/MuRun2010B_0.csv" in r.stdout and "opendata.cern.ch" in r.stdout


def test_interface_donnees_ouvertes_un_clic(tmp_path, monkeypatch):
    """Un clic sur « Télécharger et ouvrir » : téléchargement vérifié puis ouverture dans la vue interactive."""
    import numpy as np
    import pandas as pd
    from streamlit.testing.v1 import AppTest

    rng = np.random.default_rng(5)
    n = 800
    df = pd.DataFrame({"Run": 1, "Event": np.arange(n), "E1": rng.normal(10, 2, n), "pt1": rng.normal(8, 1.5, n),
                       "eta1": rng.normal(0, 1, n), "M": rng.normal(3.1, 0.2, n)})
    df.iloc[:20, df.columns.get_loc("M")] = rng.uniform(80, 95, 20)
    contenu = df.to_csv(index=False).encode()
    entree, _ = _faux_jeu(tmp_path, contenu)
    monkeypatch.setattr(do, "catalogue", lambda en_ligne=True: [entree])
    monkeypatch.setenv("ANEMONE_SANS_RESEAU", "1")
    monkeypatch.chdir(tmp_path)
    import streamlit as st
    st.cache_data.clear()  # le catalogue est mis en cache par l'application : un test précédent l'a déjà rempli

    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=300)
    at.run()
    assert not at.exception, at.exception
    assert at.selectbox(key="ouvert_choix").value == "999/test.csv"
    at.button(key="ouvert_ouvrir").click().run()
    assert not at.exception, at.exception
    chemin = entree.chemin_local(do.DOSSIER_DEFAUT)
    assert os.path.isfile(chemin) and do.deja_present(entree, do.DOSSIER_DEFAUT)
    assert at.session_state["mode_source"] == "Chemin local"
    assert at.session_state["chemin_local"] == os.path.abspath(chemin)
    assert int(at.metric[0].value) == n                       # le fichier réel est chargé
    assert "Run" not in at.sidebar.multiselect[0].value        # identifiants écartés par défaut
    assert "M" in at.sidebar.multiselect[0].value


@pytest.mark.skipif(os.environ.get("ANEMONE_TESTS_RESEAU") != "1", reason="réseau : ANEMONE_TESTS_RESEAU=1 pour activer")
def test_telechargement_reel_zmumu(tmp_path):
    """Télécharge réellement le plus petit fichier du catalogue et le lit avec l'outil."""
    entree = do.trouver("545/Zmumu.csv", do.catalogue(en_ligne=True))
    chemin = do.telecharger(entree, str(tmp_path / "donnees"))
    matrice, rapport = am.analyser_fichier_physique(chemin, entree.nom)
    assert rapport["n_evenements"] > 1000 and "pt1" in matrice.columns  # Zmumu.csv : pt/eta/phi/Q/dxy/iso des deux muons
    assert "Run" not in am.colonnes_analysables(list(matrice.columns))


def test_deja_present_somme_memorisee_et_modification_detectee(tmp_path):
    contenu = b"Run,Event,E\n1,1,4.2\n1,2,5.0\n"
    entree, _ = _faux_jeu(tmp_path, contenu)
    chemin = entree.chemin_local(str(tmp_path / "d"))
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(contenu)
    assert do.deja_present(entree, str(tmp_path / "d"))
    appels = []
    original = do.adler32_fichier
    do.adler32_fichier = lambda c: appels.append(c) or original(c)
    try:
        assert do.deja_present(entree, str(tmp_path / "d")) and appels == []      # même taille, même date : pas relu
        with open(chemin, "wb") as f:
            f.write(b"Run,Event,E\n1,1,4.2\n1,2,9.9\n")                        # même taille, contenu altéré
        os.utime(chemin, ns=(os.stat(chemin).st_atime_ns, os.stat(chemin).st_mtime_ns + 10 ** 9))
        assert not do.deja_present(entree, str(tmp_path / "d")) and appels == [chemin]
    finally:
        do.adler32_fichier = original


def test_interface_catalogue_affiche_sans_reseau(tmp_path, monkeypatch):
    """Le catalogue embarqué s'affiche sans aucune requête réseau : l'écran n'attend jamais le CERN au lancement."""
    from streamlit.testing.v1 import AppTest

    def interdit(*a, **k):
        raise AssertionError("l'affichage ne doit pas interroger le réseau")

    monkeypatch.setattr(do, "catalogue_en_ligne", interdit)
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(os.path.join(RACINE, "anemone_master.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert len(at.selectbox(key="ouvert_choix").options) == len(do.catalogue_instantane()) == 19
    at.button(key="ouvert_relire").click().run()            # relecture explicite : l'échec est affiché, pas fatal
    assert not at.exception, at.exception
    assert any("Catalogue en ligne inaccessible" in e.value for e in at.error)
