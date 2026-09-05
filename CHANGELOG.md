# Journal des versions — A.N.E.M.O.N.E

Le numéro de version publié est celui du fichier `VERSION` sur la branche `main`.
Les lanceurs le comparent au démarrage et proposent la mise à jour.

## 0.9.0 — 2026-09-05

- **Vidéo de l'événement de collision** (`anemone_evenement.py`, section
  « 🎥 Événement de collision » sous la vue 4D) : pour tout fichier qui décrit
  les impulsions des particules (px, py, pz ou pt, η, φ, charge facultative),
  trajectoires tracées depuis le vertex dans un schéma de détecteur aux
  dimensions de CMS (hélices dans B = 3,8 T selon la charge, droites sinon,
  énergie transverse manquante en pointillé), animées image par image.
  Choix de l'événement parmi les isolés, tous les événements, ou les
  événements d'une bosse du run de découverte (par exemple un candidat Z).

## 0.8.0 — 2026-09-05

- **Run de découverte** (`anemone_decouverte.py`, section « 🏁 Run de
  découverte » et ligne de commande) : une hypothèse facultative (« M ~ 91 ± 3 »
  ou texte libre), des données au choix (fichier chargé, dossier de la campagne,
  ou toutes les données réelles du CERN téléchargées automatiquement), un
  bouton. L'outil chasse les bosses, soumet chacune aux autres explications
  (fluctuation à 5 σ après correction du nombre de fenêtres, tenue dans chaque
  moitié du run, autre découpage, bord ou seuil, présence dans le run de
  référence, coïncidence avec une résonance connue de la table PDG, étroitesse),
  teste l'hypothèse à l'endroit indiqué sans facteur d'essais, et écrit une
  **thèse** (Markdown + JSON, empreintes, versions) dans `theses/`, consignée
  dans le graphe. « Thèse candidate » seulement si une bosse étroite sur une
  masse passe toutes les épreuves et ne coïncide avec rien de connu.
- **Chasse aux bosses** (`anemone_bosse.py`) : histogramme log ou linéaire,
  fond lisse ajusté sur les bandes latérales (quadratique robuste, fenêtre non
  testée si le fond ne décrit pas les bandes), probabilité de Poisson,
  correction de Bonferroni, fusion des fenêtres contiguës, resserrement au cœur
  de l'excès. Validée à l'aveugle sur les données CMS 2011 : ω, φ, J/ψ, ψ(2S),
  Υ(1S, 2S, 3S) et Z (μμ et ee) retrouvés, zéro fausse bosse à 5 σ sur un fond
  lisse simulé.
- **Masse invariante dérivée** `M_paire` quand un fichier a (E, px, py, pz) ou
  (pt, η, φ) de deux objets sans colonne de masse ; les masses passent en tête
  des variables analysées par défaut, les charges et types en queue.

## 0.7.0 — 2026-09-05

- **Mode « Découverte guidée »** (`anemone_guide.py`), pour les personnes sans
  formation en physique : choix « Niveau » en haut de la barre latérale, ou
  bouton « Je ne suis pas physicien : guide-moi » au premier écran. Le résultat
  est lu en langage courant (combien d'événements, combien d'isolés, quelle
  variable les distingue, niveau de preuve en quatre paliers, points de
  vigilance, et maintenant ?), avec un glossaire. Chaque phrase est calculée
  depuis le diagnostic ; le palier « très net » reprend exactement les seuils
  de verrouillage de l'Architecte. Les réglages techniques sont repliés dans
  « Réglages avancés », le bureau de l'Architecte s'affiche sur demande, la vue
  4D reste. Le mode Expert est inchangé et reste le défaut.

## 0.6.3 — 2026-09-05

- **Lanceur : plus de « Port 8501 is not available »**. Le lanceur passe par
  `outils/lancer.py` : si A.N.E.M.O.N.E tourne déjà depuis ce dossier (double
  clic une seconde fois, fenêtre précédente restée ouverte), il rouvre
  simplement le navigateur dessus ; si le port 8501 est pris par un autre
  programme, il prend le port libre suivant et affiche l'adresse. Fermer la
  fenêtre arrête bien le serveur (plus de processus orphelin sur le port).

