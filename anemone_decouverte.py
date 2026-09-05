# -*- coding: utf-8 -*-
"""Run de découverte : de l'hypothèse à la thèse, en un clic, soumise ensuite au physicien.

Le run prend des fichiers d'événements (ou un dossier), une hypothèse
facultative, éventuellement un run de référence, puis :

1. lit chaque fichier, ajoute les grandeurs dérivées (masse invariante d'une
   paire quand elle peut être calculée) et choisit les variables de chasse :
   les masses d'abord, sinon les grandeurs spectrales (énergies, impulsions
   transverses…), jamais les angles ;
2. chasse les bosses (anemone_bosse) ;
3. pour chaque bosse, cherche les AUTRES explications, chacune par un calcul :
   fluctuation statistique (seuil 5 σ après correction du nombre de fenêtres),
   moitié de run seulement (épisode ou dérive : la bosse doit tenir dans chaque
   moitié), artefact de découpage (elle doit tenir avec un autre nombre de
   classes), bord ou seuil de déclenchement, présence identique dans le run de
   référence, coïncidence avec une résonance déjà connue (table PDG) ;
4. teste l'hypothèse du physicien à l'endroit qu'il indique, sans facteur
   d'essais (un seul test) ;
5. conclut : « thèse candidate » seulement si une bosse passe toutes les
   épreuves et ne coïncide avec rien de connu ; sinon « instrument validé »
   (résonances connues retrouvées) ou « rien à soumettre ». Écrit la thèse
   (Markdown + JSON, empreintes des fichiers, versions) dans `theses/`.

Aucune conclusion n'est physique : la thèse est un dossier de preuves
calculées, que seul un physicien peut transformer en résultat.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import anemone_master as am
import anemone_bosse as ab

DOSSIER_THESES = "theses"
SEUIL_P_MOITIE = 1e-3          # la bosse doit être visible (p locale) dans chaque moitié du run
SEUIL_P_REFERENCE = 1e-3       # présente aussi dans la référence si p locale < seuil là-bas
TOLERANCE_CONNUE = 0.025       # ±2,5 % autour d'une masse connue (résolution + découpage)
DEMI_LARGEUR_HYPOTHESE = 0.02  # ±2 % autour de la valeur indiquée par le physicien, si aucune largeur n'est donnée

# Résonances connues, masses publiées par le Particle Data Group (GeV/c²). Une bosse qui coïncide
# avec l'une d'elles n'est pas nouvelle : c'est l'instrument qui retrouve la physique établie.
RESONANCES_CONNUES = {
    "ω(782)": 0.78266, "φ(1020)": 1.019461, "J/ψ(1S)": 3.096900, "ψ(2S)": 3.686097,
    "Υ(1S)": 9.46040, "Υ(2S)": 10.02326, "Υ(3S)": 10.3552, "Z": 91.1876, "H (Higgs)": 125.25,
}


@dataclass
class Hypothese:
    texte: str = ""
    variable: Optional[str] = None
    valeur: Optional[float] = None
    demi_largeur: Optional[float] = None

    def est_localisee(self) -> bool:
        return bool(self.variable) and self.valeur is not None


@dataclass
class Candidat:
    fichier: str
    bosse: Dict[str, Any]
    epreuves: Dict[str, Dict[str, Any]] = field(default_factory=dict)   # nom → {"ok": bool|None, "detail": str}
    connue: Optional[str] = None
    verdict: str = ""                                                     # these | connue | indice | structure | ecarte
    raisons: List[str] = field(default_factory=list)
    cumul: Optional[List[Dict[str, Any]]] = None                          # courbe de l'excès run après run (candidats de cumul)


@dataclass
class TestHypothese:
    fichier: str
    variable: str
    fenetre: List[float]
    observe: int
    attendu: Optional[float]
    p_local: Optional[float]
    z_local: Optional[float]
    soutenue: Optional[bool]
    detail: str


@dataclass
class RunDecouverte:
    horodatage: str
    hypothese: Dict[str, Any]
    fichiers: List[Dict[str, Any]]
    candidats: List[Dict[str, Any]]
    tests_hypothese: List[Dict[str, Any]]
    conclusion: str            # these | connue | indice | rien
    resume: str
    a_verifier: List[str]
    versions: Dict[str, str]
    reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sha256(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def variables_de_chasse(matrice: pd.DataFrame) -> List[str]:
    """Masses (présentes ou dérivées) d'abord ; sinon les grandeurs spectrales par défaut, sans les angles."""
    masses = [c for c in matrice.columns if am.est_masse(c) or c == "M_paire"]
    if masses:
        return masses
    return ab.colonnes_spectrales(am.colonnes_analysables(list(matrice.columns)))[:8]


