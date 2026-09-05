# -*- coding: utf-8 -*-
"""Analyse à l'aveugle : le protocole est scellé avant de regarder la région du signal.

Pratique des grandes collaborations : on décide de tout AVANT de regarder là où
l'on espère un signal, sinon on finit toujours par trouver quelque chose. Ici :

1. le physicien scelle un protocole : variable, fenêtre [bas, haut), hypothèse,
   fichiers engagés (avec leur empreinte SHA-256) ou dossier de runs à venir,
   paramètres du test. Le protocole reçoit une empreinte et une date ; il est
   écrit dans `theses/protocoles/` ;
2. tant que le protocole est scellé, l'outil MASQUE la fenêtre : les événements
   qui y tombent sont retirés de tout ce qui s'affiche et s'analyse (vue 4D,
   isolés, registre, chasse aux bosses). Seul le fond attendu dans la fenêtre,
   estimé sur les bandes latérales, est montré ;
3. lever l'aveugle est un acte unique et irréversible : un seul test, à
   l'endroit scellé, sans facteur d'essais ; le résultat est écrit dans le
   protocole avec les empreintes des données réellement utilisées. Un protocole
   levé ne peut pas être relevé, ni modifié : toute analyse ultérieure de la
   même fenêtre est, par construction, « après coup ».
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import anemone_master as am
import anemone_bosse as ab

DOSSIER_PROTOCOLES = os.path.join("theses", "protocoles")
SEUIL_P_MOITIE = 1e-3


@dataclass
class Protocole:
    identifiant: str
    cree_le: str
    physicien: str
    hypothese: str
    variable: str
    bas: float
    haut: float
    fichiers: List[Dict[str, str]] = field(default_factory=list)   # [{"fichier", "sha256"}] engagés (vide : runs à venir)
    dossier: Optional[str] = None
    parametres: Dict[str, Any] = field(default_factory=dict)
    empreinte: str = ""
    etat: str = "scelle"                                            # scelle | leve
    resultat: Optional[Dict[str, Any]] = None
    chemin: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("chemin", None)
        return d

    def couvre(self, valeurs: pd.Series) -> pd.Series:
        return (valeurs >= self.bas) & (valeurs < self.haut)


def _sha256_fichier(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def empreinte_de(p: Protocole) -> str:
    """Empreinte du protocole : tout ce qui est décidé avant de regarder, rien de ce qui vient après."""
    contenu = {k: v for k, v in p.to_dict().items() if k not in ("empreinte", "etat", "resultat")}
    return hashlib.sha256(json.dumps(contenu, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def sceller(variable: str, bas: float, haut: float, hypothese: str = "", physicien: str = "",
            fichiers: Sequence[str] = (), dossier: Optional[str] = None,
            dossier_protocoles: str = DOSSIER_PROTOCOLES) -> Protocole:
    if not (haut > bas):
        raise ValueError("la fenêtre doit vérifier haut > bas")
    maintenant = datetime.now()
    engages = [{"fichier": os.path.basename(f), "sha256": _sha256_fichier(f)} for f in fichiers]
    p = Protocole(identifiant="", cree_le=maintenant.isoformat(timespec="seconds"), physicien=physicien, hypothese=hypothese,
                  variable=variable, bas=float(bas), haut=float(haut), fichiers=engages, dossier=dossier,
                  parametres={"n_classes": ab.N_CLASSES, "bande": ab.BANDE, "seuil_p_decouverte": ab.P_CINQ_SIGMA,
                              "seuil_p_moitie": SEUIL_P_MOITIE, "version_outil": am.VERSION_OUTIL})
    p.empreinte = empreinte_de(p)
    p.identifiant = "P" + maintenant.strftime("%Y%m%d_%H%M%S") + "_" + p.empreinte[:6]
    p.empreinte = empreinte_de(p)     # l'identifiant fait partie du contenu scellé
    os.makedirs(dossier_protocoles, exist_ok=True)
    p.chemin = os.path.join(dossier_protocoles, p.identifiant + ".json")
    _ecrire(p)
    return p


def _ecrire(p: Protocole) -> None:
    with open(p.chemin, "w", encoding="utf-8") as f:
        json.dump(p.to_dict(), f, ensure_ascii=False, indent=1)


def charger(chemin: str) -> Protocole:
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    p = Protocole(**d)
    p.chemin = chemin
    return p


def lister(dossier_protocoles: str = DOSSIER_PROTOCOLES) -> List[Protocole]:
    if not os.path.isdir(dossier_protocoles):
        return []
    return sorted((charger(os.path.join(dossier_protocoles, f)) for f in os.listdir(dossier_protocoles) if f.endswith(".json")),
                  key=lambda p: p.cree_le)


def integre(p: Protocole) -> bool:
    """Vrai si le contenu scellé n'a pas été modifié depuis la signature."""
    return empreinte_de(p) == p.empreinte


