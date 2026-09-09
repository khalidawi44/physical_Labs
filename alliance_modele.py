# -*- coding: utf-8 -*-
"""Modèle de démonstration de la mécanique d'Alliance Groupe.

Ce fichier décrit — comme un schéma éditable, pas comme un relevé automatique —
l'infrastructure d'Alliance Groupe et la façon dont ses deux systèmes d'audit
travaillent : le dépôt GitHub synchronisé avec le repo local, l'intégration
continue, le site en production, l'audit web **AG-Audit** et l'audit Kali expert
**AG-Kali**, et les livrables. Tout est structuré pour être cartographié en 4D
(trois axes d'espace + la couche comme quatrième dimension, en couleur) et
rejoué comme une animation.

Rien ici n'est scanné en direct : c'est le modèle qui montre la mécanique à des
experts. Chaque nœud, chaque interaction et chaque étape se modifie ici.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Les couches (la « quatrième dimension » scientifique : la couleur du nœud).
COUCHES: Tuple[str, ...] = ("Développement", "Intégration", "Production", "Audit web", "Audit Kali", "Livrables")

COULEURS: Dict[str, str] = {
    "Développement": "#3498db",   # bleu
    "Intégration": "#1abc9c",     # turquoise
    "Production": "#2ecc71",      # vert
    "Audit web": "#f39c12",       # orange
    "Audit Kali": "#e74c3c",      # rouge (Kali)
    "Livrables": "#9b59b6",       # violet
}

# ---------------------------------------------------------------------------
# Nœuds : id, nom affiché, couche, importance (taille), description.
# ---------------------------------------------------------------------------
NOEUDS: Tuple[Dict[str, Any], ...] = (
    {"id": "local", "nom": "Repo local", "couche": "Développement", "poids": 3,
     "detail": "Ton dossier de travail sur la machine. Édition du code et des configurations d'audit."},
    {"id": "github", "nom": "Dépôt GitHub", "couche": "Développement", "poids": 4,
     "detail": "Le dépôt distant. Source de vérité partagée, historique complet, base des mises à jour."},
    {"id": "sync", "nom": "Synchronisation auto", "couche": "Développement", "poids": 3,
     "detail": "git push / pull bidirectionnel : le repo local et GitHub restent alignés automatiquement."},
    {"id": "ci", "nom": "CI GitHub Actions", "couche": "Intégration", "poids": 3,
     "detail": "À chaque poussée : tests, lint, et exécution des lanceurs sur Windows, macOS et Linux."},
    {"id": "deploiement", "nom": "Déploiement", "couche": "Intégration", "poids": 2,
     "detail": "Une fois la CI verte, la nouvelle version part vers l'hébergement du site."},
    {"id": "site", "nom": "Site Alliance Groupe", "couche": "Production", "poids": 4,
     "detail": "Le site en production (WordPress). C'est la cible de l'audit."},
    {"id": "wordpress", "nom": "Cœur WordPress", "couche": "Production", "poids": 2,
     "detail": "Thèmes, extensions, version du cœur : la surface d'attaque principale d'un site WordPress."},
    {"id": "bdd", "nom": "Base de données", "couche": "Production", "poids": 2,
     "detail": "Contenus, comptes, sessions. Cible des injections SQL testées à blanc pendant l'audit."},
    {"id": "formulaires", "nom": "Formulaires & API", "couche": "Production", "poids": 2,
     "detail": "Points d'entrée : contact, connexion, endpoints REST. Testés pour l'injection et l'authentification."},
    {"id": "ag_audit", "nom": "AG-Audit", "couche": "Audit web", "poids": 4,
     "detail": "L'audit web guidé : cadrage, scan, puis rapport DOCX brandé et devis de remédiation."},
    {"id": "crawl", "nom": "Exploration", "couche": "Audit web", "poids": 1,
     "detail": "Cartographie des pages, formulaires, scripts et appels externes du site."},
    {"id": "entetes", "nom": "En-têtes & TLS", "couche": "Audit web", "poids": 1,
     "detail": "En-têtes de sécurité (CSP, HSTS…) et qualité du certificat TLS."},
    {"id": "ag_kali", "nom": "AG-Kali", "couche": "Audit Kali", "poids": 4,
     "detail": "L'audit expert sous Kali Linux : la chaîne d'outils complète, en profondeur."},
    {"id": "nmap", "nom": "nmap", "couche": "Audit Kali", "poids": 1,
     "detail": "Découverte des ports et services ouverts, versions logicielles exposées."},
    {"id": "whatweb", "nom": "WhatWeb", "couche": "Audit Kali", "poids": 1,
     "detail": "Empreinte des technologies : serveur, CMS, extensions, versions."},
    {"id": "wpscan", "nom": "WPScan", "couche": "Audit Kali", "poids": 1,
     "detail": "Vulnérabilités connues du cœur, des thèmes et des extensions WordPress ; comptes énumérables."},
    {"id": "nikto", "nom": "Nikto", "couche": "Audit Kali", "poids": 1,
     "detail": "Fichiers et configurations dangereuses exposées par le serveur web."},
    {"id": "gobuster", "nom": "Gobuster", "couche": "Audit Kali", "poids": 1,
     "detail": "Répertoires et fichiers cachés découverts par force brute de dictionnaire."},
    {"id": "sslscan", "nom": "sslscan", "couche": "Audit Kali", "poids": 1,
     "detail": "Protocoles et algorithmes TLS faibles encore acceptés par le serveur."},
    {"id": "sqlmap", "nom": "sqlmap (à blanc)", "couche": "Audit Kali", "poids": 1,
     "detail": "Test d'injection SQL en mode détection seule, sans extraction : confirme un point d'entrée vulnérable."},
    {"id": "findings", "nom": "Vulnérabilités", "couche": "Livrables", "poids": 3,
     "detail": "Les constats consolidés des deux audits, classés par gravité (critique → info)."},
    {"id": "rapport", "nom": "Rapport DOCX", "couche": "Livrables", "poids": 3,
     "detail": "Le rapport brandé Advise Alliance Group, lisible par un décideur comme par un expert."},
    {"id": "devis", "nom": "Devis de remédiation", "couche": "Livrables", "poids": 2,
     "detail": "Le chiffrage des corrections, prêt à envoyer au client."},
)

# ---------------------------------------------------------------------------
# Interactions : (source, cible, relation, nature).
# nature : "sync" (bidirectionnel), "flux" (déploiement/données), "audit" (scan), "livrable".
# ---------------------------------------------------------------------------
ARETES: Tuple[Tuple[str, str, str, str], ...] = (
    ("local", "github", "push / pull automatique", "sync"),
    ("github", "sync", "suit", "sync"),
    ("sync", "local", "aligne", "sync"),
    ("github", "ci", "déclenche", "flux"),
    ("ci", "deploiement", "valide puis déploie", "flux"),
    ("deploiement", "site", "met en ligne", "flux"),
    ("site", "wordpress", "sert", "flux"),
    ("site", "bdd", "lit / écrit", "flux"),
    ("site", "formulaires", "expose", "flux"),
    ("github", "ag_audit", "héberge la config", "flux"),
    ("github", "ag_kali", "héberge la config", "flux"),
    ("ag_audit", "crawl", "lance", "audit"),
    ("ag_audit", "entetes", "lance", "audit"),
    ("crawl", "site", "explore", "audit"),
    ("entetes", "site", "mesure", "audit"),
    ("ag_kali", "nmap", "lance", "audit"),
    ("ag_kali", "whatweb", "lance", "audit"),
    ("ag_kali", "wpscan", "lance", "audit"),
    ("ag_kali", "nikto", "lance", "audit"),
    ("ag_kali", "gobuster", "lance", "audit"),
    ("ag_kali", "sslscan", "lance", "audit"),
    ("ag_kali", "sqlmap", "lance", "audit"),
    ("nmap", "site", "sonde", "audit"),
    ("whatweb", "wordpress", "empreinte", "audit"),
    ("wpscan", "wordpress", "teste", "audit"),
    ("nikto", "site", "teste", "audit"),
    ("gobuster", "site", "teste", "audit"),
    ("sslscan", "site", "teste", "audit"),
    ("sqlmap", "formulaires", "teste (à blanc)", "audit"),
    ("crawl", "findings", "remonte", "livrable"),
    ("entetes", "findings", "remonte", "livrable"),
    ("wpscan", "findings", "remonte", "livrable"),
    ("nikto", "findings", "remonte", "livrable"),
    ("sqlmap", "findings", "remonte", "livrable"),
    ("sslscan", "findings", "remonte", "livrable"),
    ("findings", "rapport", "alimente", "livrable"),
    ("findings", "devis", "chiffre", "livrable"),
    ("rapport", "local", "corrections à appliquer", "sync"),
)

# ---------------------------------------------------------------------------
# Le rejeu animé : la séquence de la mécanique, étape par étape (la « vidéo »).
# Chaque étape allume des nœuds et des interactions.
# ---------------------------------------------------------------------------
SEQUENCE: Tuple[Dict[str, Any], ...] = (
    {"titre": "1 · Synchronisation", "acteur": "Git",
     "description": "Le repo local et GitHub s'alignent en continu : chaque correction poussée devient la source de vérité partagée.",
     "noeuds": ("local", "sync", "github"), "aretes": (("local", "github"), ("github", "sync"), ("sync", "local"))},
    {"titre": "2 · Intégration continue", "acteur": "GitHub Actions",
     "description": "La poussée déclenche la CI : tests et lanceurs sur trois systèmes. Verte, elle autorise le déploiement.",
     "noeuds": ("github", "ci", "deploiement"), "aretes": (("github", "ci"), ("ci", "deploiement"))},
    {"titre": "3 · Mise en production", "acteur": "Déploiement",
     "description": "La nouvelle version part en ligne. Le site, WordPress, la base et les formulaires sont la cible de l'audit.",
     "noeuds": ("deploiement", "site", "wordpress", "bdd", "formulaires"),
     "aretes": (("deploiement", "site"), ("site", "wordpress"), ("site", "bdd"), ("site", "formulaires"))},
    {"titre": "4 · Audit web AG-Audit", "acteur": "AG-Audit",
     "description": "L'audit guidé explore le site et mesure ses en-têtes et son TLS. Rapide, cadré, reproductible.",
     "noeuds": ("ag_audit", "crawl", "entetes", "site"),
     "aretes": (("github", "ag_audit"), ("ag_audit", "crawl"), ("ag_audit", "entetes"), ("crawl", "site"), ("entetes", "site"))},
    {"titre": "5 · Audit expert AG-Kali", "acteur": "AG-Kali",
     "description": "Sous Kali Linux, la chaîne complète : reconnaissance, empreinte, WordPress, serveur, TLS, injection testée à blanc.",
     "noeuds": ("ag_kali", "nmap", "whatweb", "wpscan", "nikto", "gobuster", "sslscan", "sqlmap"),
     "aretes": (("github", "ag_kali"), ("ag_kali", "nmap"), ("ag_kali", "whatweb"), ("ag_kali", "wpscan"),
                ("ag_kali", "nikto"), ("ag_kali", "gobuster"), ("ag_kali", "sslscan"), ("ag_kali", "sqlmap"),
                ("nmap", "site"), ("wpscan", "wordpress"), ("sqlmap", "formulaires"))},
    {"titre": "6 · Consolidation", "acteur": "AG-Audit",
     "description": "Les constats des deux audits se rassemblent, classés par gravité, et deviennent le rapport brandé et le devis.",
     "noeuds": ("findings", "rapport", "devis"),
     "aretes": (("wpscan", "findings"), ("sqlmap", "findings"), ("entetes", "findings"),
                ("findings", "rapport"), ("findings", "devis"))},
    {"titre": "7 · Boucle de remédiation", "acteur": "Git",
     "description": "Les corrections du rapport reviennent dans le repo local, sont poussées, et le cycle recommence, plus sûr.",
     "noeuds": ("rapport", "local", "github"),
     "aretes": (("rapport", "local"), ("local", "github"))},
)

# ---------------------------------------------------------------------------
# La chaîne d'outils Kali (section experte : ce que fait AG-Kali, phase par phase).
# ---------------------------------------------------------------------------
OUTILS_KALI: Tuple[Dict[str, str], ...] = (
    {"phase": "Reconnaissance", "outil": "nmap", "but": "Cartographier les ports et services ouverts",
     "revele": "Quels services (HTTP, SSH, base…) sont exposés et leurs versions."},
    {"phase": "Empreinte", "outil": "WhatWeb", "but": "Identifier les technologies du site",
     "revele": "Serveur web, CMS WordPress, thème, extensions et leurs versions exactes."},
    {"phase": "WordPress", "outil": "WPScan", "but": "Chercher les vulnérabilités connues WordPress",
     "revele": "Cœur, thèmes et extensions vulnérables ; comptes utilisateurs énumérables."},
    {"phase": "Serveur web", "outil": "Nikto", "but": "Repérer les configurations et fichiers dangereux",
     "revele": "Fichiers de sauvegarde, panneaux d'administration, options serveur risquées."},
    {"phase": "Contenu caché", "outil": "Gobuster", "but": "Découvrir répertoires et fichiers non liés",
     "revele": "Chemins cachés (/admin, /backup, .git…) accessibles sans y être invité."},
    {"phase": "Chiffrement", "outil": "sslscan", "but": "Évaluer la solidité du TLS",
     "revele": "Protocoles et algorithmes faibles encore acceptés, certificat expiré ou mal configuré."},
    {"phase": "Injection", "outil": "sqlmap (à blanc)", "but": "Confirmer un point d'injection SQL, sans extraire",
     "revele": "Si un formulaire ou un paramètre laisse passer une injection — en détection seule, sans toucher aux données."},
    {"phase": "Rapport", "outil": "AG-Audit", "but": "Consolider et rédiger",
     "revele": "Un rapport DOCX brandé et un devis de remédiation, du constat à la correction chiffrée."},
)


def noeuds() -> List[Dict[str, Any]]:
    return [dict(n) for n in NOEUDS]


def aretes() -> List[Tuple[str, str, str, str]]:
    return list(ARETES)


def sequence() -> List[Dict[str, Any]]:
    return [dict(e) for e in SEQUENCE]


def outils_kali() -> List[Dict[str, str]]:
    return [dict(o) for o in OUTILS_KALI]


def noeud(identifiant: str) -> Dict[str, Any]:
    for n in NOEUDS:
        if n["id"] == identifiant:
            return dict(n)
    raise KeyError(identifiant)


def valider() -> List[str]:
    """Cohérence du modèle : couches connues, arêtes et étapes ne référençant que des nœuds existants."""
    ids = {n["id"] for n in NOEUDS}
    problemes: List[str] = []
    if len(ids) != len(NOEUDS):
        problemes.append("identifiants de nœuds en double")
    for n in NOEUDS:
        if n["couche"] not in COUCHES:
            problemes.append(f"nœud {n['id']} : couche inconnue {n['couche']}")
    for s, d, _, nature in ARETES:
        if s not in ids or d not in ids:
            problemes.append(f"arête {s}→{d} : nœud inconnu")
        if nature not in ("sync", "flux", "audit", "livrable"):
            problemes.append(f"arête {s}→{d} : nature inconnue {nature}")
    couples = {(s, d) for s, d, _, _ in ARETES}
    for e in SEQUENCE:
        for nid in e["noeuds"]:
            if nid not in ids:
                problemes.append(f"étape « {e['titre']} » : nœud inconnu {nid}")
        for s, d in e["aretes"]:
            if s not in ids or d not in ids:
                problemes.append(f"étape « {e['titre']} » : arête vers un nœud inconnu {s}→{d}")
    return problemes
