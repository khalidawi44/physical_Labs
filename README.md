# 🌌 physical_Labs — Projet A.N.E.M.O.N.E

Système d'exploration subatomique & Robot Architecte cognitif. L'outil lit
des **matrices de données réelles** (fichiers ROOT ou CSV), isole l'inconnu par
apprentissage **non supervisé** (Isolation Forest), le cartographie en 4D, et
fait dialoguer le physicien avec un **Architecte** critique dont chaque
réplique est consignée dans un **graphe de connaissances persistant**.


## Lancement en un clic

1. Télécharger le dépôt : bouton vert **Code → Download ZIP** sur GitHub (ou la
   dernière *Release*), puis dézipper où vous voulez.
2. **Windows** : double-cliquer sur `lancer_anemone.bat`.
   **macOS** : double-cliquer sur `lancer_anemone.command` (si macOS refuse :
   clic droit → Ouvrir).
   **Linux** : double-cliquer sur `lancer_anemone.sh`, ou dans un terminal :
   `bash lancer_anemone.sh`.

Le lanceur cherche Python 3.11+ (sous Windows, il propose de l'installer
automatiquement via `winget` s'il manque), crée un environnement isolé `.venv`
dans le dossier, installe les dépendances au premier démarrage (3 à 5 minutes,
ensuite quelques secondes), puis ouvre l'outil dans le navigateur sur
`http://localhost:8501`. Rien n'est installé hors du dossier : pour
désinstaller, supprimer le dossier.

Seul prérequis : **Python 3.11 ou plus récent**
(https://www.python.org/downloads/, cocher « Add python.exe to PATH »).
Le pas-à-pas complet pour l'utilisateur final est dans `GUIDE_DEMARRAGE.md`.

## Configuration livrée

`.streamlit/config.toml` s'applique automatiquement au lancement :

- pas d'invite « Email » de Streamlit au premier démarrage, aucune statistique
  d'usage envoyée ;
- l'outil n'écoute que sur `localhost` : invisible depuis le réseau du labo ;
- téléversement navigateur limité à 4 Go ; au-delà, utiliser le mode
  **Chemin local** de la barre latérale (aucune limite, aucune copie).

La variable d'environnement `ANEMONE_PHYSICIEN` pré-remplit le nom du
physicien consigné dans le graphe (sinon, champ libre dans la barre latérale).

## Installation manuelle

```bash
git clone https://github.com/khalidawi44/physical_labs && cd physical_labs
pip install -r requirements.txt
streamlit run anemone_master.py
```

`requirements.txt` fige les versions exactes testées ; les tests sont passés
avec ces versions sous Python 3.11.

Tests :

```bash
pip install pytest
python -m pytest tests -q
```

## Données réelles (.root / .csv)

La fonction `analyser_fichier_physique(source, nom_fichier, arbre, max_evenements)`
remplace l'ancien générateur fictif :

- **CSV / TSV / DAT** : séparateur détecté automatiquement, lignes `#` ignorées.
- **ROOT** : lecture par `uproot` d'un **TTree** ou d'un **RNTuple** (choix de
  la table dans la barre latérale). Seules les branches numériques scalaires
  sont gardées (les branches vectorielles / jagged sont ignorées).
- Nettoyage : colonnes non numériques et constantes écartées, lignes
  incomplètes ou infinies retirées. Un rapport de nettoyage est affiché.
- Trois modes dans la barre latérale : fichier téléversé, chemin local, ou
  **démo synthétique** (clairement étiquetée : aucune valeur physique).
  Un exemple CSV synthétique est fourni dans `exemples/detecteur_demo.csv`.

## Détection de l'inconnu

`detecter_inconnu(df, colonnes, contamination, seed)` : Isolation Forest sur
les variables choisies. Ajoute `Inconnu` (-1 = isolé, 1 = conforme) et
`Score_anomalie`. Le taux de contamination et la graine sont réglables.

## Visualisation 4D

- 🟢 Physique conforme : points verts estompés.
- 🔥 Anomalies : échelle thermique sur la 4ᵉ dimension choisie (couleur),
  reliées dans l'ordre de l'axe X.
- ➡️ Vecteur de tendance : axe principal (SVD) du nuage d'anomalies, tracé
  à travers son centroïde.
- Les axes X/Y/Z/couleur sont libres ; des rôles (temps, énergie,
  température) sont proposés d'après le nom des colonnes.

## L'Architecte : rien d'inventé, tout calculé

Toutes ses répliques s'appuient sur `diagnostiquer()` (test de
Kolmogorov–Smirnov, d de Cohen, corrélations internes aux anomalies,
géométrie SVD, concentration temporelle). Aucun chiffre n'est écrit en dur.

- **⚠️ Objection** : cherche un biais instrumental (corrélation forte entre la
  variable dominante et une autre, notamment thermique), un épisode
  transitoire, et exige un test de robustesse au taux de contamination.
- **🔮 Hypothèse** : conjecture « aveugle » déduite de la géométrie du nuage
  (décalage en σ, axe principal, part de variance expliquée).
- **🛡️ Preuves** : plaidoyer chiffré. Il **verrouille l'écran** uniquement si
  une variable passe simultanément `p < 0.001` et `|d| ≥ 1` ; sinon il cède
  honnêtement. Le déverrouillage exige une **réfutation** écrite, consignée
  dans le graphe.

## Graphe de connaissances persistant

Classe `GrapheConnaissances` (nœuds typés + arêtes étiquetées), stockée dans
`st.session_state["graphe"]` et :

- **sauvegardée automatiquement** dans un fichier JSON (`anemone_graphe.json`
  par défaut, désactivable) pour survivre à la fermeture de l'onglet ;
- exportable / importable (fusion) en JSON depuis la barre latérale ;
- visualisée en réseau (plotly + networkx) sous la vue 4D ;
- consultable en chronologie dans « Historique du débat ».

Types de nœuds : `jeu_de_donnees`, `parametres`, `anomalies`, `observation`,
`objection`, `hypothese`, `defense`, `refutation`.
Relations : `porte_sur`, `applique_a`, `conteste`, `repond_a`, `prolonge`,
`defend`, `refute`.