MAX_LARGEUR_RELATIVE = 0.12    # une résonance est étroite : au-delà de 12 % de largeur relative, c'est une « structure »


def est_variable_de_masse(colonne: str) -> bool:
    return am.est_masse(colonne) or colonne == "M_paire"


def resonance_connue(bord_bas: float, bord_haut: float) -> Optional[str]:
    """Résonance connue dont la masse tombe dans la fenêtre (élargie de la tolérance)."""
    trouvees = [(nom, masse) for nom, masse in RESONANCES_CONNUES.items()
                if bord_bas * (1 - TOLERANCE_CONNUE) <= masse <= bord_haut * (1 + TOLERANCE_CONNUE)]
    if not trouvees:
        return None
    return ", ".join(f"{nom} ({masse:g} GeV, PDG)" for nom, masse in trouvees)


def _moities(matrice: pd.DataFrame) -> tuple:
    """Deux moitiés dans l'ordre du fichier (l'ordre d'enregistrement), par numéro de run si présent."""
    if "Run" in matrice.columns and matrice["Run"].nunique() >= 2:
        ordre = matrice.sort_values("Run", kind="stable")
    else:
        ordre = matrice
    n = len(ordre) // 2
    return ordre.iloc[:n], ordre.iloc[n:]


def eprouver(bosse: ab.Bosse, matrice: pd.DataFrame, reference: Optional[pd.DataFrame]) -> Candidat:
    """Toutes les autres explications d'une bosse, chacune tranchée par un calcul."""
    x = matrice[bosse.variable].to_numpy(float)
    bords, _ = ab.classes(x)
    cand = Candidat(fichier="", bosse=bosse.to_dict())
    ep = cand.epreuves

    ep["fluctuation"] = {"ok": bosse.p_global < ab.P_CINQ_SIGMA,
                         "detail": f"p globale {bosse.p_global:.2g} ({bosse.n_tests} fenêtres testées) ; seuil 5 σ = {ab.P_CINQ_SIGMA:.2g}"}

    m1, m2 = _moities(matrice)
    r1 = ab.exces_dans_fenetre(m1[bosse.variable].to_numpy(float), bords, bosse.i_debut, bosse.i_fin)
    r2 = ab.exces_dans_fenetre(m2[bosse.variable].to_numpy(float), bords, bosse.i_debut, bosse.i_fin)
    ok_moities = None
    if r1["testable"] and r2["testable"]:
        ok_moities = r1["p_local"] < SEUIL_P_MOITIE and r2["p_local"] < SEUIL_P_MOITIE
    ep["deux_moities"] = {"ok": ok_moities, "detail": (
        f"1re moitié : {r1['observe']} observés / {r1['attendu']:.1f} attendus, p = {r1['p_local']:.2g} ; "
        f"2de moitié : {r2['observe']} / {r2['attendu']:.1f}, p = {r2['p_local']:.2g}" if ok_moities is not None
        else "fond non estimable sur une moitié (trop peu d'événements)")}

    n_alt = int(ab.N_CLASSES * 0.8)
    bords_alt, _ = ab.classes(x, n_alt)
    j0, j1 = ab.fenetre_autour(bords_alt, bosse.centre, (bosse.bord_haut - bosse.bord_bas) / 2)
    ra = ab.exces_dans_fenetre(x, bords_alt, j0, j1)
    ep["decoupage"] = {"ok": (ra["p_local"] < SEUIL_P_MOITIE) if ra["testable"] else None,
                       "detail": (f"avec {n_alt} classes : {ra['observe']} observés / {ra['attendu']:.1f} attendus, p = {ra['p_local']:.2g}"
                                  if ra["testable"] else f"fond non estimable avec {n_alt} classes")}

    ep["bord"] = {"ok": not bosse.au_bord, "detail": "au bord du spectre (seuil, coupure ?)" if bosse.au_bord else "loin des bords"}

    if reference is not None and bosse.variable in reference.columns:
        rr = ab.exces_dans_fenetre(reference[bosse.variable].to_numpy(float), bords, bosse.i_debut, bosse.i_fin)
        if rr["testable"]:
            presente = rr["p_local"] < SEUIL_P_REFERENCE
            ep["reference"] = {"ok": not presente, "detail": (f"référence : {rr['observe']} observés / {rr['attendu']:.1f} attendus, "
                                                             f"p = {rr['p_local']:.2g}" + (" → présente aussi dans la référence" if presente else " → absente de la référence"))}
        else:
            ep["reference"] = {"ok": None, "detail": "référence : fond non estimable dans cette fenêtre"}
    else:
        ep["reference"] = {"ok": None, "detail": "aucun run de référence fourni"}

    masse = est_variable_de_masse(bosse.variable)
    cand.connue = resonance_connue(bosse.bord_bas, bosse.bord_haut) if masse else None
    lr = ab.largeur_relative(bosse)
    ep["etroitesse"] = {"ok": lr <= MAX_LARGEUR_RELATIVE,
                        "detail": f"largeur relative {100 * lr:.0f} % (résonance attendue ≤ {100 * MAX_LARGEUR_RELATIVE:.0f} %)"}
    echecs = [nom for nom, e in ep.items() if e["ok"] is False]
    if cand.connue and not [n for n in echecs if n not in ("etroitesse",)]:
        cand.verdict = "connue"          # une famille de résonances (Υ 1S/2S/3S) peut remplir une fenêtre large
        cand.raisons = [f"coïncide avec {cand.connue} : physique établie retrouvée, pas une nouveauté"]
    elif echecs:
        if echecs == ["fluctuation"]:
            cand.verdict = "indice"
            cand.raisons = ["significative après correction, mais sous 5 σ : indice, pas preuve"]
        elif echecs == ["etroitesse"]:
            cand.verdict = "structure"
            cand.raisons = ["excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance"]
        else:
            cand.verdict = "ecarte"
            cand.raisons = [f"{nom} : {ep[nom]['detail']}" for nom in echecs]
    elif not masse:
        cand.verdict = "structure"
        cand.raisons = [f"excès solide sur {bosse.variable}, qui n'est pas une masse : structure cinématique ou instrumentale "
                        "à interpréter, pas une résonance"]
    else:
        cand.verdict = "these"
        cand.raisons = ["passe toutes les épreuves, étroite, sur une masse, et ne coïncide avec aucune résonance connue"]
    return cand