## 0.6.2 — 2026-09-05

- **Premier écran « Commencer »** : rien de chargé → trois boutons en un clic
  (analyser l'exemple livré, démo synthétique, ouvrir un fichier réel du CERN)
  font apparaître la vue 4D et l'Architecte sans passer par la barre latérale.
  Sans variable sélectionnée, un avertissement remplace l'écran vide.
- **Vue 4D en premier** : dès qu'un fichier est ouvert, la visualisation et le
  bureau de l'Architecte sont en haut de page ; Albert, les données du CERN et
  la campagne passent en dessous, repliés.
- L'écran n'attend plus le réseau au lancement : le catalogue CERN affiché est
  celui embarqué (mêmes tailles et sommes de contrôle que l'API, vérifié) ;
  un bouton relit l'API sur demande. Auparavant chaque affichage interrogeait
  opendata.cern.ch (jusqu'à 30 s d'écran vide derrière un pare-feu).
- La présence d'un fichier téléchargé n'est plus re-vérifiée par somme de
  contrôle à chaque interaction (mémorisée tant que taille et date ne changent pas).

## 0.6.1 — 2026-09-05

- Albert, après sa première recherche sur les dix tranches CMS 2010 : il
  n'apprend plus que des identités (R² ≥ 0,995), il désigne comme « déduite »
  la grandeur composée d'une identité (E dans E² = px² + py² + pz², pt dans
  pt² = px² + py²), et son cahier ne répète plus une réfutation par tranche.
- Les noms de colonnes CSV sont nettoyés de leurs espaces parasites
  (« px1  » dans le fichier CMS 2010).

## 0.6.0 — 2026-09-05

- **Albert, physicien robot** (`anemone_physicien.py`) : il apprend des données
  les relations démontrables entre variables (identités quadratiques comme
  E² = px² + py² + pz², variables apparentées), débat avec l'Architecte en
  réfutant avec preuve calculée, pose au physicien les questions qu'il ne peut
  pas trancher, et **cherche seul** dans un dossier de runs sous plusieurs
  stratégies d'analyse : trouvaille = « solide » sous au moins deux stratégies.
  Cahier de laboratoire (Markdown + JSON) dans `cahier_albert/`.
- **Base de connaissances** `anemone_connaissances.json` : relations apprises ou
  déclarées, questions ouvertes, leçons. L'Architecte et la campagne
  n'accusent plus une paire de variables connue.
- **Deux modes** dans la barre latérale : « avec Albert » (autonome et
  collaboratif) ou « Fred seul avec l'Architecte » (Albert n'agit pas, seules
  les relations déclarées par une personne comptent).
- Réfutation : case « Enseigner à l'outil : X ↔ Y est une relation connue ».
- Balayage de robustesse : la variable dominante est jugée stable si une variable
  structurellement liée (corrélée chez les conformes, ou relation connue) prend le
  relais ; E et pt qui se relaient ne sont plus une « fragilité ».
- Albert apprend les relations sur les seuls événements conformes : une
  corrélation portée par les anomalies n'est jamais blanchie en relation connue.

## 0.5.0 — 2026-09-05

- L'Architecte distingue une **corrélation structurelle** (présente aussi chez
  les événements conformes : cinématique, par exemple impulsion ↔ énergie d'une
  même particule) d'un **biais propre aux anomalies** (corrélation qui n'apparaît,
  ou ne se renforce nettement, que chez les isolés). Seule la seconde vaut
  objection ou verdict « suspect ». Le diagnostic expose désormais les
  corrélations chez les conformes.

## 0.4.0 — 2026-09-05

- **Données réelles en un clic** : catalogue de 19 fichiers d'événements réels
  du détecteur CMS publiés par le CERN Open Data (enregistrements 545 et 700),
  téléchargement vérifié par somme de contrôle, ouverture dans la vue
  interactive ou campagne sur les dix tranches de 2010 avec référence.
  Ligne de commande : `python outils/donnees_ouvertes.py --tout`.
- Les colonnes d'identifiants (Run, Event, …) sont écartées par défaut de la
  détection, dans la vue interactive comme en campagne.

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
