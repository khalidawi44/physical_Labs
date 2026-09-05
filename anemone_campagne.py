#!/usr/bin/env python3
"""Mode campagne — l'outil analyse seul, le physicien ne regarde que ce qui compte.

Pensé du point de vue du chercheur : il a un dossier de runs (un fichier .root
ou .csv par prise de données), parfois un run de référence (calibration, fond
connu). Il n'a pas le temps d'ouvrir chaque fichier. Ce module :

1. lit chaque run et y applique la détection non supervisée (Isolation Forest)
   avec les mêmes réglages ;
2. mène lui-même les expériences de robustesse que l'Architecte exige :
   - **balayage** du taux de contamination et de la graine : le même noyau
     d'événements reste-t-il isolé ?
   - **fond bootstrap** : on ré-échantillonne les seuls événements conformes
     et on relance la détection ; si les « anomalies » y sont aussi nettes,
     ce ne sont que les queues du fond, pas un signal ;
   - **comparaison à la référence** (si fournie) : dérive des distributions
     et excès d'isolement par rapport au run de référence ;
3. rend un **verdict** par run, calculé avec les seuils de l'Architecte, et
   classe les runs : solide → suspect (biais) → fragile → queues du fond →
   faible → insuffisant → erreur ;
4. écrit un rapport reproductible (Markdown + CSV + JSON avec empreintes des
   fichiers, paramètres et versions) et consigne la campagne dans le graphe de
   connaissances.

Utilisation en ligne de commande (sans interface, par exemple sur un serveur) :

    python anemone_campagne.py /data/runs --reference /data/calib.root
    python anemone_campagne.py /data/runs --veille 300     (ré-analyse toutes les 5 min)

Aucun chiffre n'est inventé : tout vient de `diagnostiquer()` et des seuils
de l'Architecte définis dans anemone_master.py.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

RACINE = os.path.dirname(os.path.abspath(__file__))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import anemone_master as am  # noqa: E402

EXTENSIONS = tuple(am.EXTENSIONS_ROOT) + tuple(am.EXTENSIONS_CSV)
VERDICTS = ("solide", "suspect_biais", "fragile", "queues_du_fond", "faible", "insuffisant", "erreur")
PRIORITE = {v: i for i, v in enumerate(VERDICTS)}
ETIQUETTES = {
    "solide": "🟢 solide",
    "suspect_biais": "🟠 suspect (biais)",
    "fragile": "🟡 fragile",
    "queues_du_fond": "⚪ queues du fond",
    "faible": "⚪ faible",
    "insuffisant": "⚫ insuffisant",
    "erreur": "🔴 erreur",
}
EXPLICATIONS = {
    "solide": "séparation significative et massive, stable au balayage, nettement au-dessus du fond bootstrap, sans biais apparent",
    "suspect_biais": "séparation nette mais corrélée à une autre variable (thermique ?) ou concentrée dans un épisode transitoire",
    "fragile": "séparation nette mais le noyau d'événements isolés change avec le taux de contamination ou la graine",
    "queues_du_fond": "le fond seul, ré-échantillonné, produit une séparation aussi nette : ce sont les queues de distribution, pas un signal",
    "faible": "aucune variable ne passe simultanément les seuils de significativité et de taille d'effet",
    "insuffisant": "trop peu d'événements isolés pour conclure",
    "erreur": "fichier illisible ou analyse impossible",
}

SEUIL_STABILITE = 0.5        # recouvrement moyen minimal du noyau isolé au balayage
SEUIL_DOMINANTE_STABLE = 0.75  # part des essais où la variable dominante est la même
SEUIL_EXCES_FOND = 1.5       # |d| observé / |d| maximal du fond bootstrap
SEUIL_TRANSITOIRE = 0.6      # fraction de la plage temporelle (même seuil que l'Architecte)
SEUIL_DERIVE_KS = 0.1        # statistique KS minimale pour parler de dérive vs référence
MIN_ANOMALIES = 5
N_BOOTSTRAP = 8


# =============================================================================
# 1. Résultat d'un run
# =============================================================================

@dataclass
class ResultatFichier:
    fichier: str
    chemin: str
    verdict: str = "erreur"
    motifs: List[str] = field(default_factory=list)
    sha256: str = ""
    format: str = ""
    n_evenements: int = 0
    n_anomalies: int = 0
    variables: List[str] = field(default_factory=list)
    dominante: Optional[str] = None
    d_cohen: float = float("nan")
    p_value: float = float("nan")
    stabilite: float = float("nan")
    dominante_stable: Optional[bool] = None
    exces_fond: float = float("nan")
    d_fond_max: float = float("nan")
    correlation_suspecte: Optional[str] = None
    fraction_fenetre_temporelle: Optional[float] = None
    derive_reference: Dict[str, Dict[str, float]] = field(default_factory=dict)
    exces_reference: float = float("nan")
    duree_s: float = 0.0
    erreur: Optional[str] = None

    @property
    def etiquette(self) -> str:
        return ETIQUETTES[self.verdict]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["etiquette"] = self.etiquette
        return d


# =============================================================================
# 2. Outils
# =============================================================================

def empreinte_sha256(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def lister_fichiers(dossier: str, recursif: bool = False) -> List[str]:
    """Fichiers .root / .csv / .tsv / .txt / .dat d'un dossier, triés (fichiers cachés ignorés)."""
    trouves: List[str] = []
    if recursif:
        for racine, sous, noms in os.walk(dossier):
            sous[:] = [s for s in sous if not s.startswith(".")]
            trouves += [os.path.join(racine, n) for n in noms if _admissible(n)]
    else:
        trouves = [os.path.join(dossier, n) for n in os.listdir(dossier)
                   if _admissible(n) and os.path.isfile(os.path.join(dossier, n))]
    return sorted(trouves)