def tester_hypothese(h: Hypothese, matrice: pd.DataFrame, fichier: str) -> Optional[TestHypothese]:
    if not h.est_localisee() or h.variable not in matrice.columns:
        return None
    x = matrice[h.variable].to_numpy(float)
    bords, _ = ab.classes(x)
    demi = h.demi_largeur if h.demi_largeur else abs(h.valeur) * DEMI_LARGEUR_HYPOTHESE
    i0, i1 = ab.fenetre_autour(bords, h.valeur, demi)
    r = ab.exces_dans_fenetre(x, bords, i0, i1)
    if not r["testable"]:
        return TestHypothese(fichier, h.variable, [float(bords[i0]), float(bords[i1])], r["observe"], None, None, None, None,
                             "fond non estimable à cet endroit (bord du spectre ou trop peu d'événements)")
    soutenue = r["p_local"] < ab.P_CINQ_SIGMA
    detail = (f"{r['observe']} observés pour {r['attendu']:.1f} attendus, p = {r['p_local']:.2g} (un seul test, sans facteur d'essais) → "
              + ("excès à plus de 5 σ : hypothèse soutenue par ce run" if soutenue else
                 ("excès sous 5 σ : indice seulement" if r["p_local"] < SEUIL_P_MOITIE else "aucun excès : hypothèse non soutenue")))
    return TestHypothese(fichier, h.variable, [float(bords[i0]), float(bords[i1])], r["observe"], r["attendu"],
                         r["p_local"], r["z_local"], soutenue, detail)