def scelles(dossier_protocoles: str = DOSSIER_PROTOCOLES) -> List[Protocole]:
    return [p for p in lister(dossier_protocoles) if p.etat == "scelle"]


def masquer(matrice: pd.DataFrame, protocoles: Sequence[Protocole]) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Retire de la matrice les événements des fenêtres scellées (tant que l'aveugle n'est pas levé)."""
    garde = pd.Series(True, index=matrice.index)
    masques: List[Dict[str, Any]] = []
    for p in protocoles:
        if p.etat != "scelle" or p.variable not in matrice.columns:
            continue
        dans = p.couvre(matrice[p.variable])
        n = int(dans.sum())
        garde &= ~dans
        masques.append({"protocole": p.identifiant, "variable": p.variable, "bas": p.bas, "haut": p.haut, "n_masques": n})
    return matrice[garde], masques


def fond_attendu(p: Protocole, matrice: pd.DataFrame) -> Dict[str, Any]:
    """Ce qu'on a le droit de voir avant de lever l'aveugle : le fond attendu dans la fenêtre, jamais l'observé."""
    if p.variable not in matrice.columns:
        return {"testable": False, "detail": f"variable {p.variable} absente"}
    x = matrice[p.variable].to_numpy(float)
    x = x[np.isfinite(x)]
    if len(x) < 200:
        return {"testable": False, "detail": "trop peu d'événements"}
    bords, echelle = ab.classes(x, p.parametres.get("n_classes", ab.N_CLASSES))
    i0, i1 = ab.fenetre_autour(bords, (p.bas + p.haut) / 2, (p.haut - p.bas) / 2)
    comptes, _ = np.histogram(x, bins=bords)
    attendu = ab._fond_attendu(comptes, i0, i1 - i0)
    if attendu is None:
        return {"testable": False, "detail": "fond non estimable : bandes latérales mal décrites (bord, seuil) ou trop étroites",
                "fenetre_classes": [float(bords[i0]), float(bords[i1])]}
    return {"testable": True, "attendu": float(attendu), "fenetre_classes": [float(bords[i0]), float(bords[i1])], "echelle": echelle,
            "n_evenements": int(len(x)), "detail": f"fond attendu dans la fenêtre : {attendu:.1f} événements (bandes latérales seules)"}


