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
import sys
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

RACINE_OUTIL = os.path.dirname(os.path.abspath(__file__))
if RACINE_OUTIL not in sys.path:
    sys.path.insert(0, RACINE_OUTIL)


def lire_version_outil() -> str:
    """Numéro de version publié (fichier VERSION à côté de ce script)."""
    try:
        with open(os.path.join(RACINE_OUTIL, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "inconnue"
    except OSError:
        return "inconnue"


VERSION_OUTIL = lire_version_outil()

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
    df.columns = [str(c).strip() for c in df.columns]  # « px1  » (espace parasite) devient « px1 »
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
    matrice, derivees = grandeurs_derivees(matrice)
    rapport.update({"fichier": nom_fichier, "format": format_, "arbre": arbre, "derivees": derivees,
                    "n_variables": int(matrice.shape[1])})
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


MOTIFS_IDENTIFIANTS = [r"^run$", r"^event$", r"^evt$", r"^id$", r"^index$", r"^idx$", r"^numero$", r"^num$", r"^entry$",
                       r"^lumi", r"_id$", r"^n_?evt", r"^event_?number$", r"^run_?number$"]


def est_identifiant(colonne: str) -> bool:
    """Numéro de run, d'événement, index… : une étiquette, pas une grandeur physique."""
    return _mot_cle(colonne, MOTIFS_IDENTIFIANTS)


MOTIFS_MASSE = ("mass", "minv", "m_inv", "invmass")
PRIORITE_PHYSIQUE = (("masse", ()), ("pt", ("pt",)), ("energie", ("energ", r"^e\d*$")),
                     ("impulsion", (r"^p[xyz]?\d*$", "momentum")), ("temps", ("time", "temps")))


def est_masse(colonne: str) -> bool:
    nom = colonne.lower()
    return nom in ("m", "m1", "m2", "mll", "mjj", "mmumu", "mee") or any(m in nom for m in MOTIFS_MASSE) or nom.startswith("m_")


def grandeurs_derivees(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Ajoute la masse invariante d'une paire quand (E, px, py, pz) des deux objets sont présents et qu'aucune masse ne l'est.

    M² = (E1+E2)² − (px1+px2)² − (py1+py2)² − (pz1+pz2)² (relativité restreinte, unités du fichier).
    La colonne ajoutée s'appelle M_paire ; les valeurs non physiques (M² < 0, bruit de mesure) sont mises à 0.
    """
    ajoutees: List[str] = []
    if any(est_masse(c) for c in df.columns):
        return df, ajoutees
    quad = [f"{c}1" for c in ("E", "px", "py", "pz")] + [f"{c}2" for c in ("E", "px", "py", "pz")]
    cyl = [f"{c}1" for c in ("pt", "eta", "phi")] + [f"{c}2" for c in ("pt", "eta", "phi")]
    if all(c in df.columns for c in quad):
        E = df["E1"] + df["E2"]
        p2 = (df["px1"] + df["px2"]) ** 2 + (df["py1"] + df["py2"]) ** 2 + (df["pz1"] + df["pz2"]) ** 2
        df = df.copy()
        df["M_paire"] = np.sqrt(np.clip(E ** 2 - p2, 0.0, None))
        ajoutees.append("M_paire")
    elif all(c in df.columns for c in cyl):
        # Masses des objets négligées devant leur impulsion (approximation ultra-relativiste) :
        # M² = 2 pt1 pt2 (cosh(η1−η2) − cos(φ1−φ2)).
        df = df.copy()
        m2 = 2.0 * df["pt1"] * df["pt2"] * (np.cosh(df["eta1"] - df["eta2"]) - np.cos(df["phi1"] - df["phi2"]))
        df["M_paire"] = np.sqrt(np.clip(m2, 0.0, None))
        ajoutees.append("M_paire")
    return df, ajoutees


def _rang_physique(colonne: str) -> int:
    nom = colonne.lower()
    if est_masse(nom):
        return 0
    for rang, (_, motifs) in enumerate(PRIORITE_PHYSIQUE[1:], start=1):
        for m in motifs:
            if (m.startswith("^") and re.match(m, nom)) or (not m.startswith("^") and m in nom):
                return rang
    if nom.startswith("q") or "charge" in nom or nom.startswith("type"):
        return 9
    return 5


def colonnes_analysables(colonnes: Sequence[str]) -> List[str]:
    """Colonnes proposées par défaut à la détection : les grandeurs physiques, sans les identifiants.

    Ordre : masses d'abord, puis impulsions transverses, énergies, impulsions,
    temps, le reste, et en dernier charges et types (tri stable : l'ordre du
    fichier est conservé à rang égal). Avec « 8 premières » par défaut, une masse
    invariante n'est ainsi jamais laissée de côté.
    """
    physiques = sorted(colonnes_physiques(colonnes), key=_rang_physique)
    return physiques or list(colonnes)


def colonnes_physiques(colonnes: Sequence[str]) -> List[str]:
    """Les grandeurs physiques dans l'ordre du fichier (sans les identifiants), sans tri."""
    return [c for c in colonnes if not est_identifiant(c)]


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
        "correlations_conformes": {},
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

    # Corrélations internes aux anomalies (chercher un biais instrumental caché),
    # et les mêmes chez les conformes : une corrélation présente des deux côtés est
    # une propriété des données (cinématique), pas un biais propre aux anomalies.
    if len(colonnes) >= 2:
        corr = ano[colonnes].corr().fillna(0.0)
        corr_ok = ok[colonnes].corr().fillna(0.0)
        for i, c1 in enumerate(colonnes):
            for c2 in colonnes[i + 1:]:
                diag["correlations_anomalies"][f"{c1} ↔ {c2}"] = float(corr.loc[c1, c2])
                diag["correlations_conformes"][f"{c1} ↔ {c2}"] = float(corr_ok.loc[c1, c2])

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


SEUIL_CORR_BIAIS = 0.5   # corrélation interne aux anomalies jugée forte
SEUIL_EXCES_CORR = 0.3   # excès minimal de corrélation (isolés − conformes) pour parler de biais


def correlations_fortes(diag: Dict[str, Any], variable: str, seuil: float = SEUIL_CORR_BIAIS,
                        exces: float = SEUIL_EXCES_CORR, connues: Optional[Iterable[frozenset]] = None) -> List[Dict[str, Any]]:
    """Corrélations fortes impliquant `variable` chez les isolés, qualifiées par comparaison aux conformes.

    - « structurelle » : aussi présente chez les conformes (ou sans excès notable) :
      une propriété des données (par exemple impulsion ↔ énergie d'une même
      particule), pas un biais des anomalies ;
    - « suspecte » : n'apparaît (ou ne se renforce nettement) que chez les isolés :
      un effet d'appareillage n'est pas exclu ;
    - « connue » : la paire figure dans les relations connues de l'outil (apprises
      des données par le physicien robot, ou déclarées par le physicien).
    Triées de la plus forte à la plus faible corrélation chez les isolés.
    """
    resultats = []
    conformes = diag.get("correlations_conformes", {})
    connues = set(connues or ())
    for paire, r in diag.get("correlations_anomalies", {}).items():
        gauche, droite = [x.strip() for x in paire.split("↔")]
        if variable not in (gauche, droite) or abs(r) < seuil:
            continue
        autre = droite if gauche == variable else gauche
        r_ok = float(conformes.get(paire, 0.0))
        structurelle = abs(r_ok) >= seuil or (abs(r) - abs(r_ok)) < exces
        if frozenset((variable, autre)) in connues:
            nature = "connue"
        else:
            nature = "structurelle" if structurelle else "suspecte"
        resultats.append({"autre": autre, "r_isoles": float(r), "r_conformes": r_ok, "nature": nature,
                          "thermique": diag.get("roles", {}).get("temperature") == autre})
    return sorted(resultats, key=lambda x: -abs(x["r_isoles"]))


# =============================================================================
# 4. GRAPHE DE CONNAISSANCES PERSISTANT
# =============================================================================

TYPES_NOEUDS = ("jeu_de_donnees", "anomalies", "observation", "objection", "hypothese", "defense", "refutation", "parametres",
                "campagne", "verdict")


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
    SEUIL_CORR_BIAIS = SEUIL_CORR_BIAIS  # corrélation interne aux anomalies jugée forte
    SEUIL_EXCES_CORR = SEUIL_EXCES_CORR  # excès (isolés − conformes) minimal pour parler de biais

    def __init__(self, graphe: GrapheConnaissances, diag: Dict[str, Any], physicien: str = "collègue",
                 paires_connues: Optional[Iterable[frozenset]] = None):
        self.g = graphe
        self.diag = diag
        self.physicien = physicien
        self.paires_connues = set(paires_connues or ())  # relations enseignées à l'outil : jamais accusées

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
            fortes = correlations_fortes(d, dom, self.SEUIL_CORR_BIAIS, self.SEUIL_EXCES_CORR, self.paires_connues)
            suspectes = [c for c in fortes if c["nature"] == "suspecte"]
            structurelles = [c for c in fortes if c["nature"] == "structurelle"]
            connues = [c for c in fortes if c["nature"] == "connue"]
            if suspectes:
                c = suspectes[0]
                lignes.append(
                    f"Or, au sein même des anomalies, **{dom}** est corrélée à **{c['autre']}** "
                    f"(r = {_fmt(c['r_isoles'])} chez les isolés contre {_fmt(c['r_conformes'])} chez les conformes) : "
                    "cette dépendance n'existe que dans ton lot isolé. "
                    + ("Ce que tu prends pour un signal physique pourrait être un effet **thermique instrumental** du capteur. "
                       if c["thermique"] else "Un effet de l'appareillage n'est pas exclu. ")
                    + f"Prouve-moi le contraire en retirant **{c['autre']}** des variables et en vérifiant que l'isolement persiste."
                )
            elif connues:
                c = connues[0]
                lignes.append(
                    f"**{dom}** est corrélée à **{c['autre']}** (r = {_fmt(c['r_isoles'])}), mais cette relation m'a été "
                    "enseignée comme connue : je ne l'invoquerai pas contre toi, et je ne te crois pas pour autant."
                )
            elif structurelles:
                c = structurelles[0]
                lignes.append(
                    f"**{dom}** est corrélée à **{c['autre']}** chez les isolés (r = {_fmt(c['r_isoles'])}), mais aussi chez "
                    f"les conformes (r = {_fmt(c['r_conformes'])}) : c'est une propriété de tes données, pas un biais propre "
                    "aux anomalies. Je ne l'invoquerai pas contre toi, mais je ne te crois pas pour autant."
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
    # Une section (données ouvertes, campagne) a demandé l'ouverture d'un fichier : on règle
    # la barre latérale AVANT que ses widgets ne soient instanciés (Streamlit l'interdit après).
    chemin = st.session_state.pop("ouverture_demandee", None)
    if chemin:
        st.session_state["mode_source"] = "Chemin local"
        st.session_state["chemin_local"] = chemin
    mode = st.session_state.pop("mode_demande", None)
    if mode:
        st.session_state["mode_source"] = mode
    niveau = st.session_state.pop("niveau_demande", None)
    if niveau:
        st.session_state["niveau"] = niveau


def _demander_ouverture(st, chemin: str) -> None:
    """Ouvre `chemin` dans la vue interactive au prochain passage (voir _init_session)."""
    st.session_state["ouverture_demandee"] = os.path.abspath(chemin)
    st.rerun()


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
    "campagne": "#16a085", "verdict": "#d35400",
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
            marker=dict(size=16, color=COULEURS_NOEUDS.get(type_, "#7f8c8d")),
        ))
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0), height=420, xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def lancer_interface() -> None:  # pragma: no cover - interface graphique
    import streamlit as st

    st.set_page_config(layout="wide", page_title="A.N.E.M.O.N.E & L'Architecte")
    _init_session(st)
    connaissances = _charger_connaissances(st)
    st.title("🌌 Projet A.N.E.M.O.N.E — Hub de Co-Recherche")
    st.subheader("Système d'Analyse Subatomique & Robot Architecte Cognitif")
    st.markdown("---")

    # ------------------------------------------------------------------ barre latérale
    with st.sidebar:
        st.session_state.setdefault("niveau", NIVEAUX_INTERFACE[1])
        niveau = st.radio("Niveau", NIVEAUX_INTERFACE, key="niveau",
                          help="Découverte guidée : le résultat est lu en langage courant, les réglages techniques sont repliés. "
                               "Expert : tous les réglages et le bureau de l'Architecte.")
        guide = niveau.startswith("🧭")
        st.header("📂 Source des données")
        # Nom pré-rempli via la variable d'environnement ANEMONE_PHYSICIEN (aucun nom en dur).
        physicien = st.text_input("Nom du physicien" if not guide else "Votre nom",
                                  value=os.environ.get("ANEMONE_PHYSICIEN", ""),
                                  placeholder="Votre nom (consigné dans le graphe)")

        def _radio_albert():
            return st.radio("Travailler", ["🤝 Avec Albert (autonome et collaboratif)", "👤 Fred seul avec l'Architecte"],
                            key="mode_albert", horizontal=False,
                            help="Avec Albert : le physicien robot apprend des données, débat, cherche seul et enseigne à l'outil. "
                                 "Seul : Albert n'agit pas et l'Architecte n'utilise que ce que vous avez vous-même déclaré.")

        mode_albert = _radio_albert() if not guide else None
        mode_source = st.radio("Mode", ["Fichier téléversé (.root / .csv)", "Chemin local", "Démo synthétique (aucune valeur physique)"],
                               key="mode_source")
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
                chemin = st.text_input("Chemin du fichier", placeholder="/data/run_1234.root", key="chemin_local")
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

        matrice_complete, masques_aveugle = matrice, []
        if matrice is not None:
            try:
                import anemone_aveugle as av
                matrice, masques_aveugle = av.masquer(matrice, av.scelles())
            except Exception as exc:  # pragma: no cover - dépend du disque
                st.warning(f"Protocoles à l'aveugle illisibles : {exc}")
            if masques_aveugle:
                st.caption("🙈 " + " ; ".join(f"{m['n_masques']} événements masqués ({m['variable']} dans [{m['bas']:g}, {m['haut']:g}), "
                                              f"protocole {m['protocole']})" for m in masques_aveugle))

        st.header("🧠 Détection de l'inconnu")
        colonnes = list(matrice.columns) if matrice is not None else []
        choisies = st.multiselect("Variables analysées", colonnes, default=colonnes_analysables(colonnes)[:8],
                                  help="Les identifiants (Run, Event…) sont écartés par défaut.") if colonnes else []
        zone = st.expander("⚙️ Réglages avancés (mode expert)", expanded=False) if guide else st.container()
        with zone:
            if guide:
                mode_albert = _radio_albert()
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

            st.markdown("---")
            st.caption(f"A.N.E.M.O.N.E version {VERSION_OUTIL} · mise à jour proposée au lancement")
            with st.expander("🩺 Diagnostic (à envoyer en cas de problème)", expanded=False):
                try:
                    from outils.diagnostic import rapport_diagnostic
                    texte_diag = rapport_diagnostic()
                except Exception as exc:  # pragma: no cover - dépend de l'installation
                    texte_diag = f"Diagnostic indisponible : {exc}"
                st.code(texte_diag, language="text")
                st.download_button("📋 Télécharger le rapport", texte_diag, file_name="diagnostic_anemone.txt", mime="text/plain")
        avec_albert = mode_albert.startswith("🤝")

    def _sections_sources(ouvertes: bool) -> None:
        with st.expander("🌐 Données réelles en un clic — CERN Open Data", expanded=ouvertes):
            _section_donnees_ouvertes(st)
        with st.expander("🧪 Campagne automatique — l'outil analyse seul un dossier de runs", expanded=ouvertes):
            _section_campagne(st, physicien, float(contamination), int(seed), max_ev, chemin_auto,
                              connaissances.paires_connues(sans_albert=not avec_albert) if connaissances else set())

    def _section_albert_si_actif() -> None:
        if avec_albert:
            with st.expander("🧑‍🔬 Albert, physicien robot — il apprend, débat, cherche seul et enseigne à l'outil", expanded=False):
                _section_albert(st, connaissances, matrice, choisies, rapport, float(contamination), int(seed), max_ev, chemin_auto, physicien)

    # ------------------------------------------------------------------ rien de chargé : démarrage en un clic
    chemin_charge = st.session_state.get("chemin_local", "") if str(st.session_state.get("mode_source", "")).startswith("Chemin") else ""

    if matrice is None:
        _section_demarrage(st, guide)
        with st.expander("🏁 Run de découverte — de l'hypothèse à la thèse, en un clic", expanded=True):
            _section_decouverte(st, None, None, physicien, chemin_auto, max_ev)
        with st.expander("🙈 Analyse à l'aveugle — sceller le protocole avant de regarder", expanded=False):
            _section_aveugle(st, None, None, physicien, chemin_auto, "")
        _sections_sources(ouvertes=False)
        _section_albert_si_actif()
        st.stop()
    if not choisies:
        st.warning("Aucune variable sélectionnée : choisis au moins une variable dans « Variables analysées » (barre latérale).")
        _section_albert_si_actif()
        _sections_sources(ouvertes=False)
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

    paires_connues = connaissances.paires_connues(sans_albert=not avec_albert) if connaissances else set()
    architecte = Architecte(g, diag, physicien=physicien.split(" ")[0] if physicien else "collègue", paires_connues=paires_connues)

    if rapport["format"] == "demo":
        st.warning("⚠️ Données SYNTHÉTIQUES de démonstration : aucune conclusion physique n'en découle.")
    if guide:
        st.info("🧭 **Découverte guidée** : à gauche, chaque point est un événement (vert : ordinaire ; chaud : isolé). "
                "À droite, ce que l'outil a trouvé, en langage courant. Les calculs complets sont en mode Expert (barre latérale).")
    if masques_aveugle:
        st.warning("🙈 **Analyse à l'aveugle en cours** : " + " ; ".join(
            f"{m['n_masques']} événements avec {m['variable']} dans [{m['bas']:g}, {m['haut']:g}) sont masqués partout "
            f"(protocole {m['protocole']})" for m in masques_aveugle) + ". Ils ne réapparaîtront qu'en levant l'aveugle.")

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
        _section_evenement(st, matrice, resultat, guide)

    montrer_bureau = True
    if guide:
        with col_droite:
            _section_guidee(st, diag, rapport, paires_connues)
            montrer_bureau = st.checkbox("Voir le bureau de l'Architecte (débat technique)", key="guide_bureau")
    if montrer_bureau:
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
                    paire_suspecte = next((c for c in correlations_fortes(diag, variable_dominante(diag) or "", connues=paires_connues)
                                           if c["nature"] == "suspecte"), None) if variable_dominante(diag) else None
                    declarer = st.checkbox(
                        f"Enseigner à l'outil : {variable_dominante(diag)} ↔ {paire_suspecte['autre']} est une relation connue",
                        key="declarer_relation") if paire_suspecte and connaissances else False
                    if st.form_submit_button("🔓 Soumettre la réfutation") and ref.strip():
                        if declarer and paire_suspecte:
                            connaissances.ajouter_relation([variable_dominante(diag), paire_suspecte["autre"]], "declaree",
                                                           f"déclarée par {physicien or 'le physicien'} : {ref.strip()[:120]}",
                                                           physicien or "physicien", rapport.get("fichier"))
                            _sauver_connaissances(st, connaissances)
                        architecte.refutation(ref.strip())
                        st.session_state["verrou"] = False
                        st.session_state["derniere_observation"] = ref.strip()
                        st.session_state["derniere_reponse"] = "🤖 *Réfutation consignée. L'Architecte libère l'écran et retourne à ses matrices.*"
                        _sauver_graphe(st, g, chemin_auto)
                        st.rerun()

            st.markdown("---")
            st.write("#### 💬 Dernière réplique")
            if st.session_state["derniere_observation"]:
                st.info(f"👨‍🔬 **{physicien or 'Physicien'} :** {st.session_state['derniere_observation']}")
            st.write(st.session_state["derniere_reponse"] or Architecte.attente())

            with st.expander("📜 Historique du débat (chronologie du graphe)", expanded=False):
                for n in g.chronologie():
                    if n["type"] in ("observation", "objection", "hypothese", "defense", "refutation"):
                        st.markdown(f"**{n['horodatage']} · {n['type']}**  \n{n['texte']}")
                        liens = [f"{rel} → {autre}" for rel, autre, sens in g.voisins(n["id"]) if sens == "sortante"]
                        if liens:
                            st.caption(" · ".join(liens))

    with st.expander("🏁 Run de découverte — de l'hypothèse à la thèse, en un clic", expanded=False):
        _section_decouverte(st, matrice, rapport, physicien, chemin_auto, max_ev)
    with st.expander("🙈 Analyse à l'aveugle — sceller le protocole avant de regarder", expanded=bool(masques_aveugle)):
        _section_aveugle(st, matrice_complete, rapport, physicien, chemin_auto, chemin_charge)
    _section_albert_si_actif()
    _sections_sources(ouvertes=False)

    st.markdown("---")
    with (st.expander("🕸️ Graphe de connaissances des débats (mode expert)", expanded=False) if guide else st.container()):
        if not guide:
            st.write("### 🕸️ Graphe de connaissances des débats")
        st.caption(" · ".join(f"{k}: {v}" for k, v in g.statistiques().items() if v))
        fig_g = _figure_graphe(g)
        if fig_g is not None:
            st.plotly_chart(fig_g, width="stretch")

    st.markdown("---")
    with (st.expander("📋 Tableau des événements isolés", expanded=False) if guide else st.container()):
        if not guide:
            st.write("### 📋 Registre des événements isolés par l'IA")
        st.dataframe(anomalies[list(choisies) + ["Score_anomalie"]].sort_values(by="Score_anomalie", ascending=False), width="stretch")
    with st.expander("🔬 Diagnostic quantitatif complet (ce que lit l'Architecte)"):
        st.json({k: v for k, v in diag.items() if k != "variables"})
        st.dataframe(pd.DataFrame(diag["variables"]).T if diag.get("variables") else pd.DataFrame())


def _section_decouverte(st, matrice, rapport, physicien: str, chemin_auto: Optional[str], max_ev: Optional[int]) -> None:  # pragma: no cover - interface graphique
    """Run de découverte : hypothèse facultative, données au choix, un bouton, une thèse soumise au physicien."""
    import anemone_decouverte as ad
    from outils import donnees_ouvertes as do

    st.caption("Donne une hypothèse (ou laisse l'outil chercher), choisis les données, lance. L'outil chasse les bosses "
               "sur les masses (présentes ou calculées), cherche pour chacune les autres explications (fluctuation, épisode, "
               "découpage, bord, référence, résonance déjà connue), teste ton hypothèse à l'endroit indiqué, puis écrit une "
               "thèse dans `theses/` : un dossier de calculs, à valider par un physicien.")
    hypothese = st.text_input("Hypothèse (facultative)", key="run_hypothese",
                              placeholder="ex. : M_paire ~ 91 ± 3, ou « je pense à une résonance vers 42 GeV dans M »",
                              help="Forme localisée reconnue : VARIABLE ~ VALEUR ± LARGEUR. Sinon, texte libre consigné dans la thèse.")
    options = []
    if matrice is not None:
        options.append("Fichier chargé")
    dossier_campagne = st.session_state.get("campagne_dossier", "")
    if dossier_campagne:
        options.append(f"Dossier de la campagne ({dossier_campagne})")
    options.append("Toutes les données réelles du CERN (téléchargement automatique, ~80 Mo)")
    if st.session_state.get("run_source_options") != options:     # les choix ont changé (fichier chargé…) : premier choix par défaut
        st.session_state.pop("run_source", None)
        st.session_state["run_source_options"] = options
    source = st.radio("Données du run", options, key="run_source", horizontal=False)
    reference = st.session_state.get("campagne_reference", "") or None
    st.caption(f"Run de référence : `{reference}`" if reference else
               "Aucun run de référence (renseigne-le dans la campagne pour l'épreuve « absente de la référence »).")
    if st.button("🏁 Lancer le run de découverte", key="run_lancer", type="primary"):
        etat = st.empty()
        try:
            if source.startswith("Fichier"):
                chemin_charge = st.session_state.get("chemin_local", "") if st.session_state.get("mode_source", "").startswith("Chemin") else ""
                if chemin_charge and os.path.isfile(chemin_charge):
                    cibles = [chemin_charge]
                else:                                            # fichier téléversé ou démo : on l'écrit tel quel pour le run
                    dossier_tmp = os.path.join(tempfile.gettempdir(), "anemone_run")
                    os.makedirs(dossier_tmp, exist_ok=True)
                    nom = os.path.splitext(os.path.basename((rapport or {}).get("fichier", "matrice")))[0] + ".csv"
                    chemin_tmp = os.path.join(dossier_tmp, nom.replace(" ", "_"))
                    matrice.to_csv(chemin_tmp, index=False)
                    cibles = [chemin_tmp]
            elif source.startswith("Dossier"):
                cibles = ad.lister_fichiers([dossier_campagne])
            else:
                # tranches du fichier 2010 complet exclues : le fichier complet les contient déjà
                entrees = [e for e in do.catalogue(en_ligne=False) if not e.nom.startswith("MuRun2010B_")]
                cibles = []
                for i, e in enumerate(entrees):
                    etat.info(f"Téléchargement {i + 1}/{len(entrees)} : {e.nom}")
                    cibles.append(do.telecharger(e, do.DOSSIER_DEFAUT))
            if not cibles:
                st.error("Aucun fichier à analyser.")
                return
            with st.spinner("Run de découverte en cours…"):
                run = ad.lancer_run(cibles, ad.analyser_hypothese(hypothese), reference, max_ev,
                                    rappel=lambda m: etat.info(m))
            chemin_these = ad.ecrire_these(run)
            etat.empty()
            st.session_state["run_decouverte"] = {"run": run.to_dict(), "these": chemin_these, "texte": ad.rediger_these(run)}
            g = _graphe(st)
            g.ajouter_noeud("verdict", f"Run de découverte : {run.resume}",
                            {"conclusion": run.conclusion, "these": chemin_these, "hypothese": run.hypothese,
                             "physicien": physicien or "", "fichiers": [f.get("fichier") for f in run.fichiers]})
            _sauver_graphe(st, g, chemin_auto)
        except Exception as exc:
            etat.empty()
            st.error(f"Run impossible : {exc}")
            return
    resultat = st.session_state.get("run_decouverte")
    if not resultat:
        return
    run = resultat["run"]
    boite = {"these": st.error, "connue": st.success, "indice": st.warning, "rien": st.info}[run["conclusion"]]
    boite(("🔴 " if run["conclusion"] == "these" else "") + run["resume"])
    if run["tests_hypothese"]:
        st.write("**Test de l'hypothèse**")
        for t in run["tests_hypothese"]:
            st.markdown(f"- `{t['fichier']}`, `{t['variable']}` : {t['detail']}")
    if run["candidats"]:
        etiquettes = {"these": "🔴 THÈSE", "connue": "🟢 connue", "indice": "🟠 indice", "structure": "🟡 structure", "ecarte": "⚪ écartée"}
        st.dataframe(pd.DataFrame([{
            "Verdict": etiquettes[c["verdict"]], "Fichier": c["fichier"], "Variable": c["bosse"]["variable"],
            "Position": round(c["bosse"]["centre"], 4), "Observés": c["bosse"]["observe"], "Attendus": round(c["bosse"]["attendu"], 1),
            "p globale": f"{c['bosse']['p_global']:.2g}", "Coïncide avec": c["connue"] or "", "Raison": c["raisons"][0],
        } for c in run["candidats"]]), width="stretch", hide_index=True)
    st.caption(f"Thèse écrite : `{resultat['these']}` (Markdown + JSON, empreintes des fichiers, versions).")
    st.download_button("📄 Télécharger la thèse (Markdown)", resultat["texte"], file_name=os.path.basename(resultat["these"]),
                       mime="text/markdown", key="run_telecharger")
    with st.expander("📜 Thèse complète", expanded=run["conclusion"] == "these"):
        st.markdown(resultat["texte"])


def _section_evenement(st, matrice, resultat, guide: bool) -> None:  # pragma: no cover - interface graphique
    """Vidéo d'un événement de collision : trajectoires des particules mesurées, animées depuis le vertex."""
    import anemone_evenement as ae

    st.write("### 🎥 Événement de collision — trajectoires (vidéo)")
    if not ae.peut_afficher(list(matrice.columns)):
        st.caption("Ce fichier ne décrit pas les impulsions des particules (px, py, pz ou pt, η, φ) : pas de trajectoires "
                   "à tracer. Avec un fichier du CERN (dimuons, Z, W…), la vidéo de chaque événement apparaît ici.")
        return
    sources = ["Isolés (score le plus fort d'abord)", "Tous les événements"]
    run = (st.session_state.get("run_decouverte") or {}).get("run")
    bosses = [c for c in (run or {}).get("candidats", []) if c["verdict"] in ("these", "connue", "indice")
              and c["bosse"]["variable"] in matrice.columns] if run else []
    if bosses:
        sources.insert(1, "Événements d'une bosse du run de découverte")
    c1, c2 = st.columns([2, 3])
    source = c1.radio("Choisir parmi", sources, key="evt_source")
    if source.startswith("Isolés"):
        candidats = resultat[resultat["Inconnu"] == -1].sort_values("Score_anomalie", ascending=False)
        etiquette = "isolé"
    elif source.startswith("Événements d'une bosse"):
        choix = c2.selectbox("Bosse", [f"{c['fichier']} : {c['bosse']['variable']} ≈ {c['bosse']['centre']:.4g}" +
                                        (f" ({c['connue'].split(' (')[0]})" if c["connue"] else "") for c in bosses], key="evt_bosse")
        b = bosses[[f"{c['fichier']} : {c['bosse']['variable']} ≈ {c['bosse']['centre']:.4g}" +
                    (f" ({c['connue'].split(' (')[0]})" if c["connue"] else "") for c in bosses].index(choix)]["bosse"]
        candidats = ae.evenements_dans_fenetre(matrice, b["variable"], b["bord_bas"], b["bord_haut"])
        etiquette = f"{b['variable']} dans [{b['bord_bas']:.4g}, {b['bord_haut']:.4g}]"
    else:
        candidats = matrice
        etiquette = "événement"
    if len(candidats) == 0:
        st.info("Aucun événement dans cette sélection.")
        return
    n = int(c2.number_input(f"Événement (1 à {len(candidats)}, {etiquette})", min_value=1, max_value=int(len(candidats)),
                            value=1, step=1, key="evt_numero"))
    ligne = candidats.iloc[n - 1]
    index = candidats.index[n - 1]
    parts = ae.particules(ligne)
    infos = " · ".join(p.description() for p in parts)
    masse = next((f"{c} = {float(ligne[c]):.4g}" for c in matrice.columns if est_masse(c) or c == "M_paire"), "")
    st.caption(f"Ligne {index} du fichier{' · ' + masse if masse else ''} · {infos}")
    st.plotly_chart(ae.figure_evenement(ligne, titre=None), width="stretch", key=f"evt_fig_{index}")
    if guide:
        st.caption("Les particules partent du point de collision (orange). Une particule chargée s'enroule dans le champ "
                   "magnétique ; plus elle est rapide, plus sa trajectoire est droite. Les cylindres sont un schéma du "
                   "détecteur : trajectographe, calorimètres, chambres à muons. Appuie sur ▶ pour voir l'événement se dérouler.")
    else:
        st.caption(f"Hélices dans B = {ae.CHAMP_TESLA} T (R = pt / 0,3 B), ligne droite si la charge est inconnue ; schéma de "
                   "détecteur aux dimensions approximatives de CMS, sans simulation. Trajectoires calculées depuis les seules impulsions mesurées.")


def _section_aveugle(st, matrice_complete, rapport, physicien: str, chemin_auto: Optional[str], chemin_charge: str) -> None:  # pragma: no cover - interface graphique
    """Sceller un protocole (variable, fenêtre, hypothèse, données engagées), voir le fond attendu, lever l'aveugle une seule fois."""
    import anemone_aveugle as av

    st.caption("On décide de tout avant de regarder la région du signal : variable, fenêtre, hypothèse, données. Le protocole "
               "est scellé (empreinte, date) et la fenêtre est masquée dans tout l'outil. Seul le fond attendu y est consultable. "
               "Lever l'aveugle est un acte unique : un seul test, à l'endroit scellé, sans facteur d'essais, au seuil de 5 σ. "
               "Le résultat est écrit dans `theses/protocoles/` et ne peut plus être refait.")
    colonnes = [c for c in matrice_complete.columns if np.issubdtype(matrice_complete[c].dtype, np.number)] if matrice_complete is not None else []
    with st.form("aveugle_sceller_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([2, 1, 1])
        if colonnes:
            defaut = next((i for i, c in enumerate(colonnes) if est_masse(c) or c == "M_paire"), 0)
            variable = c1.selectbox("Variable", colonnes, index=defaut, key="aveugle_variable")
        else:
            variable = c1.text_input("Variable", key="aveugle_variable", placeholder="M_paire")
        bas = c2.number_input("Fenêtre : bas", value=0.0, format="%.4f", key="aveugle_bas")
        haut = c3.number_input("Fenêtre : haut", value=0.0, format="%.4f", key="aveugle_haut")
        hypothese = st.text_input("Hypothèse scellée", key="aveugle_hypothese", placeholder="ex. : résonance vers 42 GeV dans M_paire")
        engager = st.checkbox(f"Engager le fichier chargé ({os.path.basename(chemin_charge)})" if chemin_charge else
                              "Engager les runs à venir (aucun fichier local chargé par chemin)", value=bool(chemin_charge),
                              key=f"aveugle_engager_{'fichier' if chemin_charge else 'aucun'}")
        sceller = st.form_submit_button("🔒 Sceller le protocole", type="primary")
    if sceller:
        try:
            if not variable:
                raise ValueError("indique une variable")
            p = av.sceller(variable, float(bas), float(haut), hypothese, physicien,
                           [chemin_charge] if (engager and chemin_charge) else [],
                           dossier=st.session_state.get("campagne_dossier") or None)
        except Exception as exc:
            st.error(f"Scellement impossible : {exc}")
        else:
            g = _graphe(st)
            g.ajouter_noeud("hypothese", f"Protocole à l'aveugle {p.identifiant} : {variable} dans [{bas:g}, {haut:g}) — {hypothese or 'sans texte'}",
                            {"protocole": p.identifiant, "empreinte": p.empreinte, "auteur": physicien or ""})
            _sauver_graphe(st, g, chemin_auto)
            st.success(f"Protocole {p.identifiant} scellé (empreinte {p.empreinte[:12]}…). La fenêtre est maintenant masquée.")
            st.rerun()
    protocoles = av.lister()
    if not protocoles:
        st.caption("Aucun protocole pour l'instant.")
        return
    st.write("**Protocoles**")
    for p in protocoles:
        etat = "🔒 scellé" if p.etat == "scelle" else "🔓 levé"
        integrite = "" if av.integre(p) else " — ⚠️ ALTÉRÉ"
        st.markdown(f"- **{p.identifiant}** {etat}{integrite} · `{p.variable}` dans [{p.bas:g}, {p.haut:g}) · {p.hypothese or 'sans texte'}"
                    + (f" · {len(p.fichiers)} fichier(s) engagé(s)" if p.fichiers else ""))
        if p.etat == "scelle":
            if matrice_complete is not None and p.variable in matrice_complete.columns:
                fa = av.fond_attendu(p, matrice_complete)
                st.caption("   " + fa["detail"])
                c1, c2 = st.columns([3, 1])
                confirme = c1.checkbox("Je comprends que lever l'aveugle est irréversible et que le test sera unique",
                                       key=f"aveugle_confirme_{p.identifiant}")
                if c2.button("🔓 Lever l'aveugle", key=f"aveugle_lever_{p.identifiant}", disabled=not confirme):
                    try:
                        p = av.lever(p, matrice_complete, [chemin_charge] if chemin_charge else [])
                    except Exception as exc:
                        st.error(f"Refusé : {exc}")
                    else:
                        g = _graphe(st)
                        g.ajouter_noeud("verdict", f"Aveugle levé {p.identifiant} : {p.resultat['verdict']}",
                                        {"protocole": p.identifiant, "resultat": p.resultat, "auteur": physicien or ""})
                        _sauver_graphe(st, g, chemin_auto)
                        st.rerun()
            else:
                st.caption("   fond attendu : charge un fichier contenant cette variable pour le consulter ou lever l'aveugle.")
        else:
            r = p.resultat or {}
            boite = st.error if r.get("decouverte") else st.info
            boite(f"{r.get('verdict')} — " + (f"{r.get('observe')} observés pour {r.get('attendu'):.1f} attendus, p = {r.get('p_local'):.2g}"
                                                if r.get("testable") else "non testable"))
            with st.expander(f"Protocole {p.identifiant} complet", expanded=False):
                st.markdown(av.rediger(p))


def _section_guidee(st, diag, rapport, paires_connues) -> None:  # pragma: no cover - interface graphique
    """Lecture en langage courant du résultat (mode découverte guidée), calculée par anemone_guide."""
    import anemone_guide as ag

    lecture = ag.lecture_guidee(diag, rapport, paires_connues)
    st.write("### 🧭 Ce que l'outil a trouvé")
    for phrase in lecture["resume"]:
        st.markdown(phrase)
    st.write("#### Niveau de preuve")
    boite = {"insuffisant": st.info, "faible": st.info, "net": st.warning, "tres_net": st.error}[lecture["niveau"]]
    boite(f"{lecture['pastille']} {lecture['phrase_niveau']}")
    if lecture["chiffres"]:
        st.markdown("\n".join(f"- **{k}** : {v}" for k, v in lecture["chiffres"].items()))
    if lecture["vigilance"]:
        st.write("#### ⚠️ Points de vigilance")
        for v in lecture["vigilance"]:
            st.markdown(f"- {v}")
    st.write("#### Et maintenant ?")
    for e in lecture["et_maintenant"]:
        st.markdown(f"- {e}")
    with st.expander("📖 Les mots utilisés ici", expanded=False):
        for mot, definition in ag.GLOSSAIRE.items():
            st.markdown(f"**{mot}** : {definition}")


CHEMIN_EXEMPLE = os.path.join(RACINE_OUTIL, "exemples", "detecteur_demo.csv")
JEU_REEL_DEMARRAGE = "545/Zmumu.csv"  # le plus petit fichier réel du catalogue (candidats Z → μμ)


NIVEAUX_INTERFACE = ["🧭 Découverte guidée (sans jargon)", "🔬 Expert (tous les réglages)"]


def _section_demarrage(st, guide: bool = False) -> None:  # pragma: no cover - interface graphique
    """Premier écran : trois façons de voir la vue 4D et l'Architecte en un clic, sans passer par la barre latérale."""
    from outils import donnees_ouvertes as do

    st.write("### 🚀 Commencer")
    if guide:
        st.caption("Mode découverte guidée. Rien n'est chargé pour l'instant : choisis des données ci-dessous, l'outil "
                   "les analyse tout seul et t'explique ce qu'il trouve en langage courant.")
    else:
        st.caption("Rien n'est chargé pour l'instant : la vue 4D, l'Architecte et le registre apparaissent dès qu'un fichier "
                   "d'événements est ouvert. L'analyse (Isolation Forest) se lance alors d'elle-même, sans bouton.")
        if st.button("🧭 Je ne suis pas physicien : guide-moi", key="demarrage_guide",
                     help="Passe en mode découverte guidée : lecture en langage courant, réglages techniques repliés."):
            st.session_state["niveau_demande"] = NIVEAUX_INTERFACE[0]
            st.rerun()
    c1, c2, c3 = st.columns(3)
    exemple = c1.button("▶️ Analyser l'exemple livré", key="demarrage_exemple", type="primary",
                        help=f"{os.path.relpath(CHEMIN_EXEMPLE, RACINE_OUTIL)} : jeu synthétique livré avec l'outil, "
                             "sans valeur physique, pour voir l'outil fonctionner.")
    demo = c2.button("🎲 Démo synthétique", key="demarrage_demo",
                     help="Événements générés à la volée, avec des anomalies injectées : aucune valeur physique.")
    reel = c3.button("🌐 Ouvrir un fichier réel du CERN", key="demarrage_reel",
                     help=f"Télécharge {JEU_REEL_DEMARRAGE} (candidats Z → μμ, CMS 2011, ~1 Mo), vérifie sa somme "
                          "de contrôle, puis l'ouvre. Nécessite l'accès à opendata.cern.ch.")
    st.caption("Ton propre fichier (.root / .csv) : barre latérale à gauche (flèche » en haut à gauche si elle est repliée) "
               "→ « Upload » ou « Chemin local ». Un dossier entier : la campagne automatique ci-dessous.")
    if exemple:
        if not os.path.isfile(CHEMIN_EXEMPLE):
            st.error(f"Exemple introuvable : {CHEMIN_EXEMPLE}")
        else:
            _demander_ouverture(st, CHEMIN_EXEMPLE)
    if demo:
        st.session_state["mode_demande"] = "Démo synthétique (aucune valeur physique)"
        st.rerun()
    if reel:
        try:
            entree = do.trouver(JEU_REEL_DEMARRAGE)
            with st.spinner(f"Téléchargement de {entree.nom} ({entree.taille_mo:.1f} Mo)…"):
                chemin = do.telecharger(entree, do.DOSSIER_DEFAUT)
        except Exception as exc:
            st.error(f"Téléchargement impossible ({exc}). Vérifie l'accès à opendata.cern.ch, ou ouvre un fichier local.")
        else:
            _demander_ouverture(st, chemin)


def _section_donnees_ouvertes(st) -> None:  # pragma: no cover - interface graphique
    """Catalogue de jeux de données publics : téléchargement vérifié, ouverture ou campagne en un clic."""
    from outils import donnees_ouvertes as do

    # Le catalogue embarqué s'affiche sans réseau (aucune attente au lancement) ; le bouton relit l'API du CERN.
    entrees = st.session_state.get("catalogue_en_ligne") or do.catalogue(en_ligne=False)
    dossier = do.DOSSIER_DEFAUT
    st.caption("Événements réels du détecteur CMS publiés par le CERN (portail Open Data). Chaque fichier est téléchargé "
               f"dans `{dossier}/`, son intégrité vérifiée avec la somme de contrôle publiée par le CERN, puis ouvert "
               "dans la vue interactive ou confié à la campagne. Les identifiants (Run, Event) sont écartés de l'analyse.")
    tableau = pd.DataFrame([{
        "Jeu": e.identifiant, "Contenu": e.description, "Mo": round(e.taille_mo, 1), "Année": e.annee,
        "Sur le disque": "✅" if do.deja_present(e, dossier) else "—",
    } for e in entrees])
    st.dataframe(tableau, width="stretch", hide_index=True, height=min(420, 38 + 35 * len(entrees)))
    c1, c2, c3 = st.columns([3, 1, 1])
    choix = c1.selectbox("Jeu de données", [e.identifiant for e in entrees], key="ouvert_choix",
                         format_func=lambda i: f"{i} — {do.trouver(i, entrees).description}")
    ouvrir = c2.button("⬇️ Télécharger et ouvrir", key="ouvert_ouvrir", type="primary")
    tout = c3.button("⬇️ Tout télécharger → campagne", key="ouvert_tout",
                     help="Télécharge tout le catalogue puis renseigne le dossier de la campagne ci-dessous.")
    if st.button("🔄 Relire le catalogue sur opendata.cern.ch", key="ouvert_relire",
                 help="Le catalogue affiché est celui embarqué dans l'outil (tailles et sommes de contrôle publiées par le CERN)."):
        try:
            with st.spinner("Lecture de l'API du CERN…"):
                st.session_state["catalogue_en_ligne"] = do.catalogue_en_ligne()
        except Exception as exc:
            st.error(f"Catalogue en ligne inaccessible ({exc}) : le catalogue embarqué reste utilisé.")
        else:
            st.rerun()
    st.caption("Sources : " + " · ".join(f"[enregistrement {r}]({do.URL_PAGE.format(record=r)})" for r in do.ENREGISTREMENTS)
               + ". Les fichiers de 2011 sont sous licence CC0 ; le CERN précise qu'ils sont destinés à l'enseignement.")

    def _telecharger(liste):
        barre = st.progress(0.0)
        chemins = []
        for i, e in enumerate(liste):
            try:
                chemins.append(do.telecharger(
                    e, dossier, rappel=lambda r, t, e=e: barre.progress(min(1.0, (i + r / max(t, 1)) / len(liste)),
                                                                        text=f"{e.nom} — {100 * r / max(t, 1):.0f} %")))
            except Exception as exc:
                st.error(f"{e.nom} : {exc}")
        barre.empty()
        return chemins

    if ouvrir:
        chemins = _telecharger([do.trouver(choix, entrees)])
        if chemins:
            _demander_ouverture(st, chemins[0])
    if tout:
        chemins = _telecharger(entrees)
        if chemins:
            st.session_state["campagne_dossier"] = os.path.abspath(os.path.join(dossier, "700"))
            st.session_state["campagne_reference"] = os.path.abspath(os.path.join(dossier, "700", "MuRun2010B.csv"))
            st.success(f"{len(chemins)} fichiers présents. La campagne ci-dessous est réglée sur les dix tranches de 2010 "
                       "avec le fichier complet en référence : clique « Analyser le dossier ».")
            st.rerun()


def _charger_connaissances(st):  # pragma: no cover - interface graphique
    """Base de connaissances de l'outil (relations, questions, leçons), lue une fois par session."""
    try:
        from anemone_physicien import Connaissances
    except Exception:
        return None
    if "connaissances" not in st.session_state:
        st.session_state["connaissances"] = Connaissances.charger().to_dict()
    return Connaissances(st.session_state["connaissances"])


def _sauver_connaissances(st, connaissances) -> None:  # pragma: no cover - interface graphique
    st.session_state["connaissances"] = connaissances.to_dict()
    try:
        connaissances.sauvegarder()
    except OSError as exc:
        st.warning(f"Connaissances non enregistrées sur le disque : {exc}")


def _section_albert(st, connaissances, matrice, choisies, rapport, contamination: float, seed: int,
                    max_ev: Optional[int], chemin_auto: Optional[str], physicien: str) -> None:  # pragma: no cover
    """Albert : ce qu'il sait, ce qu'il demande, et ses deux actions (apprendre d'un fichier, chercher seul)."""
    from anemone_physicien import Albert, rediger_cahier

    if connaissances is None:
        st.warning("Module Albert indisponible.")
        return
    resume = connaissances.resume()
    st.caption("Albert n'a aucune physique en dur. Il apprend des données (relations démontrables entre variables), "
               "réfute avec preuve calculée les objections qu'il peut réfuter, pose au physicien celles qu'il ne peut "
               "pas trancher, et ne retient comme trouvaille qu'un run « solide » sous plusieurs stratégies. "
               f"Il sait aujourd'hui : {resume['relations']} relation(s), {resume['questions_ouvertes']} question(s) ouverte(s), "
               f"{resume['lecons']} leçon(s).")

    # -- questions au physicien -------------------------------------------
    questions = connaissances.questions_ouvertes()
    if questions:
        st.write("**Albert vous demande :**")
        for q in questions:
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.write(f"{' ↔ '.join(q['variables'])} — {q['contexte']}")
            if c2.button("Relation connue", key=f"q_ok_{q['id']}"):
                connaissances.repondre(q["id"], "relation_connue", physicien or "physicien")
                _sauver_connaissances(st, connaissances)
                st.rerun()
            if c3.button("Vrai biais", key=f"q_biais_{q['id']}"):
                connaissances.repondre(q["id"], "biais", physicien or "physicien")
                _sauver_connaissances(st, connaissances)
                st.rerun()

    # -- actions -------------------------------------------------------------
    c1, c2 = st.columns(2)
    apprendre = c1.button("📚 Albert, apprends de ce fichier", key="albert_apprendre", disabled=matrice is None or not choisies,
                          help="Relations démontrables + un débat complet avec l'Architecte, consigné dans le graphe.")
    dossier = st.session_state.get("campagne_dossier", "")
    reference = st.session_state.get("campagne_reference", "")
    chercher = c2.button("🔭 Albert, cherche seul dans le dossier de la campagne", key="albert_chercher",
                         disabled=not dossier, help="Renseigne d'abord le dossier (et la référence) dans la section « Campagne automatique ».")
    albert = Albert(connaissances)
    if apprendre and matrice is not None:
        g = _graphe(st)
        with st.spinner("Albert apprend et débat …"):
            lecon = albert.entrainer(matrice, list(choisies), g, rapport.get("fichier", "matrice"), contamination, seed)
        _sauver_graphe(st, g, chemin_auto)
        _sauver_connaissances(st, connaissances)
        st.session_state["albert_derniere_lecon"] = lecon
        st.rerun()
    if chercher and dossier:
        import anemone_campagne as ac
        chemins = [dossier] if os.path.isfile(dossier) else (ac.lister_fichiers(dossier) if os.path.isdir(dossier) else [])
        if not chemins:
            st.error("Dossier introuvable ou vide.")
        else:
            g = _graphe(st)
            barre = st.progress(0.0, text="Albert commence …")
            def rappel(etape, i, n, nom):
                barre.progress(min(1.0, i / max(n, 1)), text=f"Albert — {etape} {i}/{n} : {nom}")
            cahier = albert.chercher(chemins, reference or None, g, "cahier_albert", contamination, seed, max_ev, 0.0, rappel)
            barre.empty()
            _sauver_graphe(st, g, chemin_auto)
            _sauver_connaissances(st, connaissances)
            st.session_state["albert_dernier_cahier"] = cahier
            st.rerun()

    # -- résultats -----------------------------------------------------------
    lecon = st.session_state.get("albert_derniere_lecon")
    if lecon:
        from anemone_physicien import resume_lecon
        st.code(resume_lecon(lecon), language="text")
    cahier = st.session_state.get("albert_dernier_cahier")
    if cahier:
        st.markdown(rediger_cahier(cahier))
        st.caption(f"Cahier enregistré : `{cahier.get('chemin')}`")
    if connaissances.relations:
        with st.expander(f"Ce que l'outil sait ({len(connaissances.relations)} relations)", expanded=False):
            st.dataframe(pd.DataFrame([{"Variables": ", ".join(r["variables"]), "Nature": r["nature"], "Preuve": r["preuve"],
                                        "Origine": r["origine"], "Date": r["date"][:10]} for r in connaissances.relations]),
                         width="stretch", hide_index=True)


def _section_campagne(st, physicien: str, contamination: float, seed: int, max_ev: Optional[int],
                      chemin_auto: Optional[str], paires_connues=None) -> None:  # pragma: no cover - interface graphique
    """Le physicien donne un dossier ; l'outil analyse chaque run, mène les tests de robustesse et rend des verdicts."""
    import anemone_campagne as ac

    st.caption("Donne un dossier de fichiers .root / .csv. Chaque run est analysé avec les réglages de la barre latérale "
               "(taux de contamination, graine, événements max), soumis au balayage de robustesse, au fond bootstrap "
               "et, si tu fournis un run de référence, à la comparaison avec celui-ci. Tu ne vois que les verdicts, "
               "classés par priorité ; le rapport complet est écrit dans le dossier `rapports/`.")
    c1, c2 = st.columns(2)
    dossier = c1.text_input("Dossier de runs à analyser", key="campagne_dossier", placeholder="/data/runs")
    reference = c2.text_input("Run de référence (facultatif : calibration, fond connu)", key="campagne_reference",
                              placeholder="/data/calibration.root")
    c3, c4, c5, c6 = st.columns([1, 1, 1, 1])
    balayage = c3.checkbox("Balayage de robustesse", value=True, key="campagne_balayage",
                           help="Fait varier le taux de contamination (÷2, ×2) et la graine : le noyau isolé doit tenir.")
    recursif = c4.checkbox("Sous-dossiers inclus", value=False, key="campagne_recursif")
    veille = c5.checkbox("Veille (nouveaux fichiers toutes les 60 s)", key="campagne_veille",
                         help="Tant que cette page est ouverte, tout fichier déposé dans le dossier est analysé.")
    lancer = c6.button("▶️ Analyser le dossier", key="campagne_lancer", type="primary")
    st.session_state.setdefault("campagne_resultats", [])
    st.session_state.setdefault("campagne_vus", [])
    st.session_state.setdefault("campagne_rapport", None)

    def _tour(seulement_nouveaux: bool) -> None:
        if not dossier or not os.path.isdir(dossier):
            if not seulement_nouveaux:
                st.error("Indique un dossier existant.")
            return
        chemins = ac.lister_fichiers(dossier, recursif)
        if seulement_nouveaux:
            chemins = [c for c in chemins if c not in st.session_state["campagne_vus"]]
        else:
            st.session_state["campagne_resultats"], st.session_state["campagne_vus"] = [], []
        if not chemins:
            if not seulement_nouveaux:
                st.warning("Aucun fichier .root / .csv dans ce dossier.")
            return
        ref_df = None
        if reference:
            try:
                ref_df = ac.charger_reference(reference, max_ev)
            except Exception as exc:
                st.error(f"Référence illisible : {exc}")
                return
        barre = st.progress(0.0, text=f"0 / {len(chemins)}")

        def rappel(i: int, n: int, r: ac.ResultatFichier) -> None:
            barre.progress(i / n, text=f"{i} / {n} — {r.fichier} : {r.etiquette}")

        parametres = {"dossier": os.path.abspath(dossier), "reference": reference or None, "variables": None,
                      "contamination": contamination, "seed": seed, "max_evenements": max_ev, "balayage": balayage}
        nouveaux = ac.analyser_campagne(chemins, None, contamination, seed, balayage, ref_df, max_ev, rappel, paires_connues)
        barre.empty()
        st.session_state["campagne_vus"] += chemins
        tous = [ac.ResultatFichier(**{k: v for k, v in d.items() if k != "etiquette"}) for d in st.session_state["campagne_resultats"]]
        tous = ac.trier(tous + nouveaux)
        st.session_state["campagne_resultats"] = [r.to_dict() for r in tous]
        try:
            st.session_state["campagne_rapport"] = ac.ecrire_rapport(tous, "rapports", parametres)
        except OSError as exc:
            st.warning(f"Rapport non écrit : {exc}")
        g = _graphe(st)
        ac.consigner_dans_graphe(g, nouveaux, parametres, st.session_state["campagne_rapport"])
        _sauver_graphe(st, g, chemin_auto)

    if veille:
        @st.fragment(run_every="60s")
        def _veille() -> None:
            _tour(seulement_nouveaux=True)
            st.caption(f"Veille active — dernier passage {datetime.now().strftime('%H:%M:%S')}")
        _veille()
    elif lancer:
        _tour(seulement_nouveaux=False)

    resultats = st.session_state["campagne_resultats"]
    if not resultats:
        return
    comptes = {}
    for r in resultats:
        comptes[r["verdict"]] = comptes.get(r["verdict"], 0) + 1
    st.write("**" + " · ".join(f"{ac.ETIQUETTES[v]} : {n}" for v, n in sorted(comptes.items(), key=lambda kv: ac.PRIORITE[kv[0]])) + "**")
    tableau = pd.DataFrame([{
        "Verdict": r["etiquette"], "Run": r["fichier"], "Événements": r["n_evenements"], "Isolés": r["n_anomalies"],
        "Dominante": r["dominante"] or "—", "d": r["d_cohen"], "p": r["p_value"], "Stabilité": r["stabilite"],
        "Excès fond": r["exces_fond"], "Pourquoi": " ; ".join(r["motifs"]),
    } for r in resultats])
    st.dataframe(tableau, width="stretch", hide_index=True)
    if st.session_state["campagne_rapport"]:
        st.caption(f"Rapport complet : `{os.path.join(st.session_state['campagne_rapport'], 'rapport.md')}` (Markdown, CSV, JSON avec provenance).")
    lisibles = [r["chemin"] for r in resultats if r["verdict"] != "erreur"]
    if lisibles:
        c7, c8 = st.columns([3, 1])
        choix = c7.selectbox("Ouvrir un run dans la vue interactive", lisibles, key="campagne_ouvrir",
                             format_func=os.path.basename)
        if c8.button("🔍 Ouvrir", key="campagne_bouton_ouvrir"):
            _demander_ouverture(st, choix)


def _charger_cache(st, octets: bytes, nom: str, arbre: Optional[str], max_ev: Optional[int]):
    @st.cache_data(show_spinner="Lecture de la matrice…")
    def _lire(octets_: bytes, nom_: str, arbre_: Optional[str], max_ev_: Optional[int]):
        return analyser_fichier_physique(octets_, nom_, arbre_, max_ev_)

    return _lire(octets, nom, arbre, max_ev)


if __name__ == "__main__":
    lancer_interface()
