# -*- coding: utf-8 -*-
"""
🌌 Projet A.N.E.M.O.N.E — Hub de co-recherche
Système d'exploration subatomique & Robot Architecte cognitif.

Un seul fichier : lecture de matrices réelles (.root / .csv), détection
non supervisée de l'inconnu (Isolation Forest), moteur visuel 4D, et
Architecte critique dont chaque débat est consigné dans un graphe de
connaissances persistant (st.session_state + export/import JSON).

Lancement :  streamlit run anemone_master.py
"""
from __future__ import annotations

import io
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:  # uproot est optionnel : sans lui, seuls les CSV sont lisibles.
    import uproot  # type: ignore
    UPROOT_DISPONIBLE = True
except Exception:  # pragma: no cover - dépend de l'environnement
    uproot = None
    UPROOT_DISPONIBLE = False

from scipy import stats as sp_stats
from sklearn.ensemble import IsolationForest

# =============================================================================
# 1. LECTURE DE MATRICES DE DONNÉES RÉELLES (.root / .csv)
# =============================================================================

EXTENSIONS_CSV = (".csv", ".tsv", ".txt", ".dat")
EXTENSIONS_ROOT = (".root",)
CLASSES_TABLES = ("TTree", "ROOT::RNTuple")  # les deux formats tabulaires de ROOT


def _est_numerique_plat(valeurs: Any) -> bool:
    """Vrai si `valeurs` est un tableau numpy 1D de nombres (pas de jagged array)."""
    return (
        isinstance(valeurs, np.ndarray)
        and valeurs.ndim == 1
        and np.issubdtype(valeurs.dtype, np.number)
    )


def lister_arbres_root(source: Any) -> List[str]:
    """Liste les tables (TTree ou RNTuple) d'un fichier ROOT (chemin ou objet binaire)."""
    if not UPROOT_DISPONIBLE:
        raise RuntimeError("Le paquet `uproot` n'est pas installé : pip install uproot")
    with uproot.open(source) as fichier:
        return [
            cle.split(";")[0]
            for cle, classe in fichier.classnames().items()
            if classe in CLASSES_TABLES
        ]


def lire_root(source: Any, arbre: Optional[str] = None, max_evenements: Optional[int] = None) -> pd.DataFrame:
    """Lit un TTree (ou RNTuple) ROOT et renvoie une matrice (DataFrame) des branches numériques plates.

    Les branches vectorielles (jagged) sont ignorées : chaque ligne doit être
    un événement décrit par des scalaires.
    """
    if not UPROOT_DISPONIBLE:
        raise RuntimeError("Le paquet `uproot` n'est pas installé : pip install uproot")
    with uproot.open(source) as fichier:
        arbres = [k.split(";")[0] for k, c in fichier.classnames().items() if c in CLASSES_TABLES]
        if not arbres:
            raise ValueError("Aucun TTree / RNTuple trouvé dans ce fichier ROOT.")
        nom = arbre or arbres[0]
        if nom not in arbres:
            raise ValueError(f"TTree « {nom} » introuvable. Disponibles : {arbres}")
        tree = fichier[nom]
        brut = tree.arrays(library="np", entry_stop=max_evenements)
    colonnes = {k: v for k, v in brut.items() if _est_numerique_plat(v)}
    if not colonnes:
        raise ValueError("Aucune branche numérique scalaire exploitable dans ce TTree.")
    return pd.DataFrame(colonnes)


def lire_csv(source: Any, max_evenements: Optional[int] = None) -> pd.DataFrame:
    """Lit un CSV/TSV (séparateur détecté automatiquement, lignes '#' ignorées)."""
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    df = pd.read_csv(source, sep=None, engine="python", comment="#", nrows=max_evenements)
    return df