def _admissible(nom: str) -> bool:
    return not nom.startswith(".") and nom.lower().endswith(EXTENSIONS)


def _recouvrement(a: Set[Any], b: Set[Any]) -> float:
    """|A ∩ B| / min(|A|, |B|) : robuste quand un lot est inclus dans l'autre."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _indices_isoles(resultat: pd.DataFrame) -> Set[Any]:
    return set(resultat.index[resultat["Inconnu"] == -1])


# =============================================================================
# 3. Les expériences que l'outil mène seul
# =============================================================================

def balayer_robustesse(matrice: pd.DataFrame, colonnes: Sequence[str], contamination: float, seed: int,
                       paires_connues: Optional[Set[frozenset]] = None) -> Dict[str, Any]:
    """Fait varier contamination (÷2, ×2) et graine (+1, +2) : le noyau isolé tient-il ?

    La variable dominante est jugée stable si, à chaque essai, elle est la même ou une
    variable structurellement liée à elle (corrélée chez les conformes, ou relation
    connue de l'outil) : E et pt qui se relaient ne sont pas une fragilité.
    """
    base = am.detecter_inconnu(matrice, colonnes, contamination=contamination, seed=seed)
    noyau = _indices_isoles(base)
    diag_base = am.diagnostiquer(base, colonnes)
    dom_base = am.variable_dominante(diag_base)
    corr_ok = diag_base.get("correlations_conformes", {})
    connues = paires_connues or set()

    def liee(dom: Optional[str]) -> bool:
        if dom == dom_base:
            return True
        if dom is None or dom_base is None:
            return False
        if frozenset((dom, dom_base)) in connues:
            return True
        r = corr_ok.get(f"{dom_base} ↔ {dom}", corr_ok.get(f"{dom} ↔ {dom_base}", 0.0))
        return abs(r) >= am.SEUIL_CORR_BIAIS

    taux = sorted({max(0.005, contamination / 2), contamination, min(0.2, contamination * 2)})
    recouvrements, memes_dominantes, essais, dominantes = [], 0, 0, []
    for c in taux:
        for s in (seed, seed + 1, seed + 2):
            if c == contamination and s == seed:
                continue
            res = am.detecter_inconnu(matrice, colonnes, contamination=c, seed=s)
            recouvrements.append(_recouvrement(noyau, _indices_isoles(res)))
            dom = am.variable_dominante(am.diagnostiquer(res, colonnes))
            dominantes.append(dom)
            memes_dominantes += int(liee(dom))
            essais += 1
    return {
        "stabilite": float(np.mean(recouvrements)) if recouvrements else float("nan"),
        "dominante_stable": (memes_dominantes / essais >= SEUIL_DOMINANTE_STABLE) if essais else None,
        "dominantes": dominantes,
        "essais": essais,
    }


def fond_bootstrap(resultat: pd.DataFrame, colonnes: Sequence[str], contamination: float, seed: int,
                   n_tirages: int = N_BOOTSTRAP) -> Dict[str, Any]:
    """Ré-échantillonne les seuls événements conformes et relance la détection.

    Donne la séparation (|d| maximal) que produisent les queues du fond à elles
    seules : un signal réel doit faire nettement mieux.
    """
    conformes = resultat[resultat["Inconnu"] == 1][list(colonnes)]
    if len(conformes) < 20:
        return {"d_fond_max": float("nan"), "d_fond_moyen": float("nan"), "tirages": 0}
    rng = np.random.default_rng(seed)
    n = len(resultat)
    valeurs = []
    for _ in range(n_tirages):
        tirage = conformes.iloc[rng.integers(0, len(conformes), n)].reset_index(drop=True)
        res = am.detecter_inconnu(tirage, colonnes, contamination=contamination, seed=seed)
        diag = am.diagnostiquer(res, colonnes)
        if diag.get("insuffisant"):
            continue
        d = max(abs(v["d_cohen"]) for v in diag["variables"].values())
        if np.isfinite(d):
            valeurs.append(d)
    if not valeurs:
        return {"d_fond_max": float("nan"), "d_fond_moyen": float("nan"), "tirages": 0}
    return {"d_fond_max": float(max(valeurs)), "d_fond_moyen": float(np.mean(valeurs)), "tirages": len(valeurs)}


def comparer_reference(matrice: pd.DataFrame, reference: pd.DataFrame, colonnes: Sequence[str]) -> Dict[str, Dict[str, float]]:
    """Dérive des distributions du run par rapport à la référence (KS variable par variable)."""
    derive: Dict[str, Dict[str, float]] = {}
    for c in colonnes:
        if c not in reference.columns:
            continue
        ks = sp_stats.ks_2samp(matrice[c].to_numpy(float), reference[c].to_numpy(float))
        derive[c] = {"ks_stat": float(ks.statistic), "p_value": float(ks.pvalue),
                     "derive": bool(ks.pvalue < am.Architecte.SEUIL_P_VERROU and ks.statistic >= SEUIL_DERIVE_KS)}
    return derive


def _d_dominante_reference(reference: pd.DataFrame, colonnes: Sequence[str], contamination: float, seed: int) -> Dict[str, float]:
    """|d| par variable quand on applique la même détection à la référence."""
    cols = [c for c in colonnes if c in reference.columns]
    if len(cols) == 0:
        return {}
    res = am.detecter_inconnu(reference, cols, contamination=contamination, seed=seed)
    diag = am.diagnostiquer(res, cols)
    if diag.get("insuffisant"):
        return {}
    return {c: abs(v["d_cohen"]) for c, v in diag["variables"].items()}


# =============================================================================
# 4. Verdict (mêmes seuils que l'Architecte)
# =============================================================================

def qualifier(diag: Dict[str, Any], robustesse: Optional[Dict[str, Any]], fond: Optional[Dict[str, Any]],
              paires_connues: Optional[Set[frozenset]] = None) -> Dict[str, Any]:
    """Applique les critères de l'Architecte et des expériences de robustesse. Renvoie verdict + motifs + chiffres."""
    A = am.Architecte
    sortie: Dict[str, Any] = {"verdict": "faible", "motifs": [], "dominante": None, "d_cohen": float("nan"),
                              "p_value": float("nan"), "correlation_suspecte": None,
                              "fraction_fenetre_temporelle": None, "exces_fond": float("nan")}
    if diag.get("insuffisant") or diag.get("n_anomalies", 0) < MIN_ANOMALIES:
        sortie["verdict"] = "insuffisant"
        sortie["motifs"].append(f"{diag.get('n_anomalies', 0)} événements isolés seulement (minimum {MIN_ANOMALIES})")
        return sortie

    dom = am.variable_dominante(diag)
    v = diag["variables"][dom]
    sortie.update({"dominante": dom, "d_cohen": float(v["d_cohen"]), "p_value": float(v["p_value"])})
    passe = v["p_value"] < A.SEUIL_P_VERROU and abs(v["d_cohen"]) >= A.SEUIL_D_VERROU
    if not passe:
        sortie["motifs"].append(
            f"meilleure variable {dom} : d = {v['d_cohen']:.2f}, p = {v['p_value']:.3g} ; "
            f"seuils non atteints (p < {A.SEUIL_P_VERROU} et |d| ≥ {A.SEUIL_D_VERROU})")
        return sortie
    sortie["motifs"].append(f"{dom} sépare isolés et conformes : d = {v['d_cohen']:.2f}, p = {v['p_value']:.3g}")

    # 1) biais instrumental : corrélation interne aux anomalies impliquant la dominante
    fortes = am.correlations_fortes(diag, dom, A.SEUIL_CORR_BIAIS, A.SEUIL_EXCES_CORR, paires_connues)
    suspectes = [c for c in fortes if c["nature"] == "suspecte"]
    structurelles = [c for c in fortes if c["nature"] == "structurelle"]
    connues = [c for c in fortes if c["nature"] == "connue"]
    biais = False
    if connues:
        c = connues[0]
        sortie["motifs"].append(f"{dom} ↔ {c['autre']} (r = {c['r_isoles']:.2f}) : relation connue de l'outil, pas un biais")
    if suspectes:
        c = suspectes[0]
        sortie["correlation_suspecte"] = f"{dom} ↔ {c['autre']} (r = {c['r_isoles']:.2f} isolés, {c['r_conformes']:.2f} conformes)"
        sortie["motifs"].append(
            f"chez les isolés seulement, {dom} est corrélée à {c['autre']} (r = {c['r_isoles']:.2f} contre "
            f"{c['r_conformes']:.2f} chez les conformes)"
            + (" : effet thermique instrumental possible" if c["thermique"] else " : effet d'appareillage non exclu"))
        biais = True
    elif structurelles:
        c = structurelles[0]
        sortie["motifs"].append(
            f"{dom} ↔ {c['autre']} corrélées chez les isolés (r = {c['r_isoles']:.2f}) comme chez les conformes "
            f"(r = {c['r_conformes']:.2f}) : propriété des données, pas un biais")
    # 2) épisode transitoire
    frac = diag.get("geometrie", {}).get("fraction_fenetre_temporelle")
    sortie["fraction_fenetre_temporelle"] = frac
    if frac is not None and frac < SEUIL_TRANSITOIRE:
        sortie["motifs"].append(f"les isolés n'occupent que {100 * frac:.0f} % de la plage temporelle : épisode transitoire ?")
        biais = True
    if biais:
        sortie["verdict"] = "suspect_biais"
        return sortie

    # 3) queues du fond : le fond ré-échantillonné fait-il aussi bien ?
    if fond and np.isfinite(fond.get("d_fond_max", float("nan"))) and fond["d_fond_max"] > 0:
        exces = abs(v["d_cohen"]) / fond["d_fond_max"] if np.isfinite(v["d_cohen"]) else float("inf")
        sortie["exces_fond"] = float(exces)
        if exces < SEUIL_EXCES_FOND:
            sortie["verdict"] = "queues_du_fond"
            sortie["motifs"].append(
                f"le fond seul (bootstrap, {fond['tirages']} tirages) atteint |d| = {fond['d_fond_max']:.2f} ; "
                f"observé {abs(v['d_cohen']):.2f}, excès ×{exces:.2f} < ×{SEUIL_EXCES_FOND}")
            return sortie
        sortie["motifs"].append(f"excès ×{exces:.2f} sur le fond bootstrap (|d| fond max = {fond['d_fond_max']:.2f})")

    # 4) robustesse au balayage
    if robustesse and robustesse.get("essais"):
        stab, dom_stable = robustesse["stabilite"], robustesse["dominante_stable"]
        if stab < SEUIL_STABILITE or not dom_stable:
            sortie["verdict"] = "fragile"
            sortie["motifs"].append(
                f"balayage contamination/graine : recouvrement du noyau {100 * stab:.0f} %"
                + ("" if dom_stable else ", variable dominante changeante"))
            return sortie
        sortie["motifs"].append(f"noyau isolé stable au balayage (recouvrement {100 * stab:.0f} %, dominante constante)")

    sortie["verdict"] = "solide"
    return sortie


# =============================================================================
# 5. Analyse d'un run, puis d'une campagne
# =============================================================================

def charger_reference(chemin: str, max_evenements: Optional[int] = None) -> pd.DataFrame:
    matrice, _ = am.analyser_fichier_physique(chemin, os.path.basename(chemin), None, max_evenements)
    return matrice


def analyser_un_fichier(
    chemin: str,
    colonnes: Optional[Sequence[str]] = None,
    contamination: float = 0.03,
    seed: int = 42,
    balayage: bool = True,
    reference: Optional[pd.DataFrame] = None,
    max_evenements: Optional[int] = None,
    paires_connues: Optional[Set[frozenset]] = None,
) -> ResultatFichier:
    debut = time.time()
    r = ResultatFichier(fichier=os.path.basename(chemin), chemin=os.path.abspath(chemin))
    try:
        r.sha256 = empreinte_sha256(chemin)
        matrice, rapport = am.analyser_fichier_physique(chemin, r.fichier, None, max_evenements)
        r.format = rapport.get("format", "")
        r.n_evenements = int(len(matrice))
        cols = [c for c in (colonnes or am.colonnes_analysables(list(matrice.columns))[:8]) if c in matrice.columns]
        if not cols:
            raise ValueError("aucune des variables demandées n'existe dans ce fichier")
        r.variables = cols
        resultat = am.detecter_inconnu(matrice, cols, contamination=contamination, seed=seed)
        diag = am.diagnostiquer(resultat, cols)
        r.n_anomalies = int(diag["n_anomalies"])
        robustesse = balayer_robustesse(matrice, cols, contamination, seed, paires_connues) if balayage and not diag.get("insuffisant") else None
        fond = fond_bootstrap(resultat, cols, contamination, seed) if not diag.get("insuffisant") else None
        q = qualifier(diag, robustesse, fond, paires_connues)
        r.verdict, r.motifs = q["verdict"], q["motifs"]
        r.dominante, r.d_cohen, r.p_value = q["dominante"], q["d_cohen"], q["p_value"]
        r.correlation_suspecte, r.fraction_fenetre_temporelle, r.exces_fond = (
            q["correlation_suspecte"], q["fraction_fenetre_temporelle"], q["exces_fond"])
        if fond:
            r.d_fond_max = fond["d_fond_max"]
        if robustesse:
            r.stabilite, r.dominante_stable = robustesse["stabilite"], robustesse["dominante_stable"]
        if reference is not None:
            r.derive_reference = comparer_reference(matrice, reference, cols)
            derives = [c for c, x in r.derive_reference.items() if x["derive"]]
            if derives:
                r.motifs.append("dérive de tout le run par rapport à la référence sur : " + ", ".join(derives))
            d_ref = _d_dominante_reference(reference, cols, contamination, seed)
            if r.dominante and r.dominante in d_ref and d_ref[r.dominante] > 0 and np.isfinite(r.d_cohen):
                r.exces_reference = abs(r.d_cohen) / d_ref[r.dominante]
                r.motifs.append(f"excès ×{r.exces_reference:.2f} par rapport à la même détection sur la référence")
    except Exception as exc:  # fichier illisible, colonnes absentes, etc. : la campagne continue
        r.verdict, r.erreur = "erreur", f"{type(exc).__name__}: {exc}"
        r.motifs = [r.erreur]
    r.duree_s = round(time.time() - debut, 2)
    return r


def trier(resultats: Iterable[ResultatFichier]) -> List[ResultatFichier]:
    def cle(x: ResultatFichier):
        d = abs(x.d_cohen) if np.isfinite(x.d_cohen) else -1.0
        return (PRIORITE[x.verdict], -d, x.fichier)
    return sorted(resultats, key=cle)


def analyser_campagne(
    chemins: Sequence[str],
    colonnes: Optional[Sequence[str]] = None,
    contamination: float = 0.03,
    seed: int = 42,
    balayage: bool = True,
    reference: Optional[pd.DataFrame] = None,
    max_evenements: Optional[int] = None,
    rappel: Optional[Callable[[int, int, ResultatFichier], None]] = None,
    paires_connues: Optional[Set[frozenset]] = None,
) -> List[ResultatFichier]:
    """Analyse chaque fichier ; `rappel(i, n, resultat)` est appelé après chacun (barre de progression)."""
    resultats: List[ResultatFichier] = []
    for i, chemin in enumerate(chemins, start=1):
        r = analyser_un_fichier(chemin, colonnes, contamination, seed, balayage, reference, max_evenements, paires_connues)
        resultats.append(r)
        if rappel:
            rappel(i, len(chemins), r)
    return trier(resultats)


# =============================================================================
# 6. Rapport reproductible et graphe
# =============================================================================

def provenance(parametres: Dict[str, Any]) -> Dict[str, Any]:
    from importlib.metadata import version as _v

    def v(p: str) -> str:
        try:
            return _v(p)
        except Exception:
            return "?"

    return {
        "outil": f"A.N.E.M.O.N.E {am.VERSION_OUTIL}",
        "horodatage_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "systeme": platform.platform(),
        "paquets": {p: v(p) for p in ("numpy", "pandas", "scikit-learn", "scipy", "uproot")},
        "parametres": parametres,
        "seuils": {
            "p_verrou": am.Architecte.SEUIL_P_VERROU, "d_verrou": am.Architecte.SEUIL_D_VERROU,
            "corr_biais": am.Architecte.SEUIL_CORR_BIAIS, "stabilite": SEUIL_STABILITE,
            "exces_fond": SEUIL_EXCES_FOND, "transitoire": SEUIL_TRANSITOIRE, "min_anomalies": MIN_ANOMALIES,
        },
    }


def rediger_markdown(resultats: Sequence[ResultatFichier], prov: Dict[str, Any]) -> str:
    comptes = {v: sum(1 for r in resultats if r.verdict == v) for v in VERDICTS}
    L: List[str] = []
    L.append(f"# Campagne A.N.E.M.O.N.E — {prov['horodatage_utc']}")
    L.append("")
    L.append(f"{len(resultats)} runs analysés · " + " · ".join(f"{ETIQUETTES[v]} : {n}" for v, n in comptes.items() if n))
    L.append("")
    a_voir = [r for r in resultats if r.verdict in ("solide", "suspect_biais")]
    L.append("## À regarder en premier")
    L.append("")
    if a_voir:
        for r in a_voir:
            L.append(f"- **{r.fichier}** — {r.etiquette} — {r.dominante} (d = {r.d_cohen:.2f}, p = {r.p_value:.3g}) — {r.motifs[-1] if r.motifs else ''}")
    else:
        L.append("Aucun run ne présente de séparation solide ni de biais suspect : rien n'exige une décision aujourd'hui.")
    L.append("")
    L.append("## Tous les runs, par priorité")
    L.append("")
    L.append("| # | Run | Verdict | Événements | Isolés | Dominante | d | p | Stabilité | Excès fond | Durée |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(resultats, start=1):
        L.append(
            f"| {i} | {r.fichier} | {r.etiquette} | {r.n_evenements} | {r.n_anomalies} | {r.dominante or '—'} | "
            f"{_f(r.d_cohen)} | {_f(r.p_value, 'g')} | {_pct(r.stabilite)} | {_f(r.exces_fond)} | {r.duree_s} s |")
    L.append("")
    L.append("## Détail et raisonnement (chiffres calculés, seuils de l'Architecte)")
    L.append("")
    for r in resultats:
        L.append(f"### {r.fichier} — {r.etiquette}")
        L.append("")
        L.append(f"*{EXPLICATIONS[r.verdict]}.*")
        L.append("")
        for m in r.motifs:
            L.append(f"- {m}")
        if r.derive_reference:
            derives = [f"{c} (KS = {x['ks_stat']:.2f}, p = {x['p_value']:.2g})" for c, x in r.derive_reference.items() if x["derive"]]
            L.append("- dérive vs référence : " + (", ".join(derives) if derives else "aucune"))
        L.append(f"- variables : {', '.join(r.variables) if r.variables else '—'} · empreinte SHA-256 : `{r.sha256[:16]}…`" if r.sha256 else "")
        L.append("")
    L.append("## Verdicts : définitions")
    L.append("")
    for v in VERDICTS:
        L.append(f"- **{ETIQUETTES[v]}** : {EXPLICATIONS[v]}.")
    L.append("")
    L.append("## Provenance")
    L.append("")
    L.append("```json")
    L.append(json.dumps(prov, ensure_ascii=False, indent=2))
    L.append("```")
    return "\n".join(L) + "\n"


def _f(x: float, mode: str = "f") -> str:
    if x is None or not np.isfinite(x):
        return "—"
    return f"{x:.3g}" if mode == "g" else f"{x:.2f}"


def _pct(x: float) -> str:
    return "—" if x is None or not np.isfinite(x) else f"{100 * x:.0f} %"


def ecrire_rapport(resultats: Sequence[ResultatFichier], dossier_sortie: str, parametres: Dict[str, Any]) -> str:
    """Écrit rapport.md, resultats.csv et resultats.json dans un sous-dossier horodaté. Renvoie ce dossier."""
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dossier = os.path.join(dossier_sortie, f"campagne_{horodatage}")
    os.makedirs(dossier, exist_ok=True)
    prov = provenance(parametres)
    with open(os.path.join(dossier, "rapport.md"), "w", encoding="utf-8") as f:
        f.write(rediger_markdown(resultats, prov))
    with open(os.path.join(dossier, "resultats.json"), "w", encoding="utf-8") as f:
        json.dump({"provenance": prov, "resultats": [r.to_dict() for r in resultats]}, f, ensure_ascii=False, indent=2, default=str)
    champs = ["rang", "fichier", "verdict", "n_evenements", "n_anomalies", "dominante", "d_cohen", "p_value",
              "stabilite", "exces_fond", "exces_reference", "correlation_suspecte", "sha256", "duree_s", "erreur"]
    with open(os.path.join(dossier, "resultats.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        for i, r in enumerate(resultats, start=1):
            d = r.to_dict()
            w.writerow({"rang": i, **{k: d.get(k, "") for k in champs if k != "rang"}})
    return dossier


def consigner_dans_graphe(g: "am.GrapheConnaissances", resultats: Sequence[ResultatFichier],
                          parametres: Dict[str, Any], dossier_rapport: Optional[str]) -> str:
    """Un nœud « campagne » relié à un nœud « verdict » par run. Renvoie l'identifiant de la campagne."""
    comptes = {v: sum(1 for r in resultats if r.verdict == v) for v in VERDICTS}
    texte = f"Campagne : {len(resultats)} runs — " + ", ".join(f"{n} {v}" for v, n in comptes.items() if n)
    ident = g.ajouter_noeud("campagne", texte, {"parametres": parametres, "rapport": dossier_rapport, "comptes": comptes})
    for r in resultats:
        v = g.ajouter_noeud("verdict", f"{r.fichier} : {r.etiquette}", {k: val for k, val in r.to_dict().items() if k != "derive_reference"})
        g.ajouter_arete(v, ident, "issu_de")
    return ident


# =============================================================================
# 7. Ligne de commande
# =============================================================================

def _console_robuste() -> None:
    """Console Windows en cp1252/cp850 : ne jamais planter sur un accent ou une pastille."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    _console_robuste()
    p = argparse.ArgumentParser(description="A.N.E.M.O.N.E — campagne automatique sur un dossier de runs.")
    p.add_argument("dossier", help="dossier contenant les fichiers .root / .csv (ou un seul fichier)")
    p.add_argument("--reference", help="run de référence (calibration, fond connu)")
    p.add_argument("--variables", help="colonnes à analyser, séparées par des virgules (défaut : les 8 premières)")
    p.add_argument("--contamination", type=float, default=0.03)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-evenements", type=int, default=None)
    p.add_argument("--sans-balayage", action="store_true", help="ne pas faire varier contamination et graine")
    p.add_argument("--recursif", action="store_true")
    p.add_argument("--sortie", default="rapports", help="dossier des rapports (défaut : rapports/)")
    p.add_argument("--graphe", default="anemone_graphe.json", help="graphe de connaissances à enrichir ('' pour aucun)")
    p.add_argument("--veille", type=int, default=0, metavar="SECONDES",
                   help="rester actif et analyser les nouveaux fichiers toutes les N secondes (Ctrl+C pour arrêter)")
    a = p.parse_args(argv)

    colonnes = [c.strip() for c in a.variables.split(",")] if a.variables else None
    reference = charger_reference(a.reference, a.max_evenements) if a.reference else None
    try:
        from anemone_physicien import Connaissances
        connues = Connaissances.charger().paires_connues()
    except Exception:  # pragma: no cover
        connues = set()
    parametres = {"dossier": os.path.abspath(a.dossier), "reference": a.reference, "variables": colonnes,
                  "contamination": a.contamination, "seed": a.seed, "max_evenements": a.max_evenements,
                  "balayage": not a.sans_balayage}
    vus: Set[str] = set()
    tous: List[ResultatFichier] = []

    def un_tour() -> int:
        chemins = [a.dossier] if os.path.isfile(a.dossier) else lister_fichiers(a.dossier, a.recursif)
        nouveaux = [c for c in chemins if c not in vus]
        if not nouveaux:
            return 0
        print(f"[CAMPAGNE] {len(nouveaux)} fichier(s) à analyser ...")

        def rappel(i: int, n: int, r: ResultatFichier) -> None:
            print(f"  [{i}/{n}] {r.fichier:<40} {r.etiquette:<22} {r.motifs[-1] if r.motifs else ''}")

        resultats = analyser_campagne(nouveaux, colonnes, a.contamination, a.seed, not a.sans_balayage, reference,
                                      a.max_evenements, rappel, connues)
        vus.update(nouveaux)
        tous.extend(resultats)
        tous.sort(key=lambda r: (PRIORITE[r.verdict], -(abs(r.d_cohen) if np.isfinite(r.d_cohen) else -1)))
        dossier = ecrire_rapport(tous, a.sortie, parametres)
        print(f"[CAMPAGNE] Rapport : {os.path.join(dossier, 'rapport.md')}")
        if a.graphe:
            g = am.GrapheConnaissances.charger(a.graphe) if os.path.exists(a.graphe) else am.GrapheConnaissances()
            consigner_dans_graphe(g, resultats, parametres, dossier)
            g.sauvegarder(a.graphe)
        return len(nouveaux)

    un_tour()
    if a.veille > 0:
        print(f"[VEILLE] Surveillance de {a.dossier} toutes les {a.veille} s (Ctrl+C pour arrêter).")
        try:
            while True:
                time.sleep(a.veille)
                if un_tour() == 0:
                    print(f"[VEILLE] {datetime.now().strftime('%H:%M:%S')} rien de nouveau.")
        except KeyboardInterrupt:
            print("\n[VEILLE] Arrêt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