def cumuler(morceaux: Sequence[Tuple[str, pd.Series]]) -> pd.DataFrame:
    """Empile la même variable de plusieurs runs ; la colonne Run garde l'ordre des fichiers (pour l'épreuve des moitiés)."""
    return pd.concat([pd.DataFrame({"Run": i, "Event": np.arange(len(v)), v.name: v.to_numpy(float)})
                      for i, (_, v) in enumerate(morceaux)], ignore_index=True)


def courbe_cumul(morceaux: Sequence[Tuple[str, pd.Series]], variable: str, bosse: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comment l'excès évolue à mesure que les runs s'ajoutent : observé, attendu, z après chaque fichier."""
    tout = cumuler(morceaux)[variable].to_numpy(float)
    bords, _ = ab.classes(tout)
    i0, i1 = ab.fenetre_autour(bords, bosse["centre"], (bosse["bord_haut"] - bosse["bord_bas"]) / 2)
    courbe = []
    acc: List[np.ndarray] = []
    for nom, v in morceaux:
        acc.append(v.to_numpy(float))
        r = ab.exces_dans_fenetre(np.concatenate(acc), bords, i0, i1)
        courbe.append({"apres": nom, "n_fichiers": len(acc), "n_evenements": int(sum(len(a) for a in acc)),
                       "observe": r["observe"], "attendu": r["attendu"], "z": r["z_local"], "p": r["p_local"]})
    return courbe


def lancer_run(chemins: Sequence[str], hypothese: Optional[Hypothese] = None, reference: Optional[str] = None,
               max_evenements: Optional[int] = None, rappel: Optional[Callable[[str], None]] = None,
               cumul: bool = True) -> RunDecouverte:
    h = hypothese or Hypothese()
    dire = rappel or (lambda m: None)
    ref_matrice = None
    if reference:
        ref_matrice, _ = am.analyser_fichier_physique(reference, os.path.basename(reference), max_evenements=max_evenements)
    fichiers: List[Dict[str, Any]] = []
    candidats: List[Candidat] = []
    tests: List[TestHypothese] = []
    par_variable: Dict[str, List[Tuple[str, pd.Series]]] = {}
    for chemin in chemins:
        nom = os.path.basename(chemin)
        dire(f"lecture de {nom}")
        try:
            matrice, rapport = am.analyser_fichier_physique(chemin, nom, max_evenements=max_evenements)
        except Exception as exc:
            fichiers.append({"fichier": nom, "chemin": chemin, "erreur": str(exc)})
            continue
        variables = variables_de_chasse(matrice)
        fichiers.append({"fichier": nom, "chemin": chemin, "sha256": _sha256(chemin), "n_evenements": int(len(matrice)),
                         "variables_de_chasse": variables, "derivees": rapport.get("derivees", [])})
        for v in variables:
            if est_variable_de_masse(v):
                par_variable.setdefault(v, []).append((nom, matrice[v]))
        dire(f"chasse aux bosses dans {nom} ({', '.join(variables)})")
        for b in ab.chasser_matrice(matrice, variables):
            cand = eprouver(b, matrice, ref_matrice)
            cand.fichier = nom
            candidats.append(cand)
        t = tester_hypothese(h, matrice, nom)
        if t:
            tests.append(t)
    # Cumul : la même masse empilée sur tous les runs qui la portent. La significativité croît comme √N :
    # un excès invisible run par run peut apparaître ici, et les moitiés (premiers / derniers runs) le contrôlent.
    if cumul:
        for variable, morceaux in par_variable.items():
            if len(morceaux) < 2:
                continue
            nom = f"CUMUL {len(morceaux)} runs ({variable})"
            dire(f"cumul de {len(morceaux)} runs sur {variable}")
            empile = cumuler(morceaux)
            for b in ab.chasser_matrice(empile, [variable]):
                cand = eprouver(b, empile, ref_matrice)
                cand.fichier = nom
                cand.cumul = courbe_cumul(morceaux, variable, cand.bosse)
                candidats.append(cand)
            t = tester_hypothese(h, empile, nom)
            if t:
                tests.append(t)
    ordre = {"these": 0, "connue": 1, "indice": 2, "structure": 3, "ecarte": 4}
    candidats.sort(key=lambda c: (ordre[c.verdict], c.bosse["p_global"]))
    verdicts = {c.verdict for c in candidats}
    if "these" in verdicts:
        conclusion = "these"
    elif "connue" in verdicts:
        conclusion = "connue"
    elif "indice" in verdicts or "structure" in verdicts:
        conclusion = "indice"
    else:
        conclusion = "rien"
    run = RunDecouverte(
        horodatage=datetime.now().isoformat(timespec="seconds"), hypothese=asdict(h), fichiers=fichiers,
        candidats=[asdict(c) for c in candidats], tests_hypothese=[asdict(t) for t in tests], conclusion=conclusion,
        resume="", a_verifier=[], versions=_versions(), reference=reference,
    )
    run.resume = _resume(run)
    run.a_verifier = _a_verifier(run)
    return run


def _versions() -> Dict[str, str]:
    import platform
    v = {"anemone": am.VERSION_OUTIL, "python": platform.python_version()}
    for paquet in ("numpy", "pandas", "scipy", "scikit-learn"):
        try:
            from importlib.metadata import version
            v[paquet] = version(paquet)
        except Exception:  # pragma: no cover
            v[paquet] = "?"
    return v


def _resume(run: RunDecouverte) -> str:
    n_these = sum(c["verdict"] == "these" for c in run.candidats)
    n_connues = sum(c["verdict"] == "connue" for c in run.candidats)
    n_indices = sum(c["verdict"] in ("indice", "structure") for c in run.candidats)
    n_ecartes = sum(c["verdict"] == "ecarte" for c in run.candidats)
    if run.conclusion == "these":
        tete = f"THÈSE CANDIDATE : {n_these} bosse(s) passent toutes les épreuves et ne coïncident avec aucune résonance connue."
    elif run.conclusion == "connue":
        tete = (f"Instrument validé, rien de nouveau : {n_connues} résonance(s) connue(s) retrouvée(s) à l'aveugle, "
                "aucune bosse inexpliquée.")
    elif run.conclusion == "indice":
        tete = f"Indice(s) seulement : {n_indices} bosse(s) ou structure(s) significatives, mais sous 5 σ, larges ou hors masse."
    else:
        tete = "Rien à soumettre : aucune bosse significative."
    return tete + f" ({len(run.fichiers)} fichier(s), {len(run.candidats)} bosse(s) examinées, {n_ecartes} écartée(s).)"


def _a_verifier(run: RunDecouverte) -> List[str]:
    lignes = []
    if run.conclusion == "these":
        lignes += [
            "Vérifier la sélection des événements (déclenchement, coupures) : un excès peut naître d'une coupure.",
            "Comparer à la simulation du fond (Monte-Carlo) : le fond lisse ajusté ici n'est qu'une approximation locale.",
            "Contrôler la résolution de l'appareil autour de la bosse : une largeur inférieure à la résolution est suspecte.",
            "Refaire l'analyse sur un run indépendant : la bosse doit réapparaître au même endroit.",
        ]
    if run.reference is None:
        lignes.append("Fournir un run de référence (calibration, fond connu) : l'épreuve « référence » n'a pas pu être menée.")
    if any(c["verdict"] == "connue" for c in run.candidats):
        lignes.append("Les coïncidences avec des résonances connues sont établies sur la masse seule (±2,5 %) : à confirmer par le physicien.")
    lignes.append("Rien ici n'est une conclusion physique : c'est un dossier de calculs à valider.")
    return lignes


NOMS_EPREUVES = {"fluctuation": "Fluctuation statistique (5 σ après correction)", "deux_moities": "Tient dans chaque moitié du run",
                 "decoupage": "Tient avec un autre découpage", "bord": "Loin des bords et seuils", "reference": "Absente du run de référence",
                 "etroitesse": "Étroite comme une résonance"}


def rediger_these(run: RunDecouverte) -> str:
    L = [f"# Run de découverte A.N.E.M.O.N.E — {run.horodatage}", "", f"**Conclusion : {run.resume}**", ""]
    h = run.hypothese
    L += ["## Hypothèse", ""]
    if h.get("texte"):
        L.append(f"> {h['texte']}")
        L.append("")
    if h.get("variable") and h.get("valeur") is not None:
        L.append(f"Localisée : `{h['variable']}` autour de {h['valeur']:g}"
                 + (f" ± {h['demi_largeur']:g}" if h.get("demi_largeur") else f" (± {100 * DEMI_LARGEUR_HYPOTHESE:.0f} %)") + ".")
    elif not h.get("texte"):
        L.append("Aucune hypothèse : recherche libre.")
    L += ["", "## Données", ""]
    for f in run.fichiers:
        if "erreur" in f:
            L.append(f"- `{f['fichier']}` : lecture impossible ({f['erreur']})")
        else:
            L.append(f"- `{f['fichier']}` : {f['n_evenements']} événements, variables de chasse {', '.join(f['variables_de_chasse'])}"
                     + (f", dérivées : {', '.join(f['derivees'])}" if f["derivees"] else "") + f" (SHA-256 `{f['sha256'][:16]}…`)")
    if run.reference:
        L.append(f"- référence : `{os.path.basename(run.reference)}`")
    L += ["", "## Méthode", "",
          "Chasse aux bosses sur chaque variable de chasse : histogramme (classes logarithmiques ou linéaires), fond lisse "
          "ajusté sur les bandes latérales de chaque fenêtre, probabilité de Poisson d'un tel excès, correction du nombre "
          "de fenêtres et de variables testées (Bonferroni). Chaque bosse est ensuite soumise aux épreuves ci-dessous ; "
          "l'hypothèse localisée est testée à son endroit exact, sans facteur d'essais.", ""]
    if run.tests_hypothese:
        L += ["## Test de l'hypothèse", ""]
        for t in run.tests_hypothese:
            L.append(f"- `{t['fichier']}`, `{t['variable']}` dans [{t['fenetre'][0]:.4g}, {t['fenetre'][1]:.4g}] : {t['detail']}")
        L.append("")
    L += ["## Bosses examinées", ""]
    if not run.candidats:
        L.append("Aucune bosse significative (p globale < 0,001) dans les variables de chasse.")
    etiquettes = {"these": "🔴 THÈSE CANDIDATE", "connue": "🟢 connue", "indice": "🟠 indice", "structure": "🟡 structure", "ecarte": "⚪ écartée"}
    for c in run.candidats:
        b = c["bosse"]
        L.append(f"### {etiquettes[c['verdict']]} — `{c['fichier']}` : {b['variable']} ≈ {b['centre']:.4g}")
        L.append(f"- fenêtre [{b['bord_bas']:.4g}, {b['bord_haut']:.4g}] : {b['observe']} observés pour {b['attendu']:.1f} attendus, "
                 f"z local = {b['z_local']:.1f}, p globale = {b['p_global']:.2g} ({b['n_tests']} fenêtres testées)")
        for nom, e in c["epreuves"].items():
            marque = {True: "✅", False: "❌", None: "➖"}[e["ok"]]
            L.append(f"- {marque} {NOMS_EPREUVES[nom]} : {e['detail']}")
        if c["connue"]:
            L.append(f"- coïncidence : {c['connue']}")
        if c.get("cumul"):
            L.append("- run après run : " + " → ".join(
                f"{pt['n_fichiers']} run(s) : {pt['observe']}/{pt['attendu']:.0f}, z = {pt['z']:.1f}" if pt["attendu"] is not None
                else f"{pt['n_fichiers']} run(s) : fond non estimable" for pt in c["cumul"]))
        L.append(f"- verdict : {'; '.join(c['raisons'])}")
        L.append("")
    L += ["## À faire par le physicien", ""] + [f"- {x}" for x in run.a_verifier]
    L += ["", "## Reproductibilité", "", ", ".join(f"{k} {v}" for k, v in run.versions.items()), ""]
    return "\n".join(L)


def ecrire_these(run: RunDecouverte, dossier: str = DOSSIER_THESES) -> str:
    os.makedirs(dossier, exist_ok=True)
    base = os.path.join(dossier, "these_" + run.horodatage.replace(":", "").replace("-", "").replace("T", "_"))
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(rediger_these(run))
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(run.to_dict(), f, ensure_ascii=False, indent=1)
    return base + ".md"


def lister_fichiers(cibles: Sequence[str]) -> List[str]:
    chemins: List[str] = []
    for c in cibles:
        if os.path.isdir(c):
            chemins += sorted(os.path.join(c, f) for f in os.listdir(c)
                              if os.path.splitext(f.lower())[1] in (".csv", ".tsv", ".txt", ".dat", ".root"))
        elif os.path.isfile(c):
            chemins.append(c)
    return chemins


def analyser_hypothese(texte: str) -> Hypothese:
    """Forme localisée facultative : « M ~ 91 ± 3 », « M_paire vers 3.1 », « pic dans E autour de 42 »."""
    import re
    h = Hypothese(texte=texte.strip())
    m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:~|≈|=|vers|autour de|près de|à)\s*([0-9]+(?:[.,][0-9]+)?)(?:\s*(?:±|\+/-|plus ou moins)\s*([0-9]+(?:[.,][0-9]+)?))?", texte)
    if m:
        h.variable = m.group(1)
        h.valeur = float(m.group(2).replace(",", "."))
        h.demi_largeur = float(m.group(3).replace(",", ".")) if m.group(3) else None
    return h


def main(argv: Optional[Sequence[str]] = None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    ap = argparse.ArgumentParser(description="A.N.E.M.O.N.E — run de découverte : de l'hypothèse à la thèse.")
    ap.add_argument("cibles", nargs="+", help="fichiers ou dossiers de runs")
    ap.add_argument("--hypothese", default="", help="texte libre ; forme localisée reconnue : « M ~ 91 ± 3 »")
    ap.add_argument("--reference", default=None)
    ap.add_argument("--max-evenements", type=int, default=None)
    ap.add_argument("--sortie", default=DOSSIER_THESES)
    ap.add_argument("--sans-cumul", action="store_true", help="ne pas empiler la même masse sur tous les runs")
    args = ap.parse_args(argv)
    chemins = lister_fichiers(args.cibles)
    if not chemins:
        print("[RUN] aucun fichier .csv / .root trouvé.")
        return 2
    print(f"[RUN] {len(chemins)} fichier(s) ...")
    run = lancer_run(chemins, analyser_hypothese(args.hypothese), args.reference, args.max_evenements,
                     rappel=lambda m: print("  " + m), cumul=not args.sans_cumul)
    chemin = ecrire_these(run, args.sortie)
    print("[RUN] " + run.resume)
    for c in run.candidats[:12]:
        b = c["bosse"]
        print(f"  {c['verdict']:<7} {c['fichier']:<24} {b['variable']} ≈ {b['centre']:.4g}  p={b['p_global']:.2g}  {c['raisons'][0][:90]}")
    print(f"[RUN] Thèse : {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