def nettoyer_matrice(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Ne garde que les colonnes numériques, retire les lignes incomplètes / infinies.

    Renvoie la matrice propre et un petit rapport (colonnes écartées, lignes retirées).
    """
    numeriques = df.select_dtypes(include=[np.number]).copy()
    ecartees = [c for c in df.columns if c not in numeriques.columns]
    # Colonnes constantes : aucune information pour l'isolation.
    constantes = [c for c in numeriques.columns if numeriques[c].nunique(dropna=True) <= 1]
    numeriques = numeriques.drop(columns=constantes)
    n_avant = len(numeriques)
    numeriques = numeriques.replace([np.inf, -np.inf], np.nan).dropna()
    rapport = {
        "colonnes_non_numeriques": ecartees,
        "colonnes_constantes": constantes,
        "lignes_retirees": int(n_avant - len(numeriques)),
        "n_evenements": int(len(numeriques)),
        "n_variables": int(numeriques.shape[1]),
    }
    return numeriques.reset_index(drop=True), rapport


def analyser_fichier_physique(
    source: Any,
    nom_fichier: str,
    arbre: Optional[str] = None,
    max_evenements: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Point d'entrée unique : lit un .root ou un .csv et renvoie (matrice, rapport).

    `source` peut être un chemin, des octets ou un objet fichier. Le format est
    déduit de l'extension de `nom_fichier`.
    """
    ext = os.path.splitext(nom_fichier.lower())[1]
    if ext in EXTENSIONS_ROOT:
        if isinstance(source, (bytes, bytearray)):
            # uproot lit des chemins ou des objets fichier ; on passe par un fichier temporaire.
            with tempfile.NamedTemporaryFile(suffix=".root", delete=False) as tmp:
                tmp.write(source)
                chemin_tmp = tmp.name
            try:
                brut = lire_root(chemin_tmp, arbre=arbre, max_evenements=max_evenements)
            finally:
                os.unlink(chemin_tmp)
        else:
            brut = lire_root(source, arbre=arbre, max_evenements=max_evenements)
        format_ = "root"
    elif ext in EXTENSIONS_CSV or ext == "":
        brut = lire_csv(source, max_evenements=max_evenements)
        format_ = "csv"
    else:
        raise ValueError(f"Format non pris en charge : {ext} (attendu .root ou .csv)")
    matrice, rapport = nettoyer_matrice(brut)
    rapport.update({"fichier": nom_fichier, "format": format_, "arbre": arbre})
    return matrice, rapport


def generer_donnees_demo(seed: int = 42, n_standards: int = 1200, n_anomalies: int = 40) -> pd.DataFrame:
    """Jeu SYNTHÉTIQUE de démonstration (clairement étiqueté comme tel dans l'interface).

    Il ne sert qu'à prendre l'outil en main sans fichier : il n'a aucune valeur
    physique et n'est jamais utilisé quand un fichier réel est chargé.
    """
    rng = np.random.default_rng(seed)
    energie_std = rng.normal(4.0, 0.4, n_standards)
    temps_std = rng.uniform(0, 100, n_standards)
    angle_std = np.sin(temps_std) * 1.5 + rng.normal(0, 0.1, n_standards)
    temp_std = rng.normal(20.0, 0.3, n_standards)
    energie_ano = rng.uniform(9.0, 15.0, n_anomalies)
    temps_ano = rng.uniform(25, 75, n_anomalies)
    angle_ano = rng.uniform(-4, 4, n_anomalies)
    temp_ano = rng.uniform(27.0, 43.0, n_anomalies)
    return pd.DataFrame(
        {
            "Energie_MeV": np.concatenate([energie_std, energie_ano]),
            "Temps_ns": np.concatenate([temps_std, temps_ano]),
            "Angle_diffusion": np.concatenate([angle_std, angle_ano]),
            "Temperature_C": np.concatenate([temp_std, temp_ano]),
        }
    )


# =============================================================================
# 2. ISOLATION NON SUPERVISÉE DE L'INCONNU
# =============================================================================

def detecter_inconnu(
    df: pd.DataFrame,
    colonnes: Sequence[str],
    contamination: float = 0.03,
    seed: int = 42,
) -> pd.DataFrame:
    """Isolation Forest sur les colonnes choisies.

    Ajoute `Inconnu` (-1 = anomalie, 1 = conforme) et `Score_anomalie`
    (plus il est grand, plus l'événement est isolé).
    """
    colonnes = list(colonnes)
    if len(colonnes) == 0:
        raise ValueError("Choisir au moins une variable pour la détection.")
    X = df[colonnes].to_numpy(dtype=float)
    modele = IsolationForest(contamination=contamination, random_state=seed)
    resultat = df.copy()
    resultat["Inconnu"] = modele.fit_predict(X)
    resultat["Score_anomalie"] = -modele.decision_function(X)
    return resultat


# =============================================================================
# 3. DIAGNOSTIC QUANTITATIF (l'Architecte ne cite que des chiffres calculés)
# =============================================================================

def _mot_cle(colonne: str, motifs: Iterable[str]) -> bool:
    nom = colonne.lower()
    return any(re.search(m, nom) for m in motifs)


def deviner_roles(colonnes: Sequence[str]) -> Dict[str, Optional[str]]:
    """Devine (sans jamais l'imposer) quelle colonne joue le temps, l'énergie, la température."""
    roles: Dict[str, Optional[str]] = {"temps": None, "energie": None, "temperature": None}
    for c in colonnes:
        if roles["temperature"] is None and _mot_cle(c, [r"temp[ée]rat", r"^t_?c$", r"celsius", r"kelvin", r"°"]):
            roles["temperature"] = c
        elif roles["temps"] is None and _mot_cle(c, [r"^t$", r"temps", r"time", r"^ts", r"_ns$", r"timestamp", r"heure"]):
            roles["temps"] = c
        elif roles["energie"] is None and _mot_cle(c, [r"energ", r"^e$", r"mev", r"kev", r"gev", r"^q$", r"charge", r"npe", r"adc"]):
            roles["energie"] = c
    return roles


def diagnostiquer(df_resultat: pd.DataFrame, colonnes: Sequence[str]) -> Dict[str, Any]:
    """Compare anomalies vs conformes, variable par variable, et décrit la géométrie de l'inconnu.

    Tout ce que dit l'Architecte s'appuie sur ce dictionnaire : aucun chiffre
    n'est écrit en dur dans ses répliques.
    """
    colonnes = list(colonnes)
    ano = df_resultat[df_resultat["Inconnu"] == -1]
    ok = df_resultat[df_resultat["Inconnu"] == 1]
    diag: Dict[str, Any] = {
        "n_total": int(len(df_resultat)),
        "n_anomalies": int(len(ano)),
        "n_conformes": int(len(ok)),
        "variables": {},
        "correlations_anomalies": {},
        "geometrie": {},
        "roles": deviner_roles(colonnes),
    }
    if len(ano) < 2 or len(ok) < 2:
        diag["insuffisant"] = True
        return diag
    diag["insuffisant"] = False

    for c in colonnes:
        a, b = ano[c].to_numpy(float), ok[c].to_numpy(float)
        s_pool = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
        d_cohen = float((a.mean() - b.mean()) / s_pool) if s_pool > 0 else float("inf")
        ks = sp_stats.ks_2samp(a, b)
        diag["variables"][c] = {
            "moy_anomalies": float(a.mean()),
            "moy_conformes": float(b.mean()),
            "ecart_type_conformes": float(b.std(ddof=1)),
            "d_cohen": d_cohen,
            "ks_stat": float(ks.statistic),
            "p_value": float(ks.pvalue),
        }

    # Corrélations internes aux anomalies (chercher un biais instrumental caché).
    if len(colonnes) >= 2:
        corr = ano[colonnes].corr().fillna(0.0)
        for i, c1 in enumerate(colonnes):
            for c2 in colonnes[i + 1:]:
                diag["correlations_anomalies"][f"{c1} ↔ {c2}"] = float(corr.loc[c1, c2])

    # Géométrie : direction principale du nuage d'anomalies (variables standardisées).
    Z = (ano[colonnes] - ok[colonnes].mean()) / ok[colonnes].std(ddof=1).replace(0, 1.0)
    Z = Z.to_numpy(float)
    Zc = Z - Z.mean(axis=0)
    try:
        _, s, vt = np.linalg.svd(Zc, full_matrices=False)
        variance_expliquee = float(s[0] ** 2 / max(np.sum(s ** 2), 1e-12))
        axe = vt[0]
    except np.linalg.LinAlgError:  # pragma: no cover
        variance_expliquee, axe = 0.0, np.zeros(len(colonnes))
    diag["geometrie"] = {
        "centroide_sigma": {c: float(v) for c, v in zip(colonnes, Z.mean(axis=0))},
        "axe_principal": {c: float(v) for c, v in zip(colonnes, axe)},
        "variance_expliquee_axe1": variance_expliquee,
    }

    # Concentration temporelle des anomalies (épisode transitoire ?)
    t = diag["roles"]["temps"]
    if t and t in colonnes:
        etendue = float(df_resultat[t].max() - df_resultat[t].min())
        fenetre = float(ano[t].max() - ano[t].min())
        diag["geometrie"]["fraction_fenetre_temporelle"] = fenetre / etendue if etendue > 0 else 1.0
    return diag


def variable_dominante(diag: Dict[str, Any]) -> Optional[str]:
    """Variable qui sépare le plus les anomalies des conformes (|d de Cohen| max)."""
    if not diag.get("variables"):
        return None
    return max(diag["variables"], key=lambda c: abs(diag["variables"][c]["d_cohen"]))


# =============================================================================
# 4. GRAPHE DE CONNAISSANCES PERSISTANT
# =============================================================================

TYPES_NOEUDS = ("jeu_de_donnees", "anomalies", "observation", "objection", "hypothese", "defense", "refutation", "parametres")


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class GrapheConnaissances:
    """Graphe orienté sérialisable : nœuds typés + arêtes étiquetées.

    Stocké tel quel dans `st.session_state["graphe"]` et exportable en JSON
    pour survivre à la fermeture de l'onglet.
    """

    VERSION = 1

    def __init__(self, noeuds: Optional[List[Dict[str, Any]]] = None, aretes: Optional[List[Dict[str, Any]]] = None):
        self.noeuds: List[Dict[str, Any]] = noeuds or []
        self.aretes: List[Dict[str, Any]] = aretes or []

    # -- écriture ---------------------------------------------------------
    def ajouter_noeud(self, type_: str, texte: str, meta: Optional[Dict[str, Any]] = None) -> str:
        if type_ not in TYPES_NOEUDS:
            raise ValueError(f"Type de nœud inconnu : {type_}")
        identifiant = f"{type_}-{uuid.uuid4().hex[:8]}"
        self.noeuds.append(
            {"id": identifiant, "type": type_, "texte": texte, "horodatage": _horodatage(), "meta": meta or {}}
        )
        return identifiant

    def ajouter_arete(self, source: str, cible: str, relation: str) -> None:
        ids = {n["id"] for n in self.noeuds}
        if source not in ids or cible not in ids:
            raise KeyError("Arête vers un nœud inexistant.")
        self.aretes.append({"source": source, "cible": cible, "relation": relation, "horodatage": _horodatage()})

    # -- lecture ----------------------------------------------------------
    def noeud(self, identifiant: str) -> Optional[Dict[str, Any]]:
        return next((n for n in self.noeuds if n["id"] == identifiant), None)

    def dernier(self, type_: str) -> Optional[Dict[str, Any]]:
        candidats = [n for n in self.noeuds if n["type"] == type_]
        return candidats[-1] if candidats else None

    def par_type(self, type_: str) -> List[Dict[str, Any]]:
        return [n for n in self.noeuds if n["type"] == type_]

    def voisins(self, identifiant: str) -> List[Tuple[str, str, str]]:
        """(relation, id_autre, sens) pour chaque arête touchant le nœud."""
        res = []
        for a in self.aretes:
            if a["source"] == identifiant:
                res.append((a["relation"], a["cible"], "sortante"))
            elif a["cible"] == identifiant:
                res.append((a["relation"], a["source"], "entrante"))
        return res

    def chronologie(self) -> List[Dict[str, Any]]:
        return sorted(self.noeuds, key=lambda n: n["horodatage"])

    def statistiques(self) -> Dict[str, int]:
        compte = {t: 0 for t in TYPES_NOEUDS}
        for n in self.noeuds:
            compte[n["type"]] += 1
        compte["aretes"] = len(self.aretes)
        return compte

    # -- persistance ------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"version": self.VERSION, "noeuds": self.noeuds, "aretes": self.aretes}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, donnees: Dict[str, Any]) -> "GrapheConnaissances":
        return cls(list(donnees.get("noeuds", [])), list(donnees.get("aretes", [])))

    @classmethod
    def from_json(cls, texte: str) -> "GrapheConnaissances":
        return cls.from_dict(json.loads(texte))

    def sauvegarder(self, chemin: str) -> None:
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def charger(cls, chemin: str) -> "GrapheConnaissances":
        with open(chemin, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    # -- visualisation ----------------------------------------------------
    def vers_networkx(self):
        import networkx as nx  # import local : facultatif hors interface

        g = nx.DiGraph()
        for n in self.noeuds:
            g.add_node(n["id"], **n)
        for a in self.aretes:
            g.add_edge(a["source"], a["cible"], relation=a["relation"])
        return g


# =============================================================================
# 5. LOGIQUE COGNITIVE DE L'ARCHITECTE
# =============================================================================

def _fmt(x: float, nd: int = 2) -> str:
    if x == float("inf"):
        return "∞"
    if abs(x) < 1e-3 and x != 0:
        return f"{x:.1e}"
    return f"{x:.{nd}f}"


def _p_fmt(p: float) -> str:
    return "< 0.001" if p < 1e-3 else f"= {p:.3f}"


class Architecte:
    """Collègue virtuel critique. Chaque réplique est calculée à partir du diagnostic
    ET inscrite dans le graphe de connaissances, reliée à ce qu'elle conteste,
    propose ou défend.
    """

    SEUIL_P_VERROU = 1e-3   # p-value en dessous de laquelle il verrouille sa thèse
    SEUIL_D_VERROU = 1.0    # taille d'effet (|d de Cohen|) minimale pour verrouiller
    SEUIL_CORR_BIAIS = 0.5  # corrélation interne aux anomalies jugée suspecte

    def __init__(self, graphe: GrapheConnaissances, diag: Dict[str, Any], physicien: str = "Frédéric"):
        self.g = graphe
        self.diag = diag
        self.physicien = physicien

    # -- ancrages dans le graphe --------------------------------------------
    def _noeud_anomalies(self) -> str:
        """Nœud résumant le lot d'anomalies courant (réutilisé tant que le diagnostic ne change pas)."""
        signature = {"n_anomalies": self.diag.get("n_anomalies"), "n_total": self.diag.get("n_total"),
                     "dominante": variable_dominante(self.diag)}
        dernier = self.g.dernier("anomalies")
        if dernier and dernier["meta"].get("signature") == signature:
            return dernier["id"]
        texte = f"{signature['n_anomalies']} événements isolés sur {signature['n_total']}"
        if signature["dominante"]:
            texte += f" — variable dominante : {signature['dominante']}"
        return self.g.ajouter_noeud("anomalies", texte, {"signature": signature, "diagnostic": self.diag})

    def enregistrer_observation(self, texte: str) -> str:
        ident = self.g.ajouter_noeud("observation", texte, {"auteur": self.physicien})
        self.g.ajouter_arete(ident, self._noeud_anomalies(), "porte_sur")
        return ident

    # -- modes ---------------------------------------------------------------
    def objection(self, observation_id: Optional[str] = None) -> str:
        d = self.diag
        if d.get("insuffisant"):
            texte = ("🚨 **OBJECTION DE L'ARCHITECTE :** je n'ai pas assez d'événements isolés pour "
                     "contredire quoi que ce soit. Avant toute interprétation, augmente la statistique ou "
                     "revois le taux de contamination.")
        else:
            dom = variable_dominante(d)
            v = d["variables"][dom]
            roles = d["roles"]
            lignes = [f"🚨 **OBJECTION DE L'ARCHITECTE :**",
                      f"{self.physicien}, ton regard se porte sur **{dom}** (moyenne {_fmt(v['moy_anomalies'])} chez les "
                      f"événements isolés contre {_fmt(v['moy_conformes'])} chez les conformes, d de Cohen = {_fmt(v['d_cohen'])})."]
            # 1) biais instrumental : corrélation forte entre la dominante et une autre variable, surtout thermique
            suspects = []
            for paire, r in d["correlations_anomalies"].items():
                if dom in paire and abs(r) >= self.SEUIL_CORR_BIAIS:
                    autre = paire.replace(dom, "").replace("↔", "").strip()
                    suspects.append((autre, r))
            if suspects:
                autre, r = max(suspects, key=lambda x: abs(x[1]))
                thermique = roles.get("temperature") == autre
                lignes.append(
                    f"Or, au sein même des anomalies, **{dom}** est corrélée à **{autre}** (r = {_fmt(r)}). "
                    + ("Ce que tu prends pour un signal physique pourrait être un effet **thermique instrumental** du capteur. "
                       if thermique else "Cette dépendance est suspecte : un effet de l'appareillage n'est pas exclu. ")
                    + f"Prouve-moi le contraire en retirant **{autre}** des variables et en vérifiant que l'isolement persiste."
                )
            else:
                lignes.append(
                    f"Aucune corrélation interne supérieure à {self.SEUIL_CORR_BIAIS} n'implique **{dom}** : "
                    "je ne peux pas invoquer un biais instrumental simple, mais je ne te crois pas pour autant."
                )
            # 2) épisode transitoire
            frac = d["geometrie"].get("fraction_fenetre_temporelle")
            if frac is not None and frac < 0.6:
                lignes.append(
                    f"De plus, les anomalies occupent seulement **{_fmt(100 * frac, 0)} %** de la plage temporelle : "
                    "cela ressemble à un épisode transitoire (dérive, prise de données perturbée), pas à une loi permanente."
                )
            # 3) robustesse au paramètre de contamination
            lignes.append(
                f"Enfin, ces {d['n_anomalies']} événements sont définis par un taux de contamination choisi à la main : "
                "fais-le varier et montre-moi que le même noyau d'événements reste isolé."
            )
            texte = "\n".join(lignes)
        ident = self.g.ajouter_noeud("objection", texte, {"diagnostic": self.diag})
        self.g.ajouter_arete(ident, self._noeud_anomalies(), "porte_sur")
        if observation_id:
            self.g.ajouter_arete(ident, observation_id, "conteste")
        return texte

    def hypothese(self, observation_id: Optional[str] = None) -> str:
        d = self.diag
        if d.get("insuffisant"):
            texte = ("💡 **HYPOTHÈSE DE L'ARCHITECTE :** trop peu d'événements isolés pour dessiner une géométrie. "
                     "Charge davantage de données avant que je me risque à une conjecture.")
        else:
            geo = d["geometrie"]
            axe = sorted(geo["axe_principal"].items(), key=lambda kv: -abs(kv[1]))
            centro = sorted(geo["centroide_sigma"].items(), key=lambda kv: -abs(kv[1]))
            composantes = ", ".join(f"{c} ({_fmt(v)})" for c, v in axe[:3])
            decalages = ", ".join(f"{c} à {_fmt(v, 1)} σ" for c, v in centro[:3])
            lignes = [
                "💡 **HYPOTHÈSE DE L'ARCHITECTE (exploration aveugle, à réfuter) :**",
                f"Le nuage des {d['n_anomalies']} événements isolés est décalé de la physique conforme de : {decalages}.",
                f"Son axe principal (variables standardisées) explique **{_fmt(100 * geo['variance_expliquee_axe1'], 0)} %** "
                f"de sa dispersion et se décompose sur : {composantes}.",
            ]
            if geo["variance_expliquee_axe1"] >= 0.6:
                lignes.append(
                    "Une telle unidimensionnalité est le signe d'un **mécanisme unique** qui pousse ces événements le long "
                    "d'une seule direction — pas d'un fond aléatoire. Et si ce n'était pas un neutrino ordinaire, mais une "
                    "espèce d'interaction non répertoriée dont la signature serait justement cette direction ? "
                    "Testons-la : projetons chaque événement sur cet axe et cherchons une structure (pic, périodicité)."
                )
            else:
                lignes.append(
                    "La dispersion est répartie sur plusieurs axes : soit plusieurs mécanismes se superposent, soit "
                    "l'inconnu est un mélange de fonds. Hypothèse audacieuse : découpe le nuage en sous-populations "
                    "(clustering) et vérifie si l'une d'elles est alignée — c'est celle-là qui mérite une théorie."
                )
            texte = "\n".join(lignes)
        ident = self.g.ajouter_noeud("hypothese", texte, {"geometrie": self.diag.get("geometrie", {})})
        self.g.ajouter_arete(ident, self._noeud_anomalies(), "porte_sur")
        if observation_id:
            self.g.ajouter_arete(ident, observation_id, "repond_a")
        derniere_obj = self.g.dernier("objection")
        if derniere_obj:
            self.g.ajouter_arete(ident, derniere_obj["id"], "prolonge")
        return texte

    def defense(self) -> Tuple[str, bool]:
        """Plaidoyer : verrouille (True) uniquement si les preuves calculées passent les seuils."""
        d = self.diag
        verrou = False
        if d.get("insuffisant"):
            texte = "🛡️ **DÉFENSE DE THÈSE :** sans statistique suffisante, je ne verrouille rien. Un scientifique honnête attend les données."
        else:
            preuves = sorted(d["variables"].items(), key=lambda kv: kv[1]["p_value"])
            fortes = [(c, v) for c, v in preuves if v["p_value"] < self.SEUIL_P_VERROU and abs(v["d_cohen"]) >= self.SEUIL_D_VERROU]
            tableau = "\n".join(
                f"- **{c}** : d = {_fmt(v['d_cohen'])}, KS = {_fmt(v['ks_stat'])}, p {_p_fmt(v['p_value'])}"
                for c, v in preuves
            )
            if fortes:
                verrou = True
                noms = ", ".join(c for c, _ in fortes)
                texte = (
                    "🛡️ **DÉFENSE DE THÈSE (preuve formelle verrouillée) :**\n"
                    f"Je maintiens ma conclusion, {self.physicien}. Test de Kolmogorov–Smirnov anomalies vs conformes, variable par variable :\n"
                    f"{tableau}\n"
                    f"Sur **{noms}**, la séparation est à la fois significative (p < {self.SEUIL_P_VERROU}) et massive "
                    f"(|d| ≥ {self.SEUIL_D_VERROU}). Ce lot n'est pas une fluctuation du fond connu. L'écran reste verrouillé "
                    "tant que tu n'as pas réfuté mathématiquement ce modèle (variable instrumentale, coupure, ou nouveau jeu de données)."
                )
            else:
                texte = (
                    "🛡️ **DÉFENSE DE THÈSE — je cède :**\n"
                    f"{tableau}\n"
                    f"Aucune variable ne passe simultanément p < {self.SEUIL_P_VERROU} et |d| ≥ {self.SEUIL_D_VERROU}. "
                    "Je n'ai pas de preuve à verrouiller ; ma thèse reste une conjecture ouverte."
                )
        ident = self.g.ajouter_noeud("defense", texte, {"verrou": verrou, "variables": d.get("variables", {})})
        self.g.ajouter_arete(ident, self._noeud_anomalies(), "porte_sur")
        derniere_hyp = self.g.dernier("hypothese")
        if derniere_hyp:
            self.g.ajouter_arete(ident, derniere_hyp["id"], "defend")
        derniere_obj = self.g.dernier("objection")
        if derniere_obj:
            self.g.ajouter_arete(ident, derniere_obj["id"], "repond_a")
        return texte, verrou

    def refutation(self, texte: str) -> str:
        """Le physicien réfute la thèse verrouillée : consigné et relié à la défense."""
        ident = self.g.ajouter_noeud("refutation", texte, {"auteur": self.physicien})
        derniere_def = self.g.dernier("defense")
        if derniere_def:
            self.g.ajouter_arete(ident, derniere_def["id"], "refute")
        return ident

    @staticmethod
    def attente() -> str:
        return "🤖 *L'Architecte observe tes manipulations graphiques, analyse les flux et recalcule ses matrices de probabilités...*"


# =============================================================================
# 6. INTERFACE STREAMLIT
# =============================================================================

def _init_session(st) -> None:
    if "graphe" not in st.session_state:
        st.session_state["graphe"] = GrapheConnaissances().to_dict()
    st.session_state.setdefault("verrou", False)
    st.session_state.setdefault("derniere_reponse", None)
    st.session_state.setdefault("derniere_observation", None)
    st.session_state.setdefault("jeu_courant", None)


def _graphe(st) -> GrapheConnaissances:
    return GrapheConnaissances.from_dict(st.session_state["graphe"])


def _sauver_graphe(st, g: GrapheConnaissances, chemin_auto: Optional[str]) -> None:
    st.session_state["graphe"] = g.to_dict()
    if chemin_auto:
        try:
            g.sauvegarder(chemin_auto)
        except OSError as exc:  # pragma: no cover - dépend du disque
            st.warning(f"Sauvegarde automatique impossible : {exc}")


def _figure_4d(df: pd.DataFrame, x: str, y: str, z: str, couleur: str, colonnes: Sequence[str], diag: Dict[str, Any]):
    import plotly.graph_objects as go

    ok = df[df["Inconnu"] == 1]
    ano = df[df["Inconnu"] == -1].sort_values(by=x)
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=ok[x], y=ok[y], z=ok[z], mode="markers", name="🟢 Physique conforme (estompée)",
        marker=dict(size=2, color="#2ecc71", opacity=0.2),
    ))
    if len(ano):
        fig.add_trace(go.Scatter3d(
            x=ano[x], y=ano[y], z=ano[z], mode="markers+lines", name="🔥 Flux d'anomalies non cartographiées",
            marker=dict(size=7, color=ano[couleur], colorscale="Hot", opacity=0.9, showscale=True,
                        colorbar=dict(title=couleur)),
            line=dict(color="rgba(231, 76, 60, 0.4)", width=2),
            text=[f"score={s:.3f}" for s in ano["Score_anomalie"]],
        ))
    # Vecteur de tendance : axe principal du nuage d'anomalies passant par son centroïde (unités réelles).
    geo = diag.get("geometrie", {})
    if geo.get("axe_principal") and len(ano) >= 2 and all(c in geo["axe_principal"] for c in (x, y, z)):
        centro = ano[[x, y, z]].mean()
        ecarts = ano[[x, y, z]].std(ddof=1).replace(0, 1.0)
        direction = np.array([geo["axe_principal"][x], geo["axe_principal"][y], geo["axe_principal"][z]])
        if np.linalg.norm(direction) > 0:
            direction = direction / np.linalg.norm(direction)
            longueur = 2.0
            p1 = centro - longueur * direction * ecarts
            p2 = centro + longueur * direction * ecarts
            fig.add_trace(go.Scatter3d(
                x=[p1[x], p2[x]], y=[p1[y], p2[y]], z=[p1[z], p2[z]], mode="lines",
                name="➡️ Vecteur de tendance (axe principal)", line=dict(color="#e67e22", width=6),
            ))
    fig.update_layout(
        margin=dict(l=0, r=0, b=0, t=0), height=560,
        scene=dict(xaxis_title=x, yaxis_title=y, zaxis_title=z),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    return fig


COULEURS_NOEUDS = {
    "jeu_de_donnees": "#3498db", "anomalies": "#e74c3c", "observation": "#f1c40f", "objection": "#e67e22",
    "hypothese": "#9b59b6", "defense": "#1abc9c", "refutation": "#2c3e50", "parametres": "#95a5a6",
}


def _figure_graphe(g: GrapheConnaissances):
    import networkx as nx
    import plotly.graph_objects as go

    nxg = g.vers_networkx()
    if nxg.number_of_nodes() == 0:
        return None
    pos = nx.spring_layout(nxg, seed=7, k=1.2)
    fig = go.Figure()
    for a in g.aretes:
        (x0, y0), (x1, y1) = pos[a["source"]], pos[a["cible"]]
        fig.add_trace(go.Scatter(x=[x0, x1, None], y=[y0, y1, None], mode="lines",
                                 line=dict(color="#7f8c8d", width=1), hoverinfo="text",
                                 text=a["relation"], showlegend=False))
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=a["relation"], showarrow=False,
                           font=dict(size=9, color="#7f8c8d"))
    for type_ in TYPES_NOEUDS:
        noeuds = g.par_type(type_)
        if not noeuds:
            continue
        fig.add_trace(go.Scatter(
            x=[pos[n["id"]][0] for n in noeuds], y=[pos[n["id"]][1] for n in noeuds], mode="markers+text",
            name=type_, text=[n["id"].split("-")[1] for n in noeuds], textposition="top center",
            hovertext=[n["texte"][:300] for n in noeuds], hoverinfo="text",
            marker=dict(size=16, color=COULEURS_NOEUDS[type_]),
        ))
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0), height=420, xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def lancer_interface() -> None:  # pragma: no cover - interface graphique
    import streamlit as st

    st.set_page_config(layout="wide", page_title="A.N.E.M.O.N.E & L'Architecte")
    _init_session(st)
    st.title("🌌 Projet A.N.E.M.O.N.E — Hub de Co-Recherche")
    st.subheader("Système d'Analyse Subatomique & Robot Architecte Cognitif")
    st.markdown("---")

    # ------------------------------------------------------------------ barre latérale
    with st.sidebar:
        st.header("📂 Source des données")
        physicien = st.text_input("Nom du physicien", value="Frédéric Yermia")
        mode_source = st.radio("Mode", ["Fichier téléversé (.root / .csv)", "Chemin local", "Démo synthétique (aucune valeur physique)"])
        max_ev = st.number_input("Événements max (0 = tous)", min_value=0, value=0, step=1000)
        max_ev = int(max_ev) or None
        matrice, rapport, erreur = None, None, None
        source_id = None
        try:
            if mode_source.startswith("Fichier"):
                fichier = st.file_uploader("Matrice de physique nucléaire", type=["root", "csv", "tsv", "txt", "dat"])
                if fichier is not None:
                    octets = fichier.getvalue()
                    arbre = None
                    if fichier.name.lower().endswith(".root"):
                        if not UPROOT_DISPONIBLE:
                            raise RuntimeError("Installer `uproot` pour lire les fichiers ROOT.")
                        with tempfile.NamedTemporaryFile(suffix=".root", delete=False) as tmp:
                            tmp.write(octets)
                        try:
                            arbres = lister_arbres_root(tmp.name)
                        finally:
                            os.unlink(tmp.name)
                        arbre = st.selectbox("TTree / RNTuple", arbres)
                    matrice, rapport = _charger_cache(st, octets, fichier.name, arbre, max_ev)
                    source_id = f"{fichier.name}:{arbre}:{len(octets)}"
            elif mode_source.startswith("Chemin"):
                chemin = st.text_input("Chemin du fichier", placeholder="/data/run_1234.root")
                if chemin:
                    if not os.path.exists(chemin):
                        raise FileNotFoundError(chemin)
                    arbre = None
                    if chemin.lower().endswith(".root"):
                        arbre = st.selectbox("TTree / RNTuple", lister_arbres_root(chemin))
                    matrice, rapport = analyser_fichier_physique(chemin, os.path.basename(chemin), arbre, max_ev)
                    source_id = f"{chemin}:{arbre}:{os.path.getmtime(chemin)}"
            else:
                matrice = generer_donnees_demo()
                matrice, rapport = nettoyer_matrice(matrice)
                rapport.update({"fichier": "DÉMO SYNTHÉTIQUE", "format": "demo", "arbre": None})
                source_id = "demo"
        except Exception as exc:  # affichage propre de toute erreur de lecture
            erreur = str(exc)

        if erreur:
            st.error(f"Lecture impossible : {erreur}")
        if rapport:
            st.caption(f"📄 {rapport['fichier']} — {rapport['n_evenements']} événements × {rapport['n_variables']} variables")
            if rapport["colonnes_non_numeriques"] or rapport["colonnes_constantes"] or rapport["lignes_retirees"]:
                with st.expander("Rapport de nettoyage"):
                    st.json({k: rapport[k] for k in ("colonnes_non_numeriques", "colonnes_constantes", "lignes_retirees")})

        st.header("🧠 Détection de l'inconnu")
        colonnes = list(matrice.columns) if matrice is not None else []
        choisies = st.multiselect("Variables analysées", colonnes, default=colonnes[:8]) if colonnes else []
        contamination = st.slider("Taux de contamination (part attendue d'inconnu)", 0.005, 0.20, 0.03, 0.005)
        seed = st.number_input("Graine aléatoire", min_value=0, value=42, step=1)

        st.header("💾 Graphe de connaissances")
        chemin_auto = st.text_input("Sauvegarde auto (fichier JSON, vide = désactivée)", value="anemone_graphe.json")
        chemin_auto = chemin_auto.strip() or None
        if chemin_auto and os.path.exists(chemin_auto) and st.button("↩️ Recharger depuis le fichier"):
            st.session_state["graphe"] = GrapheConnaissances.charger(chemin_auto).to_dict()
            st.success("Graphe rechargé.")
        importe = st.file_uploader("Importer un graphe (.json)", type=["json"], key="import_graphe")
        if importe is not None and st.button("📥 Fusionner l'import"):
            g_imp = GrapheConnaissances.from_json(importe.getvalue().decode("utf-8"))
            g_cur = _graphe(st)
            ids = {n["id"] for n in g_cur.noeuds}
            g_cur.noeuds += [n for n in g_imp.noeuds if n["id"] not in ids]
            g_cur.aretes += [a for a in g_imp.aretes if a not in g_cur.aretes]
            _sauver_graphe(st, g_cur, chemin_auto)
            st.success(f"{len(g_imp.noeuds)} nœuds importés.")
        st.download_button("📤 Exporter le graphe (JSON)", _graphe(st).to_json(), file_name="anemone_graphe.json", mime="application/json")
        if st.button("🗑️ Réinitialiser le graphe"):
            st.session_state["graphe"] = GrapheConnaissances().to_dict()
            st.session_state["verrou"] = False
            st.rerun()

    if matrice is None or not choisies:
        st.info("Charge une matrice (.root ou .csv) et choisis les variables à analyser dans la barre latérale.")
        st.stop()

    # ------------------------------------------------------------------ détection + diagnostic
    resultat = detecter_inconnu(matrice, choisies, contamination=float(contamination), seed=int(seed))
    diag = diagnostiquer(resultat, choisies)
    anomalies = resultat[resultat["Inconnu"] == -1]
    g = _graphe(st)

    # Nœud « jeu de données » (un par source chargée) + nœud paramètres (à chaque changement).
    if st.session_state["jeu_courant"] != source_id:
        ident = g.ajouter_noeud("jeu_de_donnees", f"{rapport['fichier']} ({rapport['format']}) — {rapport['n_evenements']} événements", rapport)
        st.session_state["jeu_courant"] = source_id
        st.session_state["noeud_jeu"] = ident
        st.session_state["verrou"] = False
        _sauver_graphe(st, g, chemin_auto)
    params = {"variables": list(choisies), "contamination": float(contamination), "seed": int(seed)}
    dernier_p = g.dernier("parametres")
    if not dernier_p or dernier_p["meta"] != params:
        ident = g.ajouter_noeud("parametres", f"Isolation Forest · contamination {contamination} · {len(choisies)} variables", params)
        if st.session_state.get("noeud_jeu") and g.noeud(st.session_state["noeud_jeu"]):
            g.ajouter_arete(ident, st.session_state["noeud_jeu"], "applique_a")
        _sauver_graphe(st, g, chemin_auto)

    architecte = Architecte(g, diag, physicien=physicien.split(" ")[0] if physicien else "collègue")

    if rapport["format"] == "demo":
        st.warning("⚠️ Données SYNTHÉTIQUES de démonstration : aucune conclusion physique n'en découle.")

    # ------------------------------------------------------------------ mise en page
    col_gauche, col_droite = st.columns([3, 2])

    with col_gauche:
        st.write("### 🎬 Visualisation cinématique 4D des flux d'événements")
        roles = diag["roles"]
        defaut = lambda role, i: (roles.get(role) if roles.get(role) in choisies else choisies[min(i, len(choisies) - 1)])
        c1, c2, c3, c4 = st.columns(4)
        x = c1.selectbox("Axe X", choisies, index=choisies.index(defaut("temps", 0)))
        y = c2.selectbox("Axe Y", choisies, index=choisies.index(defaut("energie", 1)))
        z = c3.selectbox("Axe Z", choisies, index=min(2, len(choisies) - 1))
        couleur = c4.selectbox("Couleur (4ᵉ dimension)", choisies + ["Score_anomalie"],
                               index=(choisies + ["Score_anomalie"]).index(defaut("temperature", 3) if roles.get("temperature") in choisies else "Score_anomalie"))
        if st.session_state["verrou"]:
            st.error("🔒 ÉCRAN VERROUILLÉ PAR L'ARCHITECTE — réfute sa thèse dans le panneau de droite pour reprendre la main.")
        else:
            st.plotly_chart(_figure_4d(resultat, x, y, z, couleur, choisies, diag), width="stretch")
        m1, m2, m3 = st.columns(3)
        m1.metric("Événements", diag["n_total"])
        m2.metric("Isolés (inconnu)", diag["n_anomalies"])
        m3.metric("Variable dominante", variable_dominante(diag) or "—")

    with col_droite:
        st.write("### 🤖 Bureau de l'Architecte (collègue virtuel critique)")
        with st.form("debat", clear_on_submit=True):
            interaction = st.text_input("Débattre avec l'Architecte / soumettre une observation :", key="saisie_debat",
                                        placeholder="Ex : je pense que le pic d'énergie isole un neutrino stérile...")
            b1, b2, b3, b4 = st.columns(4)
            btn_obs = b1.form_submit_button("💬 Soumettre")
            btn_obj = b2.form_submit_button("⚠️ Objection")
            btn_hyp = b3.form_submit_button("🔮 Hypothèse")
            btn_def = b4.form_submit_button("🛡️ Preuves")

        obs_id = None
        if interaction and (btn_obs or btn_obj or btn_hyp or btn_def):
            obs_id = architecte.enregistrer_observation(interaction)
        reponse = None
        if btn_obs and interaction:
            reponse = architecte.objection(obs_id)  # par défaut, il cherche la faille
        elif btn_obj:
            reponse = architecte.objection(obs_id)
        elif btn_hyp:
            reponse = architecte.hypothese(obs_id)
        elif btn_def:
            reponse, verrou = architecte.defense()
            st.session_state["verrou"] = verrou
        if reponse is not None:
            st.session_state["derniere_reponse"] = reponse
            st.session_state["derniere_observation"] = interaction or None
            _sauver_graphe(st, g, chemin_auto)
            st.rerun()  # la colonne de gauche (verrou, figure) doit refléter l'état immédiatement

        if st.session_state["verrou"]:
            with st.form("refutation"):
                ref = st.text_area("✍️ Réfutation mathématique (obligatoire pour déverrouiller)", key="saisie_refutation",
                                   placeholder="Ex : en retirant la température, le test KS sur l'énergie donne p = 0.21...")
                if st.form_submit_button("🔓 Soumettre la réfutation") and ref.strip():
                    architecte.refutation(ref.strip())
                    st.session_state["verrou"] = False
                    st.session_state["derniere_observation"] = ref.strip()
                    st.session_state["derniere_reponse"] = "🤖 *Réfutation consignée. L'Architecte libère l'écran et retourne à ses matrices.*"
                    _sauver_graphe(st, g, chemin_auto)
                    st.rerun()

        st.markdown("---")
        st.write("#### 💬 Dernière réplique")
        if st.session_state["derniere_observation"]:
            st.info(f"👨‍🔬 **{physicien} :** {st.session_state['derniere_observation']}")
        st.write(st.session_state["derniere_reponse"] or Architecte.attente())

        with st.expander("📜 Historique du débat (chronologie du graphe)", expanded=False):
            for n in g.chronologie():
                if n["type"] in ("observation", "objection", "hypothese", "defense", "refutation"):
                    st.markdown(f"**{n['horodatage']} · {n['type']}**  \n{n['texte']}")
                    liens = [f"{rel} → {autre}" for rel, autre, sens in g.voisins(n["id"]) if sens == "sortante"]
                    if liens:
                        st.caption(" · ".join(liens))

    st.markdown("---")
    st.write("### 🕸️ Graphe de connaissances des débats")
    st.caption(" · ".join(f"{k}: {v}" for k, v in g.statistiques().items() if v))
    fig_g = _figure_graphe(g)
    if fig_g is not None:
        st.plotly_chart(fig_g, width="stretch")

    st.markdown("---")
    st.write("### 📋 Registre des événements isolés par l'IA")
    st.dataframe(anomalies[list(choisies) + ["Score_anomalie"]].sort_values(by="Score_anomalie", ascending=False), width="stretch")
    with st.expander("🔬 Diagnostic quantitatif complet (ce que lit l'Architecte)"):
        st.json({k: v for k, v in diag.items() if k != "variables"})
        st.dataframe(pd.DataFrame(diag["variables"]).T if diag.get("variables") else pd.DataFrame())


def _charger_cache(st, octets: bytes, nom: str, arbre: Optional[str], max_ev: Optional[int]):
    @st.cache_data(show_spinner="Lecture de la matrice…")
    def _lire(octets_: bytes, nom_: str, arbre_: Optional[str], max_ev_: Optional[int]):
        return analyser_fichier_physique(octets_, nom_, arbre_, max_ev_)

    return _lire(octets, nom, arbre, max_ev)


if __name__ == "__main__":
    lancer_interface()
