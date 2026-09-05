#!/usr/bin/env python3
"""Données réelles en un clic : catalogue de jeux de données publics du CERN Open Data.

Le chercheur choisit un jeu de données (ou tous), l'outil le télécharge dans
`donnees/cern_open_data/`, vérifie son intégrité (somme de contrôle Adler-32
publiée par le CERN) et l'ouvre dans la vue interactive ou dans une campagne.

Sources (vérifiées le 2026-09-05 via https://opendata.cern.ch/api/records/<id>) :

- enregistrement 545 : « Datasets derived from the Run2011A SingleElectron,
  SingleMu, DoubleElectron, and DoubleMu primary datasets », CMS, 2011,
  licence CC0-1.0. Événements candidats J/psi, Upsilon, W, Z et spectres
  dimuon / diélectron. Le CERN précise : sélection destinée à l'enseignement
  et à la diffusion, sous-ensemble de l'information par événement, non
  adaptée à une analyse de physique complète.
- enregistrement 700 : « Dimuon event information derived from the Run2010B
  public Mu dataset », CMS, 2010. Dix tranches de ~1,5 Mo et le fichier
  complet de ~15 Mo : idéal pour une campagne (dix « runs » + une référence).

Bibliothèque standard uniquement. En ligne, le catalogue est relu depuis
l'API du CERN ; hors ligne, l'instantané ci-dessous (tailles et sommes de
contrôle relevées le 2026-09-05) est utilisé.

    python outils/donnees_ouvertes.py --liste
    python outils/donnees_ouvertes.py --tout            (tout télécharger)
    python outils/donnees_ouvertes.py 545/Zmumu.csv     (un seul fichier)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import zlib
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional

API = "https://opendata.cern.ch/api/records/{record}"
URL_FICHIER = "https://opendata.cern.ch/record/{record}/files/{nom}"
URL_PAGE = "https://opendata.cern.ch/record/{record}"
DOSSIER_DEFAUT = os.path.join("donnees", "cern_open_data")
DELAI = 15

ENREGISTREMENTS: Dict[int, Dict[str, str]] = {
    545: {
        "titre": "CMS 2011 — candidats J/psi, Upsilon, W, Z et spectres dimuon / diélectron",
        "licence": "CC0-1.0",
        "annee": "2011",
        "note": "Sélection CMS pour l'enseignement ; sous-ensemble de l'information par événement.",
    },
    700: {
        "titre": "CMS 2010 — événements dimuon du jeu public Mu (Run2010B), en dix tranches",
        "licence": "voir la page CERN Open Data de l'enregistrement",
        "annee": "2010",
        "note": "Dix tranches de ~1,5 Mo + fichier complet : parfait pour une campagne avec référence.",
    },
}

# Instantané de l'API du CERN relevé le 2026-09-05 (clé, taille en octets, adler32).
INSTANTANE: Dict[int, List[Dict[str, object]]] = {
    545: [
        {"nom": "Wmunu.csv", "taille": 7969331, "adler32": "0607d5ee"},
        {"nom": "Wenu.csv", "taille": 9992209, "adler32": "1b06bb5d"},
        {"nom": "Zmumu.csv", "taille": 970550, "adler32": "0d4cfe9f"},
        {"nom": "Zee.csv", "taille": 1445651, "adler32": "3ad4c332"},
        {"nom": "Dimuon_SingleMu.csv", "taille": 11806904, "adler32": "3f2809bc"},
        {"nom": "Dimuon_DoubleMu.csv", "taille": 13935840, "adler32": "5b87a72a"},
        {"nom": "Jpsimumu.csv", "taille": 2639302, "adler32": "214e4077"},
        {"nom": "Ymumu.csv", "taille": 2599212, "adler32": "5eef7b87"},
    ],
    700: [
        {"nom": "MuRun2010B.csv", "taille": 15164517, "adler32": "19050705"},
        {"nom": "MuRun2010B_0.csv", "taille": 1515458, "adler32": "fcc5312a"},
        {"nom": "MuRun2010B_1.csv", "taille": 1519070, "adler32": "fb01b157"},
        {"nom": "MuRun2010B_2.csv", "taille": 1517788, "adler32": "7e84a8e9"},
        {"nom": "MuRun2010B_3.csv", "taille": 1514795, "adler32": "7f0bd04c"},
        {"nom": "MuRun2010B_4.csv", "taille": 1512480, "adler32": "35ebb241"},
        {"nom": "MuRun2010B_5.csv", "taille": 1513438, "adler32": "7c5b1042"},
        {"nom": "MuRun2010B_6.csv", "taille": 1517489, "adler32": "1e7bca3b"},
        {"nom": "MuRun2010B_7.csv", "taille": 1519419, "adler32": "30a1bccf"},
        {"nom": "MuRun2010B_8.csv", "taille": 1517741, "adler32": "4c596409"},
        {"nom": "MuRun2010B_9.csv", "taille": 1517640, "adler32": "9839f29c"},
    ],
}

DESCRIPTIONS: Dict[str, str] = {
    "Wmunu.csv": "candidats W → μν (un muon + énergie transverse manquante)",
    "Wenu.csv": "candidats W → eν (un électron + énergie transverse manquante)",
    "Zmumu.csv": "candidats Z → μμ",
    "Zee.csv": "candidats Z → ee",
    "Dimuon_SingleMu.csv": "spectre dimuon complet, déclenchement muon simple (100 000 événements)",
    "Dimuon_DoubleMu.csv": "spectre dimuon complet, déclenchement double muon (100 000 événements)",
    "Jpsimumu.csv": "candidats J/psi → μμ",
    "Ymumu.csv": "candidats Upsilon → μμ",
    "MuRun2010B.csv": "dimuons 2010, fichier complet (référence pour les dix tranches)",
}


@dataclass
class JeuDeDonnees:
    identifiant: str      # "545/Zmumu.csv"
    record: int
    nom: str
    titre: str
    description: str
    taille: int
    adler32: str
    licence: str
    annee: str
    url: str
    page: str

    @property
    def taille_mo(self) -> float:
        return self.taille / 1e6

    def chemin_local(self, dossier: str = DOSSIER_DEFAUT) -> str:
        return os.path.join(dossier, str(self.record), self.nom)

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["taille_mo"] = round(self.taille_mo, 2)
        return d


def _entree(record: int, nom: str, taille: int, adler32: str) -> JeuDeDonnees:
    meta = ENREGISTREMENTS[record]
    desc = DESCRIPTIONS.get(nom)
    if desc is None and nom.startswith("MuRun2010B_"):
        desc = f"dimuons 2010, tranche {nom.split('_')[1].split('.')[0]} (~{taille / 1e6:.1f} Mo)"
    return JeuDeDonnees(
        identifiant=f"{record}/{nom}", record=record, nom=nom, titre=meta["titre"],
        description=desc or nom, taille=int(taille), adler32=adler32.lower(),
        licence=meta["licence"], annee=meta["annee"],
        url=URL_FICHIER.format(record=record, nom=nom), page=URL_PAGE.format(record=record),
    )


def catalogue_instantane() -> List[JeuDeDonnees]:
    return [_entree(rec, f["nom"], f["taille"], f["adler32"]) for rec, fichiers in INSTANTANE.items() for f in fichiers]


def catalogue_en_ligne(delai: int = DELAI) -> List[JeuDeDonnees]:
    """Relit les fichiers de chaque enregistrement depuis l'API du CERN (lève une exception hors ligne)."""
    entrees: List[JeuDeDonnees] = []
    for rec in ENREGISTREMENTS:
        with urllib.request.urlopen(API.format(record=rec), timeout=delai) as rep:
            meta = json.load(rep).get("metadata", {})
        for f in meta.get("files", []):
            nom = f.get("key", "")
            if not nom.lower().endswith(".csv"):
                continue
            somme = str(f.get("checksum", "")).replace("adler32:", "")
            entrees.append(_entree(rec, nom, int(f.get("size", 0)), somme))
    if not entrees:
        raise RuntimeError("catalogue vide")
    return entrees


