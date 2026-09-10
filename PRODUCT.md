# Product

<!-- impeccable:product-schema 1 -->

Charte produit de la **cartographie 4D d'Alliance Groupe**. Ce qui n'existe pas
encore est marqué **objectif**.

## Platform

web (application Streamlit locale, ouverte dans le navigateur de la machine)

## Users

Alliance Groupe et ses interlocuteurs experts (prospects techniques, partenaires
IT), à qui l'on veut montrer clairement comment fonctionne l'entreprise : la
synchronisation GitHub ⇆ repo local, l'intégration continue, la mise en
production, les deux audits (web et Kali) et les livrables.

## Product Purpose

Une **cartographie 4D de démonstration de l'infrastructure d'Alliance Groupe** :
elle montre à des experts la mécanique complète (GitHub ⇆ repo local
synchronisés, CI, site en production, audit web **AG-Audit**, audit expert
**AG-Kali** sous Kali Linux, livrables) sous forme d'un graphe stratifié animé,
d'un rejeu vidéo, d'un mode présentation plein écran et d'un exemple de rapport
livrable téléchargeable. Le succès : qu'un expert comprenne la mécanique et la
valeur d'Alliance Groupe en quelques minutes, sans manipuler l'outil.

## Positioning

Un support de démonstration et de vente : la mécanique d'Alliance rendue visible
et racontée, du push à la remédiation, avec le livrable concret (rapport brandé
+ devis) que reçoit un client.

## Operating Context

L'outil s'exécute localement dans un navigateur via Streamlit. **Rien n'est
scanné en direct** : tout vient du modèle éditable `alliance_modele.py`. Rien ne
quitte la machine : aucune statistique d'usage, écoute sur `localhost` seulement.

## Capabilities and Constraints

- Cinq vues : présentation plein écran (mode démo, narration et navigation),
  carte complète 4D, rejeu animé, parcours étape par étape, et rapport d'exemple.
- Le rapport d'exemple (constats classés par gravité, devis chiffré, document
  Word brandé téléchargeable) est **fictif et étiqueté comme tel** : il illustre
  le rendu du livrable, il n'audite aucun site réel.
- L'audit modélisé est **défensif**, sur les propres actifs d'Alliance Groupe ;
  sqlmap est représenté en détection seule, sans extraction.
- La structure et les interactions se modifient dans `alliance_modele.py` ;
  `valider()` garantit la cohérence du modèle.
- L'outil ne collecte ni n'envoie aucune donnée.

## Brand Commitments

Marque : Advise Alliance Group. Ton : expert, clair, non sensationnaliste. La
beauté visuelle doit servir la lecture par des experts.

## Evidence on Hand

Modèle cohérent validé par `valider()`, tests automatisés sur Windows, macOS et
Linux (pytest + lanceurs), rapport d'exemple reproductible. Les constats et
montants du rapport sont illustratifs et ne doivent jamais être présentés comme
l'audit d'un site réel.

## Product Principles

- Montrer la mécanique réelle, sans la caricaturer.
- Distinguer clairement la démonstration de l'audit réel.
- Rendre le parcours simple par défaut, précis à la demande.
- Rester un audit défensif, sur ses propres actifs.
- Ne jamais inventer un chiffre ni un fait ; vérifier avant de livrer.
