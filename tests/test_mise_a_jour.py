"""Tests de la mise à jour automatique et du diagnostic (sans réseau : URLs file://)."""
import io
import os
import subprocess
import sys
import zipfile

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from outils import mise_a_jour as maj  # noqa: E402
from outils.diagnostic import rapport_diagnostic  # noqa: E402


def _archive(fichiers: dict, dossier="physical_labs-main") -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zf:
        for chemin, contenu in fichiers.items():
            zf.writestr(f"{dossier}/{chemin}", contenu)
    return tampon.getvalue()


def _outil_local(tmp_path, version="0.1.0"):
    """Simule un dossier d'outil installé chez le chercheur."""
    # Écriture binaire : sur Windows, write_text convertirait les fins de ligne
    # et le comparateur d'octets de l'outil verrait un lanceur différent.
    (tmp_path / "VERSION").write_bytes(f"{version}\n".encode())
    (tmp_path / "alliance_cartographie.py").write_bytes(b"ancien = True\n")
    (tmp_path / "lancer_anemone.sh").write_bytes(b"#!/bin/bash\necho ancien\n")
    (tmp_path / "lancer_anemone.bat").write_bytes(b"@echo ancien\r\n")
    (tmp_path / "export_perso.json").write_bytes(b"{}")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "marqueur").write_bytes(b"venv")
    return tmp_path


def test_lire_version():
    assert maj.lire_version("0.2.0\n") == (0, 2, 0)
    assert maj.lire_version("v1.10.3") == (1, 10, 3)
    assert maj.lire_version("n'importe quoi") == (0,)
    assert maj.lire_version("0.10.0") > maj.lire_version("0.9.9")


def test_installer_preserve_local_et_met_lanceur_en_attente(tmp_path):
    racine = _outil_local(tmp_path)
    archive = _archive({
        "VERSION": "0.2.0\n",
        "alliance_cartographie.py": "nouveau = True\n",
        "lancer_anemone.sh": "#!/bin/bash\necho nouveau\n",
        "lancer_anemone.bat": "@echo nouveau\r\n",
        "outils/mise_a_jour.py": "# nouveau\n",
        ".venv/marqueur": "NE DOIT PAS ECRASER",
    })
    ecrits, en_attente = maj.installer(archive, str(racine), lanceur_actif="lancer_anemone.sh")

    assert (racine / "VERSION").read_text().strip() == "0.2.0"
    assert (racine / "alliance_cartographie.py").read_text() == "nouveau = True\n"
    assert (racine / "outils" / "mise_a_jour.py").read_text() == "# nouveau\n"
    # .venv protégé et fichier local absent de l'archive préservés
    assert (racine / ".venv" / "marqueur").read_text() == "venv"
    assert (racine / "export_perso.json").exists()
    # lanceur actif mis en attente, l'autre remplacé directement
    assert en_attente == ["lancer_anemone.sh"]
    assert (racine / "lancer_anemone.sh").read_bytes() == b"#!/bin/bash\necho ancien\n"
    assert (racine / maj.DOSSIER_ATTENTE / "lancer_anemone.sh").read_bytes() == b"#!/bin/bash\necho nouveau\n"
    assert (racine / "lancer_anemone.bat").read_bytes() == b"@echo nouveau\r\n"  # CRLF conservés
    if os.name != "nt":
        assert os.access(racine / maj.DOSSIER_ATTENTE / "lancer_anemone.sh", os.X_OK)
    assert ecrits == 5


def test_installer_lanceur_inchange_pas_d_attente(tmp_path):
    racine = _outil_local(tmp_path)
    archive = _archive({"VERSION": "0.2.0\n", "lancer_anemone.sh": "#!/bin/bash\necho ancien\n"})
    _, en_attente = maj.installer(archive, str(racine), lanceur_actif="lancer_anemone.sh")
    assert en_attente == []
    assert not (racine / maj.DOSSIER_ATTENTE).exists()


def test_installer_refuse_zip_slip(tmp_path):
    racine = _outil_local(tmp_path)
    archive = _archive({"../evasion.txt": "pirate", "sous/../../evasion2.txt": "pirate"})
    maj.installer(archive, str(racine))
    assert not (tmp_path.parent / "evasion.txt").exists()
    assert not (tmp_path.parent / "evasion2.txt").exists()


def _lancer_script(racine, env_sup):
    env = {**os.environ, **env_sup}
    return subprocess.run([sys.executable, os.path.join(racine, "outils", "mise_a_jour.py")],
                          env=env, capture_output=True, text=True, timeout=60)


def _copier_outils(racine):
    (racine / "outils").mkdir(exist_ok=True)
    for nom in ("__init__.py", "mise_a_jour.py"):
        (racine / "outils" / nom).write_bytes(open(os.path.join(RACINE, "outils", nom), "rb").read())