def catalogue(en_ligne: bool = True) -> List[JeuDeDonnees]:
    """Catalogue en ligne si possible, sinon l'instantané embarqué."""
    if en_ligne and os.environ.get("ANEMONE_SANS_RESEAU") != "1":
        try:
            return catalogue_en_ligne()
        except Exception:
            pass
    return catalogue_instantane()


def trouver(identifiant: str, entrees: Optional[List[JeuDeDonnees]] = None) -> JeuDeDonnees:
    for e in entrees or catalogue(en_ligne=False):
        if e.identifiant == identifiant or e.nom == identifiant:
            return e
    raise KeyError(f"Jeu de données inconnu : {identifiant}")


def adler32_fichier(chemin: str) -> str:
    somme = 1
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            somme = zlib.adler32(bloc, somme)
    return f"{somme & 0xFFFFFFFF:08x}"


_SOMMES_CONNUES: Dict[tuple, str] = {}  # (chemin, taille, mtime) → Adler-32 déjà calculé


def adler32_memorise(chemin: str) -> str:
    """Adler-32 du fichier, recalculé seulement si sa taille ou sa date de modification a changé."""
    stat = os.stat(chemin)
    cle = (os.path.abspath(chemin), stat.st_size, stat.st_mtime_ns)
    somme = _SOMMES_CONNUES.get(cle)
    if somme is None:
        somme = _SOMMES_CONNUES[cle] = adler32_fichier(chemin)
    return somme


def deja_present(entree: JeuDeDonnees, dossier: str = DOSSIER_DEFAUT) -> bool:
    chemin = entree.chemin_local(dossier)
    return os.path.isfile(chemin) and os.path.getsize(chemin) == entree.taille and adler32_memorise(chemin) == entree.adler32


TENTATIVES = 4


