# Journal des versions — A.N.E.M.O.N.E

Le numéro de version publié est celui du fichier `VERSION` sur la branche `main`.
Les lanceurs le comparent au démarrage et proposent la mise à jour.

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