def test_script_a_jour(tmp_path):
    racine = _outil_local(tmp_path, version="0.2.0")
    _copier_outils(racine)
    distante = tmp_path.parent / f"{tmp_path.name}_VERSION"
    distante.write_bytes(b"0.2.0\n")
    r = _lancer_script(racine, {"ANEMONE_MAJ_URL_VERSION": distante.as_uri(), "ANEMONE_MAJ_AUTO": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "à jour" in r.stdout


def test_script_hors_ligne_continue(tmp_path):
    racine = _outil_local(tmp_path)
    _copier_outils(racine)
    r = _lancer_script(racine, {"ANEMONE_MAJ_URL_VERSION": (tmp_path / "inexistant").as_uri()})
    assert r.returncode == 0
    assert "Vérification impossible" in r.stdout


def test_script_desactive(tmp_path):
    racine = _outil_local(tmp_path)
    _copier_outils(racine)
    r = _lancer_script(racine, {"ANEMONE_SANS_MAJ": "1", "ANEMONE_MAJ_URL_VERSION": "http://127.0.0.1:9/x"})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_script_installe_et_signale_relance(tmp_path):
    racine = _outil_local(tmp_path)
    _copier_outils(racine)
    distante = tmp_path.parent / f"{tmp_path.name}_VERSION"
    distante.write_bytes(b"0.3.0\n")
    zip_distant = tmp_path.parent / f"{tmp_path.name}_main.zip"
    lanceur_actif = "lancer_anemone.bat" if os.name == "nt" else "lancer_anemone.sh"
    zip_distant.write_bytes(_archive({"VERSION": "0.3.0\n", "alliance_cartographie.py": "v3\n", lanceur_actif: "nouveau lanceur\n"}))
    r = _lancer_script(racine, {"ANEMONE_MAJ_URL_VERSION": distante.as_uri(),
                                "ANEMONE_MAJ_URL_ZIP": zip_distant.as_uri(), "ANEMONE_MAJ_AUTO": "1"})
    assert r.returncode == 20, r.stdout + r.stderr
    assert (racine / "VERSION").read_text().strip() == "0.3.0"
    assert (racine / "alliance_cartographie.py").read_text() == "v3\n"
    assert (racine / maj.DOSSIER_ATTENTE / lanceur_actif).read_text() == "nouveau lanceur\n"
    assert (racine / "export_perso.json").exists()                  # fichier local absent de l'archive préservé


def test_script_sans_terminal_ne_force_pas(tmp_path):
    """Sans terminal interactif et sans ANEMONE_MAJ_AUTO, la mise à jour est reportée."""
    racine = _outil_local(tmp_path)
    _copier_outils(racine)
    distante = tmp_path.parent / f"{tmp_path.name}_VERSION"
    distante.write_bytes(b"9.0.0\n")
    r = _lancer_script(racine, {"ANEMONE_MAJ_URL_VERSION": distante.as_uri(), "ANEMONE_MAJ_URL_ZIP": "http://127.0.0.1:9/x"})
    assert r.returncode == 0
    assert "reportée" in r.stdout
    assert (racine / "VERSION").read_text().strip() == "0.1.0"


def test_rapport_diagnostic():
    texte = rapport_diagnostic()
    assert "Diagnostic Alliance Groupe" in texte
    assert "Python" in texte and "streamlit" in texte
    assert "Energie" not in texte  # aucune donnée métier


def test_installer_efface_le_port_note(tmp_path, monkeypatch):
    """Après une mise à jour, le port noté est effacé pour que le lanceur démarre la nouvelle version."""
    import outils.mise_a_jour as mj

    racine = tmp_path
    (racine / "VERSION").write_text("0.1.0\n")
    (racine / ".anemone_port").write_text("8501")
    # une archive minimale contenant une nouvelle VERSION
    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("physical_labs-main/VERSION", "9.9.9\n")
        zf.writestr("physical_labs-main/alliance_cartographie.py", "# nouvelle app\n")
    monkeypatch.setattr(mj, "racine_outil", lambda: str(racine))
    monkeypatch.setattr(mj, "version_distante", lambda: "9.9.9")
    monkeypatch.setattr(mj, "telecharger", lambda *a, **k: buf.getvalue())
    monkeypatch.setattr(mj, "demander", lambda *a, **k: True)
    code = mj.main()
    assert code in (10, 20)
    assert not (racine / ".anemone_port").exists()                 # port effacé → pas de réouverture de l'ancienne
    assert (racine / "alliance_cartographie.py").exists()          # nouveau fichier bien ajouté
