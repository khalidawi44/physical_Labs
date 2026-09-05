#!/usr/bin/env python3
"""Vérification et installation des mises à jour d'A.N.E.M.O.N.E.

Appelé par les lanceurs avant l'installation des dépendances. N'utilise que la
bibliothèque standard : il fonctionne avant la création du .venv.

Principe : la branche `main` du dépôt GitHub est la version publiée. Le fichier
`VERSION` distant est comparé au fichier `VERSION` local. Si une version plus
récente existe, l'utilisateur est invité à l'installer (le ZIP de `main` est
téléchargé et déballé par-dessus le dossier de l'outil).

Ce qui n'est jamais touché : `.venv/`, `anemone_graphe.json` (le graphe du
physicien), `.git/`, et tout fichier absent de l'archive (les exports du
physicien restent en place).

Le lanceur en cours d'exécution ne peut pas être réécrit pendant qu'il tourne :
sa nouvelle version est déposée dans `.anemone_maj/` et le lanceur se remplace
lui-même en dernière instruction.

Codes de sortie :
  0  rien à faire (à jour, hors ligne, refusé, désactivé)
  10 mise à jour installée, le lanceur peut continuer
  20 mise à jour installée ET nouveau lanceur en attente dans .anemone_maj/

Variables d'environnement :
  ANEMONE_SANS_MAJ=1        ne rien vérifier
  ANEMONE_MAJ_AUTO=1        installer sans poser de question
  ANEMONE_MAJ_URL_VERSION   URL du fichier VERSION distant (tests)
  ANEMONE_MAJ_URL_ZIP       URL de l'archive ZIP distante (tests)
"""
from __future__ import annotations

import io
import os
import re
import sys
import zipfile
import urllib.request
from typing import List, Optional, Tuple

DEPOT = "khalidawi44/physical_labs"
URL_VERSION_DEFAUT = f"https://raw.githubusercontent.com/{DEPOT}/main/VERSION"
URL_ZIP_DEFAUT = f"https://github.com/{DEPOT}/archive/refs/heads/main.zip"
DELAI_RESEAU = 8  # secondes

DOSSIER_ATTENTE = ".anemone_maj"
PROTEGES = {".venv", ".git", DOSSIER_ATTENTE, "anemone_graphe.json", "rapports", "donnees", "__pycache__"}
LANCEURS = {"lancer_anemone.bat", "lancer_anemone.sh", "lancer_anemone.command", "lancer_anemone.desktop"}
LANCEUR_ACTIF = "lancer_anemone.bat" if os.name == "nt" else "lancer_anemone.sh"


def racine_outil() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lire_version(texte: str) -> Tuple[int, ...]:
    """'0.2.0\\n' -> (0, 2, 0). Texte invalide -> (0,)."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", texte or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


def version_locale(racine: str) -> str:
    try:
        with open(os.path.join(racine, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0"


def telecharger(url: str, delai: int = DELAI_RESEAU) -> bytes:
    with urllib.request.urlopen(url, timeout=delai) as reponse:
        return reponse.read()


def version_distante(url: Optional[str] = None) -> Optional[str]:
    """Version publiée, ou None si le réseau est indisponible."""
    try:
        return telecharger(url or os.environ.get("ANEMONE_MAJ_URL_VERSION", URL_VERSION_DEFAUT)).decode("utf-8").strip()
    except Exception:
        return None


def _chemin_sur(racine: str, relatif: str) -> Optional[str]:
    """Chemin absolu sous `racine`, ou None si l'entrée sort du dossier (zip-slip)."""
    relatif = relatif.replace("\\", "/")
    if relatif.startswith("/") or ".." in relatif.split("/"):
        return None
    absolu = os.path.abspath(os.path.join(racine, relatif))
    if os.path.commonpath([absolu, os.path.abspath(racine)]) != os.path.abspath(racine):
        return None
    return absolu


def _ecrire_atomique(chemin: str, donnees: bytes, executable: bool = False) -> None:
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    temporaire = chemin + ".tmp"
    with open(temporaire, "wb") as f:
        f.write(donnees)
    if executable and os.name != "nt":
        os.chmod(temporaire, 0o755)
    os.replace(temporaire, chemin)  # rename atomique : un lecteur en cours garde l'ancien fichier


def installer(archive: bytes, racine: str, lanceur_actif: str = LANCEUR_ACTIF) -> Tuple[int, List[str]]:
    """Déballe l'archive par-dessus `racine`.

    Renvoie (nombre de fichiers écrits, lanceurs mis en attente dans .anemone_maj/).
    Le premier composant du chemin (dossier racine de l'archive GitHub) est retiré.
    """
    ecrits = 0
    en_attente: List[str] = []
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            morceaux = info.filename.replace("\\", "/").split("/")
            if len(morceaux) < 2:
                continue  # fichier hors dossier racine d'archive : ignoré
            relatif = "/".join(morceaux[1:])
            if morceaux[1] in PROTEGES or relatif in PROTEGES:
                continue
            donnees = zf.read(info)
            nom = morceaux[-1]
            executable = nom in LANCEURS
            if relatif == lanceur_actif:
                actuel = os.path.join(racine, relatif)
                try:
                    with open(actuel, "rb") as f:
                        if f.read() == donnees:
                            continue  # lanceur inchangé : rien à remplacer
                except OSError:
                    pass
                cible = _chemin_sur(racine, f"{DOSSIER_ATTENTE}/{relatif}")
                if cible is None:
                    continue
                _ecrire_atomique(cible, donnees, executable)
                en_attente.append(relatif)
                ecrits += 1
                continue
            cible = _chemin_sur(racine, relatif)
            if cible is None:
                continue
            _ecrire_atomique(cible, donnees, executable)
            ecrits += 1
    return ecrits, en_attente


def demander(question: str) -> bool:
    """Oui par défaut (Entrée). Sans terminal interactif : refus."""
    if os.environ.get("ANEMONE_MAJ_AUTO") == "1":
        return True
    if not sys.stdin or not sys.stdin.isatty():
        return False
    try:
        reponse = input(question).strip().lower()
    except EOFError:
        return False
    return reponse in ("", "o", "oui", "y", "yes")


def _console_robuste() -> None:
    """Console Windows en cp1252/cp850 : ne jamais planter sur un accent ou une pastille."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def main() -> int:
    _console_robuste()
    if os.environ.get("ANEMONE_SANS_MAJ") == "1":
        return 0
    racine = racine_outil()
    locale = version_locale(racine)
    distante = version_distante()
    if distante is None:
        print(f"[MAJ] Version {locale}. Vérification impossible (hors ligne ?) : on continue.")
        return 0
    if lire_version(distante) <= lire_version(locale):
        print(f"[MAJ] Version {locale} : à jour.")
        return 0
    print(f"[MAJ] Nouvelle version disponible : {distante} (installée : {locale}).")
    print("      Vos données (graphe de connaissances, exports) sont conservées.")
    if not demander("      Installer maintenant ? [O/n] "):
        print("[MAJ] Mise à jour reportée. Elle sera proposée au prochain lancement.")
        return 0
    try:
        archive = telecharger(os.environ.get("ANEMONE_MAJ_URL_ZIP", URL_ZIP_DEFAUT), delai=120)
        ecrits, en_attente = installer(archive, racine)
    except Exception as exc:  # réseau coupé, archive corrompue, disque plein…
        print(f"[MAJ] Échec de la mise à jour ({exc}). L'outil continue en version {locale}.")
        return 0
    print(f"[MAJ] Version {distante} installée ({ecrits} fichiers).")
    return 20 if en_attente else 10


if __name__ == "__main__":
    sys.exit(main())
