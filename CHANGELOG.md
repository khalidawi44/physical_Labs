# Journal des versions — A.N.E.M.O.N.E

Le numéro de version publié est celui du fichier `VERSION` sur la branche `main`.
Les lanceurs le comparent au démarrage et proposent la mise à jour.

## 0.3.0 — 2026-09-05

- **Mode campagne** : l'outil analyse seul un dossier de runs (.root / .csv),
  mène lui-même les expériences de robustesse (balayage contamination/graine,
  fond bootstrap, comparaison à un run de référence), rend un verdict calculé
  par run (solide, suspect, fragile, queues du fond, faible, insuffisant,
  erreur), écrit un rapport reproductible (Markdown, CSV, JSON avec empreintes
  et versions) et consigne la campagne dans le graphe de connaissances.
- Veille : tout nouveau fichier déposé dans le dossier est analysé (interface
  et ligne de commande `python anemone_campagne.py DOSSIER --veille 300`).
- Depuis les verdicts, ouverture d'un run en un clic dans la vue interactive.

## 0.2.2 — 2026-09-05

- Plus de fenêtre « Installez les compétences Streamlit » ni de bouton
  « Déployer » dans l'application : interface lecteur, sans options de développeur.

## 0.2.1 — 2026-09-05

- Un lanceur téléchargé seul (sans le projet) récupère lui-même l'outil complet
  dans un dossier `ANEMONE` à côté de lui, puis démarre. Un seul fichier suffit
  pour livrer l'outil.

## 0.2.0 — 2026-09-05

- Mise à jour automatique proposée au lancement (graphe et `.venv` préservés).
- Panneau « Diagnostic » dans la barre latérale et script `outils/diagnostic.py`.
- Numéro de version affiché dans l'application.
- Intégration continue : tests sur Windows, macOS et Linux, lanceurs inclus.

## 0.1.0 — 2026-09-05

- Première livraison en un clic (Windows, macOS, Linux).
- Lecture de matrices réelles ROOT (TTree, RNTuple) et CSV.
- Isolation Forest, vue 4D, Architecte critique, graphe de connaissances persistant.
- Configuration Streamlit livrée : aucune invite au premier lancement, écoute locale.