def _reprendre(temporaire: str) -> tuple:
    """Octets déjà reçus dans un téléchargement interrompu, et leur Adler-32 partiel."""
    if not os.path.isfile(temporaire):
        return 0, 1
    somme = 1
    with open(temporaire, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            somme = zlib.adler32(bloc, somme)
    return os.path.getsize(temporaire), somme


def telecharger(entree: JeuDeDonnees, dossier: str = DOSSIER_DEFAUT,
                rappel: Optional[Callable[[int, int], None]] = None, url: Optional[str] = None,
                tentatives: int = TENTATIVES) -> str:
    """Télécharge le fichier (si absent ou corrompu), vérifie l'Adler-32, renvoie le chemin local.

    Une connexion coupée n'est pas fatale : le téléchargement reprend où il s'est
    arrêté (en-tête HTTP Range), jusqu'à `tentatives` fois.
    """
    chemin = entree.chemin_local(dossier)
    if deja_present(entree, dossier):
        if rappel:
            rappel(entree.taille, entree.taille)
        return chemin
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    temporaire = chemin + ".partiel"
    derniere_erreur: Optional[Exception] = None
    for essai in range(1, tentatives + 1):
        recus, somme = _reprendre(temporaire)
        if recus > entree.taille:  # reste d'un autre fichier : on repart de zéro
            os.remove(temporaire)
            recus, somme = 0, 1
        try:
            requete = urllib.request.Request(url or entree.url)
            if recus:
                requete.add_header("Range", f"bytes={recus}-")
            with urllib.request.urlopen(requete, timeout=DELAI) as rep:
                if recus and rep.status != 206:  # le serveur ignore la reprise : on recommence
                    recus, somme = 0, 1
                with open(temporaire, "ab" if recus else "wb") as f:
                    while True:
                        bloc = rep.read(1 << 18)
                        if not bloc:
                            break
                        f.write(bloc)
                        somme = zlib.adler32(bloc, somme)
                        recus += len(bloc)
                        if rappel:
                            rappel(recus, entree.taille)
            derniere_erreur = None
            break
        except (OSError, ConnectionError) as exc:  # coupure réseau : on réessaie en reprenant
            derniere_erreur = exc
            if essai < tentatives:
                time.sleep(2 * essai)
    if derniere_erreur is not None:
        raise ConnectionError(f"{entree.nom} : téléchargement interrompu après {tentatives} tentatives ({derniere_erreur}). "
                              "Relancez : il reprendra où il s'est arrêté.")
    calculee = f"{somme & 0xFFFFFFFF:08x}"
    if calculee != entree.adler32 or recus != entree.taille:
        os.remove(temporaire)
        raise ValueError(f"{entree.nom} : intégrité non vérifiée (attendu {entree.adler32}/{entree.taille} octets, "
                         f"reçu {calculee}/{recus}). Fichier rejeté.")
    os.replace(temporaire, chemin)
    return chemin


def tout_telecharger(dossier: str = DOSSIER_DEFAUT, entrees: Optional[List[JeuDeDonnees]] = None,
                     rappel: Optional[Callable[[JeuDeDonnees, int, int], None]] = None) -> List[str]:
    chemins = []
    for e in entrees or catalogue():
        chemins.append(telecharger(e, dossier, (lambda r, t, e=e: rappel(e, r, t)) if rappel else None))
    return chemins


def _console_robuste() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def main(argv: Optional[List[str]] = None) -> int:
    _console_robuste()
    p = argparse.ArgumentParser(description="A.N.E.M.O.N.E — données réelles du CERN Open Data en un clic.")
    p.add_argument("identifiants", nargs="*", help="jeux à télécharger, ex. 545/Zmumu.csv (rien = --liste)")
    p.add_argument("--liste", action="store_true", help="afficher le catalogue")
    p.add_argument("--tout", action="store_true", help="tout télécharger")
    p.add_argument("--dossier", default=DOSSIER_DEFAUT)
    a = p.parse_args(argv)
    entrees = catalogue()
    if a.liste or (not a.tout and not a.identifiants):
        for e in entrees:
            etat = "présent" if deja_present(e, a.dossier) else "à télécharger"
            print(f"{e.identifiant:<28} {e.taille_mo:6.1f} Mo  {etat:<14} {e.description}")
        print(f"\nSource : {', '.join(URL_PAGE.format(record=r) for r in ENREGISTREMENTS)}")
        return 0
    cibles = entrees if a.tout else [trouver(i, entrees) for i in a.identifiants]
    for e in cibles:
        def rappel(recus: int, total: int, e=e) -> None:
            print(f"\r  {e.nom:<24} {100 * recus / max(total, 1):5.1f} %", end="", flush=True)
        try:
            chemin = telecharger(e, a.dossier, rappel)
            print(f"\r  {e.nom:<24} OK → {chemin}")
        except Exception as exc:
            print(f"\r  {e.nom:<24} ÉCHEC : {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