def lever(p: Protocole, matrice: pd.DataFrame, fichiers_utilises: Sequence[str] = ()) -> Protocole:
    """L'acte irréversible : un seul test à l'endroit scellé. Refusé si l'aveugle est déjà levé ou le protocole altéré."""
    if p.etat == "leve":
        raise RuntimeError(f"aveugle déjà levé le {p.resultat.get('leve_le') if p.resultat else '?'} : un protocole ne se relève pas")
    if not integre(p):
        raise RuntimeError("protocole altéré depuis son scellement : empreinte différente")
    if p.variable not in matrice.columns:
        raise ValueError(f"variable {p.variable} absente des données")
    x = matrice[p.variable].to_numpy(float)
    x = x[np.isfinite(x)]
    bords, echelle = ab.classes(x, p.parametres.get("n_classes", ab.N_CLASSES))
    i0, i1 = ab.fenetre_autour(bords, (p.bas + p.haut) / 2, (p.haut - p.bas) / 2)
    r = ab.exces_dans_fenetre(x, bords, i0, i1)
    utilises = [{"fichier": os.path.basename(f), "sha256": _sha256_fichier(f)} for f in fichiers_utilises if os.path.isfile(f)]
    engages = {f["sha256"] for f in p.fichiers}
    conformes = None if not engages else all(u["sha256"] in engages for u in utilises) and bool(utilises)
    n = len(x) // 2
    r1 = ab.exces_dans_fenetre(x[:n], bords, i0, i1)
    r2 = ab.exces_dans_fenetre(x[n:], bords, i0, i1)
    moities = (r1["testable"] and r2["testable"] and r1["p_local"] < SEUIL_P_MOITIE and r2["p_local"] < SEUIL_P_MOITIE) \
        if (r1["testable"] and r2["testable"]) else None
    resultat = {
        "leve_le": datetime.now().isoformat(timespec="seconds"), "n_evenements": int(len(x)),
        "fenetre_classes": [float(bords[i0]), float(bords[i1])], "echelle": echelle,
        "observe": r["observe"], "attendu": r["attendu"], "p_local": r["p_local"], "z_local": r["z_local"], "testable": r["testable"],
        "decouverte": bool(r["testable"] and r["p_local"] < p.parametres.get("seuil_p_decouverte", ab.P_CINQ_SIGMA)),
        "deux_moities": moities,
        "fichiers_utilises": utilises, "donnees_conformes_au_protocole": conformes,
        "version_outil": am.VERSION_OUTIL,
    }
    if not r["testable"]:
        resultat["verdict"] = "non testable : fond non estimable dans la fenêtre"
    elif resultat["decouverte"] and moities is not False and conformes is not False:
        resultat["verdict"] = "excès au-delà de 5 σ à l'endroit scellé, sans facteur d'essais : à soumettre au physicien"
    elif resultat["decouverte"]:
        resultat["verdict"] = "excès au-delà de 5 σ, mais " + ("il ne tient pas dans chaque moitié" if moities is False else
                                                              "les données ne sont pas celles engagées") + " : réserve"
    elif r["p_local"] < SEUIL_P_MOITIE:
        resultat["verdict"] = "excès sous 5 σ : indice, pas preuve"
    else:
        resultat["verdict"] = "aucun excès à l'endroit scellé : hypothèse non soutenue"
    p.resultat = resultat
    p.etat = "leve"
    if p.chemin:
        _ecrire(p)
        with open(os.path.splitext(p.chemin)[0] + ".md", "w", encoding="utf-8") as f:
            f.write(rediger(p))
    return p


