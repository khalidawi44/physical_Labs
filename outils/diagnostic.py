#!/usr/bin/env python3
"""Rapport de diagnostic d'A.N.E.M.O.N.E, à envoyer au support en cas de problème.

Bibliothèque standard uniquement : fonctionne même si les dépendances
scientifiques ne s'installent pas. Utilisation :

    python outils/diagnostic.py            (affiche et écrit diagnostic_anemone.txt)

Le rapport ne contient aucune donnée de physique : uniquement les versions
des logiciels, le système et la présence des fichiers de l'outil.
"""
from __future__ import annotations

import os
import platform
import sys
from datetime import datetime, timezone
from typing import List

PAQUETS = ["streamlit", "numpy", "pandas", "plotly", "scikit-learn", "scipy", "networkx", "uproot", "awkward", "pyarrow"]
FICHIERS = ["anemone_master.py", "requirements.txt", "VERSION", ".streamlit/config.toml",
            "lancer_anemone.bat", "lancer_anemone.sh", "lancer_anemone.command", "anemone_graphe.json"]


def racine_outil() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version_paquet(nom: str) -> str:
    try:
        from importlib.metadata import version
        return version(nom)
    except Exception:
        return "absent"


def rapport_diagnostic() -> str:
    racine = racine_outil()
    lignes: List[str] = []
    lignes.append("=== Diagnostic A.N.E.M.O.N.E ===")
    lignes.append(f"Date (UTC)        : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        with open(os.path.join(racine, "VERSION"), encoding="utf-8") as f:
            version_outil = f.read().strip()
    except OSError:
        version_outil = "inconnue (fichier VERSION absent)"
    lignes.append(f"Version de l'outil: {version_outil}")
    lignes.append(f"Dossier           : {racine}")
    lignes.append("")
    lignes.append("--- Système ---")
    lignes.append(f"OS                : {platform.platform()}")
    lignes.append(f"Machine           : {platform.machine()}")
    lignes.append(f"Python            : {sys.version.split()[0]} ({sys.executable})")
    lignes.append(f"Dans un .venv     : {'oui' if sys.prefix != getattr(sys, 'base_prefix', sys.prefix) else 'non'}")
    lignes.append("")
    lignes.append("--- Paquets ---")
    for p in PAQUETS:
        lignes.append(f"{p:<18}: {_version_paquet(p)}")
    lignes.append("")
    lignes.append("--- Fichiers de l'outil ---")
    for f in FICHIERS:
        chemin = os.path.join(racine, f)
        if os.path.exists(chemin):
            lignes.append(f"{f:<26}: présent ({os.path.getsize(chemin)} octets)")
        else:
            lignes.append(f"{f:<26}: absent")
    lignes.append(f"{'.venv':<26}: {'présent' if os.path.isdir(os.path.join(racine, '.venv')) else 'absent'}")
    lignes.append("")
    lignes.append("--- Variables d'environnement A.N.E.M.O.N.E ---")
    for cle in sorted(k for k in os.environ if k.startswith("ANEMONE_")):
        lignes.append(f"{cle:<26}: {os.environ[cle]}")
    return "\n".join(lignes) + "\n"


def main() -> int:
    texte = rapport_diagnostic()
    print(texte)
    sortie = os.path.join(racine_outil(), "diagnostic_anemone.txt")
    try:
        with open(sortie, "w", encoding="utf-8") as f:
            f.write(texte)
        print(f"Rapport écrit dans : {sortie}")
    except OSError as exc:
        print(f"Impossible d'écrire le rapport ({exc}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
