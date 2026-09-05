#!/usr/bin/env python3
"""Albert — physicien robot : il cherche en autonomie, apprend, et enseigne à l'outil.

Albert (clin d'œil à Einstein) joue le rôle du chercheur. Rien n'est inventé :
il n'a aucune physique en dur. Il apprend :

1. **depuis les données** : les relations entre variables qu'on peut démontrer
   par le calcul,
   - relations *fonctionnelles* : une variable (ou son carré) est déterminée
     par les autres (ou leurs carrés) avec un R² ≥ 0,995 sur les événements
     conformes, par exemple E² = px² + py² + pz² (+ m²) ou pt² = px² + py² ;
   - variables *apparentées* : corrélation |r| ≥ 0,9 sur tous les événements ;
2. **depuis le physicien** : quand l'Architecte soulève une corrélation que
   personne ne peut expliquer par le calcul, le robot la consigne comme
   *question ouverte* ; le physicien répond une fois (« relation connue » ou
   « vrai biais ») et l'outil s'en souvient pour toujours ;
3. **par le débat** : il soumet lui-même le lot isolé à l'Architecte, réfute
   avec preuve calculée ce qu'il peut réfuter, et laisse le reste au
   physicien. Chaque leçon est consignée dans le graphe de connaissances.

4. **en cherchant seul** (`Albert.chercher`) : sur un dossier de runs, il
   essaie plusieurs stratégies d'analyse (grandeurs par défaut, grandeurs
   primitives sans les variables déduites, toutes les grandeurs), lance les
   campagnes, et ne retient comme *trouvaille* qu'un run « solide » sous au
   moins deux stratégies ; un « solide » sous une seule est une *piste*. Il
   tient un cahier de laboratoire (Markdown + JSON) avec ce qu'il a tenté,
   trouvé, appris, et les questions qu'il pose au physicien.

Ce qu'il a appris est enseigné à l'outil : l'Architecte et la campagne ne
lèvent plus d'objection sur une paire de variables connue.

Base de connaissances : `anemone_connaissances.json` dans le dossier de l'outil
(conservée par les mises à jour, exportable).

    python anemone_physicien.py --chercher /data/runs --reference /data/calib.root
    python anemone_physicien.py run.root                   (une leçon sur un fichier)
    python anemone_physicien.py --etat                     (ce que l'outil sait)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import numpy as np
import pandas as pd

RACINE = os.path.dirname(os.path.abspath(__file__))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import anemone_master as am  # noqa: E402

FICHIER_CONNAISSANCES = os.path.join(RACINE, "anemone_connaissances.json")
SEUIL_R2 = 0.995                # une relation fonctionnelle explique ≥ 99,5 % de la variance : des identités, pas des approximations
SEUIL_APPARENTEES = 0.9         # |r| sur tous les événements
MIN_VALEURS_DISTINCTES = 10     # en dessous : variable discrète (charge, indicateur), pas de relation cherchée
MAX_LIGNES = 20000              # sous-échantillon pour les ajustements
DOSSIER_CAHIER = "cahier_albert"


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# =============================================================================
# 1. Base de connaissances persistante
# =============================================================================

class Connaissances:
    """Ce que l'outil sait : relations entre variables, questions ouvertes, retours du physicien, leçons."""

    VERSION = 1

    def __init__(self, donnees: Optional[Dict[str, Any]] = None):
        d = donnees or {}
        self.relations: List[Dict[str, Any]] = list(d.get("relations", []))
        self.questions: List[Dict[str, Any]] = list(d.get("questions", []))
        self.retours: List[Dict[str, Any]] = list(d.get("retours", []))
        self.lecons: List[Dict[str, Any]] = list(d.get("lecons", []))

    # -- persistance --------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"version": self.VERSION, "relations": self.relations, "questions": self.questions,
                "retours": self.retours, "lecons": self.lecons}

    def sauvegarder(self, chemin: Optional[str] = None) -> None:
        chemin = chemin or FICHIER_CONNAISSANCES  # résolu à l'appel : le chemin par défaut peut être redirigé
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def charger(cls, chemin: Optional[str] = None) -> "Connaissances":
        chemin = chemin or FICHIER_CONNAISSANCES
        if not os.path.isfile(chemin):
            return cls()
        with open(chemin, encoding="utf-8") as f:
            return cls(json.load(f))

    # -- relations ----------------------------------------------------------
    def paires_connues(self, sans_albert: bool = False) -> Set[frozenset]:
        """Toutes les paires de variables couvertes par une relation connue (fonctionnelle, apparentée, déclarée).

        `sans_albert=True` (mode « Fred seul ») : seules les relations déclarées par
        une personne comptent, pas celles qu'Albert a apprises des données.
        """
        paires: Set[frozenset] = set()
        for r in self.relations:
            if sans_albert and r.get("origine") == Albert.NOM:
                continue
            v = r["variables"]
            for i in range(len(v)):
                for j in range(i + 1, len(v)):
                    paires.add(frozenset((v[i], v[j])))
        return paires

    def ajouter_relation(self, variables: Sequence[str], nature: str, preuve: str, origine: str,
                         fichier: Optional[str] = None, cible: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Enregistre une relation ; None si le même ensemble de variables est déjà connu."""
        cle = sorted(set(variables))
        if len(cle) < 2:
            return None
        for r in self.relations:
            if sorted(r["variables"]) == cle:
                return None
        rel = {"id": f"rel-{uuid.uuid4().hex[:8]}", "variables": cle, "nature": nature, "preuve": preuve,
               "origine": origine, "fichier": fichier, "cible": cible, "date": _maintenant()}
        self.relations.append(rel)
        # une question ouverte sur une de ces paires est close par la relation
        for q in self.questions:
            if q["statut"] == "ouverte" and set(q["variables"]) <= set(cle):
                q.update({"statut": "close", "reponse": "relation_connue", "date_reponse": _maintenant(), "par": origine})
        return rel

    def variables_deduites(self) -> Set[str]:
        """Variables qu'une relation fonctionnelle apprise explique par les autres (E, pt…)."""
        return {r["cible"] for r in self.relations if r.get("nature") == "fonctionnelle" and r.get("cible")}

    def oublier_relation(self, identifiant: str) -> bool:
        avant = len(self.relations)
        self.relations = [r for r in self.relations if r["id"] != identifiant]
        return len(self.relations) < avant

    # -- questions au physicien --------------------------------------------
    def ajouter_question(self, variables: Sequence[str], contexte: str, fichier: Optional[str] = None) -> Dict[str, Any]:
        cle = sorted(set(variables))
        for q in self.questions:
            if sorted(q["variables"]) == cle and q["statut"] == "ouverte":
                return q
        q = {"id": f"q-{uuid.uuid4().hex[:8]}", "variables": cle, "contexte": contexte, "fichier": fichier,
             "date": _maintenant(), "statut": "ouverte", "reponse": None}
        self.questions.append(q)
        return q

    def questions_ouvertes(self) -> List[Dict[str, Any]]:
        return [q for q in self.questions if q["statut"] == "ouverte"]

    def repondre(self, identifiant: str, reponse: str, auteur: str) -> Optional[Dict[str, Any]]:
        """`reponse` : "relation_connue" (l'outil apprend la relation) ou "biais" (l'outil retient la vigilance)."""
        q = next((q for q in self.questions if q["id"] == identifiant), None)
        if q is None:
            return None
        q.update({"statut": "close", "reponse": reponse, "date_reponse": _maintenant(), "par": auteur})
        if reponse == "relation_connue":
            self.ajouter_relation(q["variables"], "declaree", f"déclarée par {auteur}", auteur, q.get("fichier"))
        return q

    # -- retours et leçons --------------------------------------------------
    def ajouter_retour(self, fichier: str, verdict: str, avis: str, auteur: str, commentaire: str = "") -> Dict[str, Any]:
        r = {"fichier": fichier, "verdict": verdict, "avis": avis, "auteur": auteur, "commentaire": commentaire, "date": _maintenant()}
        self.retours.append(r)
        return r

    def resume(self) -> Dict[str, int]:
        return {"relations": len(self.relations), "questions_ouvertes": len(self.questions_ouvertes()),
                "retours": len(self.retours), "lecons": len(self.lecons)}


# =============================================================================
# 2. Apprentissage depuis les données
# =============================================================================

def _r2(y: np.ndarray, F: np.ndarray) -> tuple:
    F1 = np.column_stack([np.ones(len(F)), F])
    coef, *_ = np.linalg.lstsq(F1, y, rcond=None)
    residu = y - F1 @ coef
    var = float(y.var())
    return (1.0 - float(residu.var()) / var) if var > 1e-12 else 0.0, coef[1:]


def _minimiser(y: np.ndarray, F: np.ndarray, noms: List[str], seuil: float, tolerance: float = 1e-6) -> List[str]:
    """Retire une à une les variables les moins utiles tant que le R² reste ≥ seuil ET ne baisse
    pas de plus de `tolerance` par rapport à l'ajustement complet : on garde l'identité entière
    (E² = px² + py² + pz²), pas seulement son terme dominant."""
    actifs = list(range(F.shape[1]))
    r2_complet, _ = _r2(y, F)
    # Une identité exacte (R² ≈ 1) ne tolère aucune perte ; une relation approchée
    # tolère au plus la part de variance qu'on a déjà accepté de ne pas expliquer.
    tolerance = max(tolerance, 1.0 - r2_complet)
    seuil = max(seuil, r2_complet - tolerance)
    while len(actifs) > 1:
        meilleur, meilleur_r2 = None, -1.0
        for k in actifs:
            essai = [j for j in actifs if j != k]
            r2, _ = _r2(y, F[:, essai])
            if r2 > meilleur_r2:
                meilleur, meilleur_r2 = k, r2
        if meilleur_r2 >= seuil:
            actifs.remove(meilleur)
        else:
            break
    return [noms[j] for j in actifs]


def relations_fonctionnelles(matrice: pd.DataFrame, colonnes: Optional[Sequence[str]] = None,
                             seuil: float = SEUIL_R2, max_lignes: int = MAX_LIGNES) -> List[Dict[str, Any]]:
    """Variables déterminées par les autres : A ou A² ≈ combinaison linéaire des autres et de leurs carrés.

    Générique et sans physique en dur : E² = px² + py² + pz² + m² ou pt² = px² + py²
    en sont des cas particuliers. Renvoie une relation par ensemble de variables.
    """
    # Ordre du fichier (et non l'ordre « masses d'abord » de la détection) : la recherche gloutonne d'identités
    # part de la première colonne, et l'ordre naturel E, px, py, pz, pt… mène aux formes les plus simples.
    cols = [c for c in (colonnes or am.colonnes_physiques(list(matrice.columns))) if c in matrice.columns]
    X = matrice[cols].to_numpy(float)
    if len(X) > max_lignes:
        X = X[np.random.default_rng(0).choice(len(X), max_lignes, replace=False)]
    if len(X) < 50 or len(cols) < 2:
        return []
    distinctes = {c: int(pd.Series(X[:, i]).nunique()) for i, c in enumerate(cols)}
    # Mise à l'échelle SANS centrage : centrer casserait les identités exactes entre
    # carrés (pt² = px² + py², E² = px² + py² + pz² + m²) en y injectant des termes linéaires.
    echelle = np.abs(X).max(axis=0)
    echelle[echelle == 0] = 1.0
    Z = X / echelle
    trouvees: Dict[frozenset, Dict[str, Any]] = {}
    for i, cible in enumerate(cols):
        if distinctes[cible] < MIN_VALEURS_DISTINCTES:
            continue
        autres = [j for j in range(len(cols)) if j != i and distinctes[cols[j]] >= MIN_VALEURS_DISTINCTES]
        if not autres:
            continue
        noms = [cols[j] for j in autres] + [f"{cols[j]}²" for j in autres]
        F = np.column_stack([Z[:, autres], Z[:, autres] ** 2])
        for forme, y in (("A", Z[:, i]), ("A²", Z[:, i] ** 2)):
            if float(y.var()) < 1e-6:
                continue
            r2, _ = _r2(y, F)
            if r2 < seuil:
                continue
            explicatives = _minimiser(y, F, noms, seuil)
            variables = sorted({cible} | {n.rstrip("²") for n in explicatives})
            cle = frozenset(variables)
            preuve = f"{cible}{'²' if forme == 'A²' else ''} ≈ f({', '.join(explicatives)}), R² = {r2:.4f} sur {len(X)} événements"
            # Dans une identité A² = ΣB², la grandeur composée A a le plus grand second moment
            # (E² ≥ pz², pt² ≥ px²) : c'est elle qu'on appelle « déduite » des autres.
            composee = max(variables, key=lambda v: float(np.mean(X[:, cols.index(v)] ** 2)))
            if cle not in trouvees or r2 > trouvees[cle]["r2"]:
                trouvees[cle] = {"variables": variables, "nature": "fonctionnelle", "preuve": preuve, "r2": float(r2),
                                 "cible": composee, "forme": forme, "explicatives": explicatives}
            break
    return sorted(trouvees.values(), key=lambda r: (-r["r2"], r["cible"]))


def variables_apparentees(matrice: pd.DataFrame, colonnes: Optional[Sequence[str]] = None,
                          seuil: float = SEUIL_APPARENTEES) -> List[Dict[str, Any]]:
    """Paires fortement corrélées sur TOUS les événements (|r| ≥ 0,9)."""
    # Ordre du fichier (et non l'ordre « masses d'abord » de la détection) : la recherche gloutonne d'identités
    # part de la première colonne, et l'ordre naturel E, px, py, pz, pt… mène aux formes les plus simples.
    cols = [c for c in (colonnes or am.colonnes_physiques(list(matrice.columns))) if c in matrice.columns]
    if len(cols) < 2:
        return []
    corr = matrice[cols].corr().fillna(0.0)
    paires = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = float(corr.loc[a, b])
            if abs(r) >= seuil:
                paires.append({"variables": sorted((a, b)), "nature": "apparentees", "r": r,
                               "preuve": f"corrélation r = {r:.3f} sur {len(matrice)} événements"})
    return sorted(paires, key=lambda p: -abs(p["r"]))


def apprendre_relations(matrice: pd.DataFrame, connaissances: Connaissances, colonnes: Optional[Sequence[str]] = None,
                        fichier: Optional[str] = None, origine: str = "physicien robot") -> List[Dict[str, Any]]:
    """Découvre les relations dans `matrice` et les enseigne à l'outil. Renvoie celles qui sont nouvelles."""
    nouvelles = []
    for rel in relations_fonctionnelles(matrice, colonnes):
        ajout = connaissances.ajouter_relation(rel["variables"], "fonctionnelle", rel["preuve"], origine, fichier, rel["cible"])
        if ajout:
            nouvelles.append(ajout)
    deja = connaissances.paires_connues()
    for p in variables_apparentees(matrice, colonnes):
        if frozenset(p["variables"]) in deja:
            continue
        ajout = connaissances.ajouter_relation(p["variables"], "apparentees", p["preuve"], origine, fichier)
        if ajout:
            nouvelles.append(ajout)
    return nouvelles


# =============================================================================
# 3. Le robot débat avec l'Architecte
# =============================================================================

class Albert:
    """Physicien robot : soumet, écoute l'objection, réfute avec preuve calculée, sinon demande ; et cherche seul."""

    NOM = "Albert"

    def __init__(self, connaissances: Connaissances, nom: str = NOM):
        self.c = connaissances
        self.nom = nom

    def entrainer(self, matrice: pd.DataFrame, colonnes: Sequence[str], graphe: "am.GrapheConnaissances",
                  fichier: str = "matrice", contamination: float = 0.03, seed: int = 42) -> Dict[str, Any]:
        cols = [c for c in colonnes if c in matrice.columns]
        lecon: Dict[str, Any] = {"fichier": fichier, "date": _maintenant(), "variables": cols,
                                 "relations_apprises": [], "refutations": [], "questions": [], "verrou": None}
        if not cols or len(matrice) < 2:
            lecon["erreur"] = "aucune variable exploitable (fichier vide ou sans colonne numérique)"
            self.c.lecons.append(lecon)
            return lecon
        # 1) détection, puis ce que le FOND démontre : les relations sont apprises sur les seuls
        #    événements conformes, pour qu'une corrélation portée par les anomalies (un biais
        #    potentiel) ne soit jamais blanchie en « relation connue ».
        resultat = am.detecter_inconnu(matrice, cols, contamination=contamination, seed=seed)
        diag = am.diagnostiquer(resultat, cols)
        conformes = matrice[resultat["Inconnu"] == 1]
        lecon["relations_apprises"] = [r["preuve"] for r in apprendre_relations(conformes, self.c, list(matrice.columns), fichier, self.nom)]
        connues = self.c.paires_connues()
        # 2) débat
        lecon["n_anomalies"], lecon["n_total"] = diag.get("n_anomalies", 0), diag.get("n_total", 0)
        arch = am.Architecte(graphe, diag, physicien=self.nom, paires_connues=connues)
        dom = am.variable_dominante(diag)
        lecon["dominante"] = dom
        if diag.get("insuffisant") or not dom:
            obs = arch.enregistrer_observation(f"{self.nom} : trop peu d'événements isolés dans {fichier} pour débattre.")
            lecon["objection"] = arch.objection(obs)
            self.c.lecons.append(lecon)
            return lecon
        v = diag["variables"][dom]
        obs = arch.enregistrer_observation(
            f"{self.nom} soumet le lot isolé de {fichier} : {diag['n_anomalies']} événements sur {diag['n_total']}, "
            f"dominés par {dom} (d = {v['d_cohen']:.2f}, p = {v['p_value']:.2g}).")
        lecon["objection"] = arch.objection(obs)
        # 3) réfuter ce qui est démontrable, demander le reste
        for c in am.correlations_fortes(diag, dom, connues=connues):
            paire = frozenset((dom, c["autre"]))
            if c["nature"] == "suspecte":
                q = self.c.ajouter_question(
                    [dom, c["autre"]],
                    f"Dans {fichier}, {dom} et {c['autre']} sont corrélées chez les isolés (r = {c['r_isoles']:.2f}) "
                    f"mais pas chez les conformes (r = {c['r_conformes']:.2f}). Relation physique connue, ou biais ?",
                    fichier)
                lecon["questions"].append(q["id"])
            elif c["nature"] == "connue":
                rel = next((r for r in self.c.relations if paire <= set(r["variables"])), None)
                texte = (f"{self.nom} : la corrélation {dom} ↔ {c['autre']} n'est pas un biais, c'est une relation connue "
                         f"({rel['nature'] if rel else 'connue'} : {rel['preuve'] if rel else ''}).")
                arch.refutation(texte)
                lecon["refutations"].append(texte)
            elif c["nature"] == "structurelle":
                texte = (f"{self.nom} : {dom} ↔ {c['autre']} est corrélée chez les conformes aussi "
                         f"(r = {c['r_conformes']:.2f}) : propriété des données, pas un biais des anomalies.")
                arch.refutation(texte)
                lecon["refutations"].append(texte)
        texte_def, verrou = arch.defense()
        lecon["verrou"] = bool(verrou)
        lecon["defense"] = texte_def
        self.c.lecons.append(lecon)
        return lecon


    # -- recherche autonome ------------------------------------------------
    def strategies(self, matrice: pd.DataFrame) -> List[Dict[str, Any]]:
        """Les façons d'analyser qu'Albert essaie, dans l'ordre. Chacune est une liste de variables."""
        physiques = am.colonnes_analysables(list(matrice.columns))
        defaut = physiques[:8]
        strategies = [{"nom": "grandeurs par défaut", "variables": defaut}]
        deduites = self.c.variables_deduites()
        primitives = [c for c in physiques if c not in deduites]
        if deduites & set(physiques) and len(primitives) >= 2 and primitives != defaut:
            strategies.append({"nom": "grandeurs primitives (sans les variables déduites)", "variables": primitives[:8]})
        if len(physiques) > len(defaut):
            strategies.append({"nom": "toutes les grandeurs", "variables": physiques})
        return strategies

    def chercher(self, chemins: Sequence[str], reference: Optional[str] = None, graphe: Optional["am.GrapheConnaissances"] = None,
                 dossier_cahier: str = DOSSIER_CAHIER, contamination: float = 0.03, seed: int = 42,
                 max_evenements: Optional[int] = None, budget_minutes: float = 0.0,
                 rappel: Optional[Any] = None) -> Dict[str, Any]:
        """Albert cherche seul dans un dossier de runs et écrit son cahier de laboratoire. Renvoie le cahier."""
        import anemone_campagne as ac

        debut = time.time()
        g = graphe if graphe is not None else am.GrapheConnaissances()
        cahier: Dict[str, Any] = {"date": _maintenant(), "fichiers": [os.path.basename(c) for c in chemins],
                                  "reference": os.path.basename(reference) if reference else None,
                                  "lecons": [], "strategies": [], "verdicts": {}, "trouvailles": [], "pistes": [],
                                  "questions": [], "derives": [], "arret": None}

        def epuise() -> bool:
            return budget_minutes > 0 and (time.time() - debut) > 60 * budget_minutes

        # 1) une leçon par fichier : apprendre les relations, débattre
        premiere: Optional[pd.DataFrame] = None
        for i, chemin in enumerate(chemins):
            if epuise():
                cahier["arret"] = f"budget de {budget_minutes:g} min épuisé pendant les leçons ({i}/{len(chemins)} fichiers)"
                break
            try:
                matrice, _ = am.analyser_fichier_physique(chemin, os.path.basename(chemin), None, max_evenements)
            except Exception as exc:
                cahier["lecons"].append({"fichier": os.path.basename(chemin), "erreur": f"{type(exc).__name__}: {exc}"})
                continue
            cols = am.colonnes_analysables(list(matrice.columns))[:8]
            if not cols or len(matrice) < 2:
                cahier["lecons"].append({"fichier": os.path.basename(chemin), "erreur": "aucune variable exploitable"})
                continue
            premiere = premiere if premiere is not None else matrice
            try:
                lecon = self.entrainer(matrice, cols, g, os.path.basename(chemin), contamination, seed)
            except Exception as exc:  # une leçon ratée n'arrête pas la recherche
                cahier["lecons"].append({"fichier": os.path.basename(chemin), "erreur": f"{type(exc).__name__}: {exc}"})
                continue
            cahier["lecons"].append({k: lecon[k] for k in ("fichier", "dominante", "relations_apprises", "refutations", "questions", "verrou", "erreur")
                                     if k in lecon})
            if rappel:
                rappel("leçon", i + 1, len(chemins), os.path.basename(chemin))
        if premiere is None:
            cahier["arret"] = cahier["arret"] or "aucun fichier lisible"
            self._ecrire_cahier(cahier, dossier_cahier)
            return cahier

        # 2) les stratégies, chacune en campagne complète
        ref_df = None
        if reference:
            try:
                ref_df = ac.charger_reference(reference, max_evenements)
            except Exception as exc:
                cahier["derives"].append(f"référence illisible : {exc}")
        connues = self.c.paires_connues()
        for k, strat in enumerate(self.strategies(premiere)):
            if epuise():
                cahier["arret"] = f"budget de {budget_minutes:g} min épuisé avant la stratégie « {strat['nom']} »"
                break
            resultats = ac.analyser_campagne(list(chemins), strat["variables"], contamination, seed, True, ref_df,
                                             max_evenements, None, connues)
            strat_res = {"nom": strat["nom"], "variables": strat["variables"],
                         "verdicts": {r.fichier: r.verdict for r in resultats},
                         "details": {r.fichier: {"dominante": r.dominante, "d": r.d_cohen, "p": r.p_value,
                                                 "exces_fond": r.exces_fond, "stabilite": r.stabilite,
                                                 "motifs": r.motifs} for r in resultats}}
            cahier["strategies"].append(strat_res)
            params = {"strategie": strat["nom"], "variables": strat["variables"], "contamination": contamination, "seed": seed,
                      "reference": reference, "auteur": self.nom}
            ac.consigner_dans_graphe(g, resultats, params, None)
            for r in resultats:
                cahier["verdicts"].setdefault(r.fichier, {})[strat["nom"]] = r.verdict
                for c, x in r.derive_reference.items():
                    if x.get("derive") and k == 0:
                        cahier["derives"].append(f"{r.fichier} : {c} dérive par rapport à la référence (KS = {x['ks_stat']:.2f})")
            if rappel:
                rappel("stratégie", k + 1, len(self.strategies(premiere)), strat["nom"])

        # 2 bis) chasse aux bosses : le run de découverte sur les mêmes fichiers (masses présentes ou dérivées, cumul des runs)
        if not epuise():
            try:
                import anemone_decouverte as ad
                run = ad.lancer_run(list(chemins), reference=reference, max_evenements=max_evenements)
                cahier["bosses"] = {"conclusion": run.conclusion, "resume": run.resume,
                                    "candidats": [{"fichier": c["fichier"], "variable": c["bosse"]["variable"], "centre": c["bosse"]["centre"],
                                                   "p_global": c["bosse"]["p_global"], "verdict": c["verdict"], "connue": c["connue"],
                                                   "raison": c["raisons"][0] if c["raisons"] else ""}
                                                  for c in run.candidats if c["verdict"] != "ecarte"]}
                for c in run.candidats:
                    if c["verdict"] == "these":
                        cahier["trouvailles"].append({"fichier": c["fichier"], "strategies": ["chasse aux bosses"],
                                                      "details": {"dominante": c["bosse"]["variable"], "bosse": c["bosse"]["centre"],
                                                                  "p": c["bosse"]["p_global"], "d": None}})
                connues = [f"{c['fichier']} : {c['bosse']['variable']} ≈ {c['bosse']['centre']:.4g} ({c['connue']})"
                           for c in run.candidats if c["verdict"] == "connue"]
                if connues:
                    self.c.lecons.append({"type": "bosses_connues", "date": cahier["date"], "bosses": connues})
                if rappel:
                    rappel("bosses", 1, 1, run.conclusion)
            except Exception as exc:
                cahier["bosses"] = {"erreur": f"{type(exc).__name__}: {exc}"}
        else:
            cahier["arret"] = cahier.get("arret") or f"budget de {budget_minutes:g} min épuisé avant la chasse aux bosses"

        # 3) ce qui tient : trouvaille si « solide » sous ≥ 2 stratégies (ou sous la seule stratégie tentée)
        n_strats = len(cahier["strategies"])
        for fichier, par_strat in cahier["verdicts"].items():
            solides = [nom for nom, v in par_strat.items() if v == "solide"]
            if (n_strats >= 2 and len(solides) >= 2) or (n_strats == 1 and len(solides) == 1):
                cahier["trouvailles"].append({"fichier": fichier, "strategies": solides, "details": self._details(cahier, fichier, solides[0])})
            elif solides:
                cahier["pistes"].append({"fichier": fichier, "strategies": solides, "details": self._details(cahier, fichier, solides[0])})
        cahier["questions"] = [{"id": q["id"], "variables": q["variables"], "contexte": q["contexte"]} for q in self.c.questions_ouvertes()]
        cahier["duree_s"] = round(time.time() - debut, 1)
        cahier["connaissances"] = self.c.resume()
        self.c.lecons.append({"type": "recherche", "date": cahier["date"], "fichiers": cahier["fichiers"],
                              "trouvailles": [t["fichier"] for t in cahier["trouvailles"]],
                              "pistes": [t["fichier"] for t in cahier["pistes"]], "duree_s": cahier["duree_s"]})
        cahier["chemin"] = self._ecrire_cahier(cahier, dossier_cahier)
        return cahier

    @staticmethod
    def _details(cahier: Dict[str, Any], fichier: str, strategie: str) -> Dict[str, Any]:
        for s in cahier["strategies"]:
            if s["nom"] == strategie:
                return s["details"].get(fichier, {})
        return {}

    def _ecrire_cahier(self, cahier: Dict[str, Any], dossier: str) -> str:
        os.makedirs(dossier, exist_ok=True)
        base = os.path.join(dossier, datetime.now(timezone.utc).strftime("cahier_%Y%m%d_%H%M%S"))
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(cahier, f, ensure_ascii=False, indent=2, default=str)
        with open(base + ".md", "w", encoding="utf-8") as f:
            f.write(rediger_cahier(cahier, self.nom))
        return base + ".md"


PhysicienRobot = Albert  # alias


def rediger_cahier(cahier: Dict[str, Any], nom: str = Albert.NOM) -> str:
    """Le cahier de laboratoire d'Albert, lisible par le physicien."""
    L = [f"# Cahier de laboratoire de {nom} — {cahier['date']}", ""]
    L.append(f"Données : {len(cahier['fichiers'])} fichier(s)" + (f", référence : {cahier['reference']}" if cahier.get("reference") else ", sans référence") + ".")
    if cahier.get("arret"):
        L.append(f"Arrêt : {cahier['arret']}.")
    L.append("")
    L.append("## Ce que j'ai trouvé")
    L.append("")
    if cahier["trouvailles"]:
        for t in cahier["trouvailles"]:
            d = t["details"]
            L.append(f"- **{t['fichier']}** : « solide » sous {len(t['strategies'])} stratégies ({', '.join(t['strategies'])}). "
                     f"Dominante {d.get('dominante')}, d = {_f(d.get('d'))}, p = {_f(d.get('p'), 'g')}, excès fond ×{_f(d.get('exces_fond'))}, "
                     f"stabilité {_pct(d.get('stabilite'))}.")
    else:
        L.append("Rien qui tienne sous plusieurs stratégies. Je ne conclus pas.")
    if cahier["pistes"]:
        L.append("")
        L.append("Pistes (solide sous une seule stratégie, à confirmer) :")
        for t in cahier["pistes"]:
            L.append(f"- {t['fichier']} sous « {t['strategies'][0]} » : dominante {t['details'].get('dominante')}, d = {_f(t['details'].get('d'))}.")
    L += ["", "## Ce que j'ai tenté", ""]
    for s in cahier["strategies"]:
        comptes: Dict[str, int] = {}
        for v in s["verdicts"].values():
            comptes[v] = comptes.get(v, 0) + 1
        L.append(f"- **{s['nom']}** ({', '.join(s['variables'])}) : " + ", ".join(f"{n} {v}" for v, n in sorted(comptes.items())))
    L += ["", "## Ce que j'ai appris et enseigné à l'outil", ""]
    appris = list(dict.fromkeys(p for l in cahier["lecons"] for p in l.get("relations_apprises", [])))
    L += [f"- {p}" for p in appris] or ["- rien de nouveau : l'outil connaissait déjà ces relations, ou les données n'en montrent aucune"]
    refut = list(dict.fromkeys(r for l in cahier["lecons"] for r in l.get("refutations", [])))
    if refut:
        L += ["", "Objections de l'Architecte que j'ai réfutées avec preuve :", ""] + [f"- {r}" for r in refut]
    if cahier["derives"]:
        L += ["", "## Dérives par rapport à la référence", ""] + [f"- {d}" for d in cahier["derives"]]
    L += ["", "## Questions que je pose au physicien", ""]
    L += [f"- {' ↔ '.join(q['variables'])} : {q['contexte']}" for q in cahier["questions"]] or ["- aucune : tout ce que l'Architecte a soulevé, j'ai pu le trancher par le calcul"]
    bosses = cahier.get("bosses")
    if bosses:
        L += ["", "## Chasse aux bosses (run de découverte)", ""]
        if "erreur" in bosses:
            L.append(f"Impossible : {bosses['erreur']}.")
        else:
            L.append(bosses["resume"])
            for c in bosses["candidats"]:
                L.append(f"- {c['verdict']} — {c['fichier']} : {c['variable']} ≈ {c['centre']:.4g}, p globale {c['p_global']:.2g}"
                         + (f", {c['connue']}" if c.get("connue") else "") + f" — {c['raison']}")
    L += ["", "## Verdicts détaillés", "", "| Run | " + " | ".join(s["nom"] for s in cahier["strategies"]) + " |",
          "|---|" + "---|" * len(cahier["strategies"])]
    for fichier, par_strat in cahier["verdicts"].items():
        L.append(f"| {fichier} | " + " | ".join(par_strat.get(s["nom"], "—") for s in cahier["strategies"]) + " |")
    L += ["", f"Durée : {cahier.get('duree_s', 0)} s · connaissances de l'outil : {cahier.get('connaissances', {})}", ""]
    return "\n".join(L)


def _f(x: Any, mode: str = "f") -> str:
    try:
        if x is None or not np.isfinite(float(x)):
            return "—"
        return f"{float(x):.3g}" if mode == "g" else f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "—"


def _pct(x: Any) -> str:
    try:
        return "—" if x is None or not np.isfinite(float(x)) else f"{100 * float(x):.0f} %"
    except (TypeError, ValueError):
        return "—"


def resume_lecon(lecon: Dict[str, Any]) -> str:
    lignes = [f"Leçon sur {lecon['fichier']} — {lecon.get('n_anomalies', 0)} isolés sur {lecon.get('n_total', 0)}, "
              f"dominante : {lecon.get('dominante') or '—'}"]
    lignes += [f"  appris : {p}" for p in lecon.get("relations_apprises", [])] or ["  appris : rien de nouveau"]
    lignes += [f"  réfuté : {t}" for t in lecon.get("refutations", [])]
    lignes += [f"  question au physicien : {q}" for q in lecon.get("questions", [])]
    if lecon.get("verrou") is not None:
        lignes.append("  l'Architecte verrouille sa thèse" if lecon["verrou"] else "  l'Architecte cède (pas de preuve à verrouiller)")
    return "\n".join(lignes)


# =============================================================================
# 4. Ligne de commande
# =============================================================================

def _console_robuste() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    _console_robuste()
    p = argparse.ArgumentParser(description="A.N.E.M.O.N.E — physicien robot : il apprend et enseigne à l'outil.")
    p.add_argument("fichiers", nargs="*", help="fichiers .root / .csv sur lesquels s'entraîner")
    p.add_argument("--connaissances", default=FICHIER_CONNAISSANCES)
    p.add_argument("--graphe", default="anemone_graphe.json", help="graphe de connaissances à enrichir ('' pour aucun)")
    p.add_argument("--variables", help="colonnes, séparées par des virgules (défaut : grandeurs physiques, 8 premières)")
    p.add_argument("--contamination", type=float, default=0.03)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-evenements", type=int, default=None)
    p.add_argument("--etat", action="store_true", help="afficher ce que l'outil sait")
    p.add_argument("--chercher", metavar="DOSSIER", help="Albert cherche seul dans ce dossier de runs (cahier dans cahier_albert/)")
    p.add_argument("--reference", help="run de référence pour la recherche autonome")
    p.add_argument("--budget-minutes", type=float, default=0.0, help="temps maximal de recherche (0 = sans limite)")
    a = p.parse_args(argv)
    c = Connaissances.charger(a.connaissances)
    if a.etat or (not a.fichiers and not a.chercher):
        print(f"Connaissances : {c.resume()}  ({a.connaissances})")
        for r in c.relations:
            print(f"  relation [{r['nature']}] {' , '.join(r['variables'])} — {r['preuve']} ({r['origine']}, {r['date'][:10]})")
        for q in c.questions_ouvertes():
            print(f"  question ouverte {q['id']} : {' ↔ '.join(q['variables'])} — {q['contexte']}")
        return 0
    g = am.GrapheConnaissances.charger(a.graphe) if a.graphe and os.path.exists(a.graphe) else am.GrapheConnaissances()
    robot = Albert(c)
    if a.chercher:
        import anemone_campagne as ac
        chemins = [a.chercher] if os.path.isfile(a.chercher) else ac.lister_fichiers(a.chercher)
        print(f"[ALBERT] {len(chemins)} fichier(s) à explorer ...")
        cahier = robot.chercher(chemins, a.reference, g, DOSSIER_CAHIER, a.contamination, a.seed, a.max_evenements,
                                a.budget_minutes, rappel=lambda etape, i, n, nom: print(f"  {etape} {i}/{n} : {nom}"))
        print(f"[ALBERT] {len(cahier['trouvailles'])} trouvaille(s), {len(cahier['pistes'])} piste(s), "
              f"{len(cahier['questions'])} question(s) au physicien. Cahier : {cahier['chemin']}")
    for chemin in a.fichiers:
        matrice, _ = am.analyser_fichier_physique(chemin, os.path.basename(chemin), None, a.max_evenements)
        cols = [x.strip() for x in a.variables.split(",")] if a.variables else am.colonnes_analysables(list(matrice.columns))[:8]
        lecon = robot.entrainer(matrice, cols, g, os.path.basename(chemin), a.contamination, a.seed)
        print(resume_lecon(lecon))
    c.sauvegarder(a.connaissances)
    if a.graphe:
        g.sauvegarder(a.graphe)
    print(f"Connaissances enregistrées : {a.connaissances} — {c.resume()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