def rediger(p: Protocole) -> str:
    L = [f"# Protocole d'analyse à l'aveugle {p.identifiant}", "",
         f"- scellé le {p.cree_le}" + (f" par {p.physicien}" if p.physicien else ""),
         f"- empreinte `{p.empreinte}`" + ("" if integre(p) else " — **ALTÉRÉ** (empreinte différente)"),
         f"- variable `{p.variable}`, fenêtre [{p.bas:g}, {p.haut:g})",
         f"- hypothèse : {p.hypothese or '(aucune)'}",
         f"- données engagées : " + (", ".join(f"`{f['fichier']}` ({f['sha256'][:12]}…)" for f in p.fichiers) if p.fichiers
                                    else (f"runs à venir dans `{p.dossier}`" if p.dossier else "non précisées")),
         f"- paramètres : " + ", ".join(f"{k} = {v}" for k, v in p.parametres.items()), ""]
    if p.etat == "scelle":
        L += ["## État : scellé", "", "La fenêtre est masquée dans tout l'outil. Seul le fond attendu (bandes latérales) peut être consulté.", ""]
        return "\n".join(L)
    r = p.resultat or {}
    L += ["## État : aveugle levé", "", f"- levé le {r.get('leve_le')} sur {r.get('n_evenements')} événements"]
    if r.get("testable"):
        L += [f"- fenêtre de classes [{r['fenetre_classes'][0]:.4g}, {r['fenetre_classes'][1]:.4g}] ({r['echelle']})",
              f"- **{r['observe']} observés pour {r['attendu']:.1f} attendus**, p = {r['p_local']:.2g}, z = {r['z_local']:.1f} (un seul test, sans facteur d'essais)",
              f"- tient dans chaque moitié : {'oui' if r['deux_moities'] else ('non' if r['deux_moities'] is False else 'non testable')}"]
    L += [f"- données utilisées : " + (", ".join(f"`{f['fichier']}` ({f['sha256'][:12]}…)" for f in r.get("fichiers_utilises", [])) or "non précisées"),
          f"- conformes au protocole : {'oui' if r.get('donnees_conformes_au_protocole') else ('NON' if r.get('donnees_conformes_au_protocole') is False else 'aucun fichier engagé')}",
          "", f"**Verdict : {r.get('verdict')}**", "",
          "Ce résultat est définitif pour ce protocole. Toute nouvelle analyse de cette fenêtre est, par construction, après coup.", ""]
    return "\n".join(L)


def main(argv: Optional[Sequence[str]] = None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    ap = argparse.ArgumentParser(description="A.N.E.M.O.N.E — analyse à l'aveugle : sceller, lister, lever.")
    sub = ap.add_subparsers(dest="commande", required=True)
    s = sub.add_parser("sceller")
    s.add_argument("--variable", required=True)
    s.add_argument("--bas", type=float, required=True)
    s.add_argument("--haut", type=float, required=True)
    s.add_argument("--hypothese", default="")
    s.add_argument("--physicien", default="")
    s.add_argument("--dossier", default=None)
    s.add_argument("fichiers", nargs="*")
    s.add_argument("--protocoles", default=DOSSIER_PROTOCOLES)
    li = sub.add_parser("lister")
    li.add_argument("--protocoles", default=DOSSIER_PROTOCOLES)
    le = sub.add_parser("lever")
    le.add_argument("identifiant")
    le.add_argument("fichiers", nargs="+")
    le.add_argument("--protocoles", default=DOSSIER_PROTOCOLES)
    le.add_argument("--oui", action="store_true", help="confirme l'acte irréversible")
    args = ap.parse_args(argv)
    if args.commande == "sceller":
        p = sceller(args.variable, args.bas, args.haut, args.hypothese, args.physicien, args.fichiers, args.dossier, args.protocoles)
        print(f"[AVEUGLE] Protocole {p.identifiant} scellé (empreinte {p.empreinte[:12]}…) : {p.chemin}")
        return 0
    if args.commande == "lister":
        for p in lister(args.protocoles):
            print(f"{p.identifiant}  {p.etat:<6}  {p.variable} [{p.bas:g}, {p.haut:g})  {p.hypothese[:60]}")
        return 0
    if not args.oui:
        print("[AVEUGLE] Lever l'aveugle est irréversible : ajoutez --oui pour confirmer.")
        return 2
    cible = [p for p in lister(args.protocoles) if p.identifiant == args.identifiant]
    if not cible:
        print(f"[AVEUGLE] protocole inconnu : {args.identifiant}")
        return 2
    morceaux = [am.analyser_fichier_physique(f, os.path.basename(f))[0] for f in args.fichiers]
    matrice = pd.concat(morceaux, ignore_index=True)
    p = lever(cible[0], matrice, args.fichiers)
    print(f"[AVEUGLE] {p.resultat['verdict']}")
    print(rediger(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
