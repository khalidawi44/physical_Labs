# -*- coding: utf-8 -*-
"""Mode « Découverte guidée » d'A.N.E.M.O.N.E : lire le résultat sans jargon.

Tout ce qui est écrit ici est calculé depuis le diagnostic (`diagnostiquer`) :
aucun chiffre n'est inventé, aucune interprétation physique n'est produite.
Le niveau de preuve reprend exactement les seuils de l'Architecte
(p < SEUIL_P_VERROU et |d| ≥ SEUIL_D_VERROU pour « très net »).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import anemone_master as am

# Niveaux de preuve, du plus faible au plus fort. Les seuils « net » sont
# volontairement plus prudents que ceux de la publication : ils disent seulement
# « ça mérite un regard », jamais « c'est une découverte ».
SEUIL_P_NET = 0.01
SEUIL_D_NET = 0.5
SEUIL_FENETRE_TEMPORELLE = 0.2   # isolés concentrés sur moins de 20 % de la durée → épisode

NIVEAUX = {
    "insuffisant": ("⚪", "Pas assez d'événements isolés pour conclure quoi que ce soit."),
    "faible": ("🟡", "Écart faible : les isolés ressemblent beaucoup aux autres. Rien à signaler."),
    "net": ("🟠", "Écart net : les isolés se distinguent, mais pas assez pour exclure une fluctuation. À regarder."),
    "tres_net": ("🔴", "Écart très net : les isolés forment un groupe à part. C'est ce que l'Architecte défend "
                       "comme preuve formelle. Reste à vérifier que ce n'est pas l'appareil de mesure."),
}

GLOSSAIRE = {
    "événement": "Une ligne du fichier : une collision, une mesure, un instant enregistré par le détecteur.",
    "variable": "Une colonne du fichier : une grandeur mesurée pour chaque événement (énergie, temps, angle…).",
    "isolé (ou anomalie)": "Un événement que l'outil n'arrive pas à ranger avec les autres : il est loin de la masse "
                           "sur l'ensemble des variables. Cela ne veut pas dire « nouvelle physique », seulement « inhabituel ».",
    "Isolation Forest": "La méthode qui repère les isolés : elle coupe les données au hasard, encore et encore ; "
                        "un événement séparé des autres en quelques coupes est isolé.",
    "taux de contamination": "La part d'événements que l'outil accepte de marquer comme isolés (3 % par défaut). "
                             "Ce n'est pas une mesure, c'est un réglage.",
    "variable dominante": "La variable sur laquelle les isolés s'écartent le plus des autres événements.",
    "p (p-value)": "La probabilité d'observer un écart au moins aussi grand si, en réalité, les isolés étaient tirés "
                   "de la même population que les autres. Plus p est petit, moins le hasard explique l'écart.",
    "d (taille d'effet)": "L'écart entre les moyennes des isolés et des autres, compté en nombre d'écarts-types. "
                          "d = 1 : un écart-type entier ; d = 0,2 : un écart à peine visible.",
    "biais instrumental": "Un écart qui vient de l'appareil (dérive, coupure, saturation) et non de la physique. "
                          "Indice classique : les isolés partagent un lien entre deux variables que les autres n'ont pas.",
    "fond": "Les événements connus et attendus. Une « queue du fond » est un événement rare mais ordinaire.",
    "run": "Un fichier d'événements enregistré d'un seul tenant par le détecteur.",
    "référence": "Un run de calibration ou de fond connu, utilisé pour vérifier que l'écart n'apparaît pas aussi là où il ne devrait pas.",
    "verdict de campagne": "Solide, suspect de biais, fragile, queues du fond, faible, insuffisant : ce que l'outil conclut "
                           "après avoir refait l'analyse sous plusieurs réglages.",
}


def _nombre(x: float) -> str:
    """Nombre lisible : 3 chiffres significatifs, sans notation scientifique inutile."""
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1000 or a < 0.001:
        return f"{x:.2e}"
    if a >= 100:
        return f"{x:.0f}"
    if a >= 10:
        return f"{x:.1f}"
    return f"{x:.2f}"


def _p_lisible(p: float) -> str:
    if p < 1e-4:
        return "moins d'une chance sur 10 000"
    if p < 1e-3:
        return "moins d'une chance sur 1 000"
    if p < 0.01:
        return "moins d'une chance sur 100"
    if p < 0.05:
        return "moins d'une chance sur 20"
    return f"environ {p * 100:.0f} chances sur 100"


def niveau_de_preuve(diag: Dict[str, Any]) -> str:
    """Clé de NIVEAUX pour la variable dominante, avec les seuils de l'Architecte pour « très net »."""
    if diag.get("insuffisant") or not diag.get("variables"):
        return "insuffisant"
    dom = am.variable_dominante(diag)
    v = diag["variables"][dom]
    p, d = v["p_value"], abs(v["d_cohen"])
    if p < am.Architecte.SEUIL_P_VERROU and d >= am.Architecte.SEUIL_D_VERROU:
        return "tres_net"
    if p < SEUIL_P_NET and d >= SEUIL_D_NET:
        return "net"
    return "faible"


def lecture_guidee(diag: Dict[str, Any], rapport: Dict[str, Any],
                   paires_connues: Optional[Iterable[frozenset]] = None) -> Dict[str, Any]:
    """Résumé en langage courant, entièrement dérivé du diagnostic et du rapport de lecture."""
    n, k, n_ano = diag["n_total"], len(diag.get("variables", {})) or len(diag.get("roles", {})), diag["n_anomalies"]
    demo = rapport.get("format") == "demo"
    resume: List[str] = [
        f"Le fichier **{rapport.get('fichier', 'chargé')}** contient **{n} événements**, décrits par "
        f"**{rapport.get('n_variables', k)} variables**."
    ]
    if n:
        resume.append(f"L'outil en a isolé **{n_ano}** ({100.0 * n_ano / n:.1f} %) : ils ne ressemblent pas aux autres "
                      "sur l'ensemble des variables analysées.")
    niveau = niveau_de_preuve(diag)
    pastille, phrase = NIVEAUX[niveau]
    chiffres: Dict[str, str] = {}
    vigilance: List[str] = []
    dominante = None
    if niveau != "insuffisant":
        dominante = am.variable_dominante(diag)
        v = diag["variables"][dominante]
        sens = "plus haut" if v["moy_anomalies"] > v["moy_conformes"] else "plus bas"
        resume.append(f"La variable qui les distingue le plus est **{dominante}** : en moyenne "
                      f"{_nombre(v['moy_anomalies'])} chez les isolés contre {_nombre(v['moy_conformes'])} chez les autres "
                      f"({sens}).")
        chiffres = {
            "Écart (d)": f"{_nombre(abs(v['d_cohen']))} écart-type" + ("s" if abs(v["d_cohen"]) >= 2 else ""),
            "Hasard (p)": _p_lisible(v["p_value"]),
        }
        for corr in am.correlations_fortes(diag, dominante, connues=paires_connues):
            if corr["nature"] == "suspecte":
                vigilance.append(f"Chez les isolés, **{dominante}** varie avec **{corr['autre']}** "
                                 f"(lien {_nombre(corr['r_isoles'])}) alors que ce lien est absent ou bien plus faible chez les "
                                 f"autres ({_nombre(corr['r_conformes'])}). Cela peut venir de l'appareil de mesure plutôt que "
                                 "de la physique : à vérifier avant tout.")
        fraction = diag.get("geometrie", {}).get("fraction_fenetre_temporelle")
        if fraction is not None and fraction < SEUIL_FENETRE_TEMPORELLE:
            vigilance.append(f"Les isolés sont concentrés dans une courte période ({100 * fraction:.0f} % de la durée "
                             "du fichier) : un incident ponctuel de l'appareil est possible.")
    et_maintenant: List[str] = []
    if demo:
        et_maintenant.append("Ces données sont synthétiques : elles servent à voir l'outil fonctionner, rien de plus. "
                             "Pour du réel, ouvre un fichier du CERN depuis « Données réelles en un clic ».")
    else:
        if niveau in ("net", "tres_net"):
            et_maintenant.append("Lance la campagne automatique sur le dossier du run : elle refait l'analyse sous plusieurs "
                                 "réglages et dit si l'écart tient (verdict « solide ») ou s'effondre (« fragile »).")
            et_maintenant.append("Si tu disposes d'un run de calibration ou de fond connu, donne-le en référence : "
                                 "l'écart ne doit pas apparaître aussi là.")
        if vigilance:
            et_maintenant.append("Montre les points de vigilance à un physicien ou à la personne qui connaît l'appareil : "
                                 "eux seuls peuvent dire si c'est un artefact de mesure.")
        if niveau == "faible":
            et_maintenant.append("Rien ne ressort ici. Tu peux essayer d'autres variables, ou un autre run.")
        if niveau == "insuffisant":
            et_maintenant.append("Charge un fichier plus grand, ou augmente le taux de contamination dans les réglages avancés.")
    et_maintenant.append("Pour voir les calculs derrière ces phrases, passe en mode Expert (barre latérale) : "
                         "rien n'est caché, seulement traduit.")
    return {
        "resume": resume,
        "niveau": niveau,
        "pastille": pastille,
        "phrase_niveau": phrase,
        "dominante": dominante,
        "chiffres": chiffres,
        "vigilance": vigilance,
        "et_maintenant": et_maintenant,
        "demo": demo,
    }
