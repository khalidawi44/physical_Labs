# 🛰️ Alliance Groupe — Cartographie 4D de l'infrastructure

Outil de **démonstration** : il cartographie en 4D (trois axes + la couche en
couleur) toute la mécanique d'Alliance Groupe et la rejoue comme une animation,
pour la montrer à des experts. On y voit le **dépôt GitHub synchronisé avec le
repo local**, l'intégration continue, le site en production, l'audit web
**AG-Audit** et l'audit expert **AG-Kali** sous Kali Linux avec sa chaîne
d'outils complète, puis les livrables (rapport DOCX brandé, devis).

C'est un **modèle éditable** (`alliance_modele.py`) : rien n'est scanné en
direct, la structure et les interactions se modifient à la main. L'application
est `alliance_cartographie.py` ; le lanceur l'ouvre directement.

Quatre vues, choisies dans le menu de gauche :

- **Présentation (plein écran)** — le mode démo : la carte se raconte étape par
  étape, narration bien visible, navigation *Précédent / Suivant / Recommencer*
  et scénario complet pour préparer le pitch. C'est la vue par défaut.
- **Carte complète (4D)** — tout allumé : nœuds colorés par couche, liens par
  nature (synchronisation, déploiement, audit, livrable).
- **Rejeu animé (vidéo)** — la « vidéo » des interactions, du push à la
  remédiation, avec ▶ Lire / Pause / curseur.
- **Parcours étape par étape** — une étape isolée à la fois, le reste estompé.
- **Rapport d'exemple (livrable)** — un exemple *fictif* du rapport remis en fin
  d'audit : constats classés par gravité, devis de remédiation chiffré, et le
  **rapport Word brandé téléchargeable**. Montre à un prospect ce qu'il recevrait.

> **Moteur A.N.E.M.O.N.E (physique) conservé.** Les modules d'exploration
> subatomique (`anemone_master.py` et compagnie, avec leur cartographie 4D, le
> run de découverte, l'analyse à l'aveugle et le physicien robot Albert) restent
> dans le dépôt et dans l'historique git : ils ne sont simplement plus l'outil
> ouvert par le lanceur. Description ci-dessous.

---

## (Ancien) Projet A.N.E.M.O.N.E — exploration subatomique

Système d'exploration subatomique & Robot Architecte cognitif. L'outil lit
des **matrices de données réelles** (fichiers ROOT ou CSV), isole l'inconnu par
apprentissage **non supervisé** (Isolation Forest), le cartographie en 4D, et
fait dialoguer le physicien avec un **Architecte** critique dont chaque
réplique est consignée dans un **graphe de connaissances persistant**.


## Lancement en un clic

**Le plus simple : un seul fichier.** Envoyer au chercheur le lanceur de son
système (`lancer_anemone.bat` pour Windows, `lancer_anemone.command` pour
macOS, `lancer_anemone.sh` pour Linux). Double-cliqué seul, il télécharge
l'outil complet dans un dossier `ANEMONE` à côté de lui, puis démarre.

**Ou le dossier complet :**

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
`http://localhost:8501` (ou le port libre suivant si celui-ci est pris ; un
second double-clic rouvre simplement l'outil déjà en marche). Rien n'est
installé hors du dossier : pour désinstaller, supprimer le dossier.

Seul prérequis : **Python 3.11 ou plus récent**
(https://www.python.org/downloads/, cocher « Add python.exe to PATH »).
Le pas-à-pas complet pour l'utilisateur final est dans `GUIDE_DEMARRAGE.md`,
l'historique des versions dans `CHANGELOG.md`, la charte produit (à qui l'outil
s'adresse, ce qu'il promet et ce qu'il ne promet pas) dans `PRODUCT.md`.

## Configuration livrée

`.streamlit/config.toml` s'applique automatiquement au lancement :

- pas d'invite « Email » de Streamlit au premier démarrage, aucune statistique
  d'usage envoyée ;
- l'outil n'écoute que sur `localhost` : invisible depuis le réseau du labo ;
- téléversement navigateur limité à 4 Go ; au-delà, utiliser le mode
  **Chemin local** de la barre latérale (aucune limite, aucune copie).

La variable d'environnement `ANEMONE_PHYSICIEN` pré-remplit le nom du
physicien consigné dans le graphe (sinon, champ libre dans la barre latérale).

## Mises à jour automatiques

La branche `main` est la version publiée. À chaque lancement, le lanceur
compare le fichier `VERSION` local à celui de `main` et, s'il est plus récent,
propose d'installer la nouvelle version (Entrée = oui). Le graphe de
connaissances, les exports du physicien et le `.venv` ne sont jamais touchés.
Hors ligne, l'outil démarre normalement.

**Pour publier une mise à jour** (côté mainteneur) :

1. Incrémenter `VERSION` (par exemple `0.2.0` → `0.2.1`) et compléter `CHANGELOG.md`.
2. Fusionner sur `main` : les tests GitHub Actions doivent être verts
   (Windows, macOS, Linux, lanceurs compris).
3. Tous les utilisateurs se voient proposer la mise à jour à leur prochain lancement.

Variables : `ANEMONE_SANS_MAJ=1` désactive la vérification,
`ANEMONE_MAJ_AUTO=1` installe sans demander.

## Diagnostic

En cas de problème, le chercheur peut envoyer un rapport (versions, système,
fichiers présents ; aucune donnée de physique) :

- depuis l'application : barre latérale → « 🩺 Diagnostic » → Télécharger ;
- si l'application ne démarre pas : `python outils/diagnostic.py` écrit
  `diagnostic_anemone.txt` dans le dossier de l'outil.

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

## Données réelles en un clic (CERN Open Data)

Section **🌐 Données réelles en un clic** de l'application, ou :

```bash
python outils/donnees_ouvertes.py --liste          # catalogue
python outils/donnees_ouvertes.py 545/Zmumu.csv    # un fichier
python outils/donnees_ouvertes.py --tout           # tout (≈ 90 Mo)
```

Catalogue : 19 fichiers CSV d'événements réels du détecteur CMS publiés par le
CERN, enregistrements [545](https://opendata.cern.ch/record/545) (2011, CC0 :
candidats J/psi, Upsilon, W, Z, spectres dimuon et diélectron) et
[700](https://opendata.cern.ch/record/700) (2010 : dimuons en dix tranches plus
le fichier complet). Chaque téléchargement est vérifié avec la somme de contrôle
Adler-32 publiée par le CERN et rangé dans `donnees/cern_open_data/`. Le bouton
« Tout télécharger → campagne » règle la campagne sur les dix tranches de 2010
avec le fichier complet en référence. Le CERN précise que ces sélections sont
destinées à l'enseignement et ne contiennent qu'un sous-ensemble de
l'information par événement.

Les colonnes d'identifiants (`Run`, `Event`, `*_id`…) sont écartées par défaut
de la détection.

## Albert, physicien robot

Albert (clin d'œil à Einstein) joue le rôle du chercheur, sans aucune physique
en dur. Section **🧑‍🔬 Albert** de l'application, ou en ligne de commande :

```bash
python anemone_physicien.py --chercher /data/runs --reference /data/calibration.root
python anemone_physicien.py run.root        # une leçon sur un fichier
python anemone_physicien.py --etat          # ce que l'outil sait
```

- **Il apprend des données** : relations fonctionnelles démontrables (une
  variable ou son carré déterminée par les autres avec R² ≥ 0,98, par exemple
  E² = px² + py² + pz² + m² ou pt² = px² + py²) et variables apparentées
  (|r| ≥ 0,9 sur tous les événements).
- **Il débat** : soumet le lot isolé à l'Architecte, réfute avec preuve calculée
  ce qu'il peut réfuter, et **pose au physicien** ce qu'il ne peut pas trancher
  (« corrélées chez les isolés seulement : relation connue, ou biais ? »).
  Le physicien répond une fois ; l'outil s'en souvient.
- **Il cherche seul** : plusieurs stratégies d'analyse (grandeurs par défaut,
  grandeurs primitives sans les variables déduites, toutes les grandeurs),
  une campagne complète par stratégie, et ne retient comme **trouvaille** qu'un
  run « solide » sous au moins deux stratégies ; sous une seule, c'est une
  piste. Il écrit son cahier de laboratoire dans `cahier_albert/`.
- **Il enseigne à l'outil** : tout va dans `anemone_connaissances.json` ;
  l'Architecte et la campagne n'accusent plus une paire de variables connue.

**Deux modes**, au choix du physicien, dans la barre latérale : « 🤝 Avec
Albert » (autonome et collaboratif) ou « 👤 Fred seul avec l'Architecte »
(Albert n'agit pas ; seules les relations déclarées par une personne comptent).

## Mode campagne : l'outil analyse seul

Le physicien a un dossier de runs, pas le temps d'ouvrir chaque fichier. Dans
l'application, section **🧪 Campagne automatique** (ou en ligne de commande) :

```bash
python anemone_campagne.py /data/runs --reference /data/calibration.root
python anemone_campagne.py /data/runs --veille 300      # ré-analyse les nouveaux fichiers toutes les 5 min
```

Pour chaque run, l'outil applique la détection avec les réglages courants, puis
mène **lui-même** les expériences que l'Architecte exige :

- **balayage** du taux de contamination (÷2, ×2) et de la graine : le noyau
  d'événements isolés doit rester le même (recouvrement ≥ 50 %) ;
- **fond bootstrap** : les seuls événements conformes sont ré-échantillonnés
  et la détection relancée ; si les queues du fond produisent une séparation
  aussi nette (excès < ×1,5), ce n'est pas un signal ;
- **référence** (facultative) : dérive des distributions du run par rapport au
  run de calibration (KS) et excès d'isolement par rapport à la même détection
  sur la référence.

Il rend un **verdict calculé** avec les seuils de l'Architecte, et classe :
🟢 solide → 🟠 suspect (biais thermique ou épisode transitoire) → 🟡 fragile
(instable au balayage) → ⚪ queues du fond → ⚪ faible → ⚫ insuffisant → 🔴 erreur.
Le physicien ne regarde que le haut de la liste, et ouvre un run en un clic
dans la vue interactive pour débattre avec l'Architecte.

Chaque campagne écrit `rapports/campagne_<horodatage>/` : `rapport.md`
(raisonnement chiffré par run), `resultats.csv`, `resultats.json` (empreintes
SHA-256 des fichiers, paramètres, seuils, versions des paquets : reproductible),
et ajoute un nœud `campagne` relié à un nœud `verdict` par run dans le graphe.

**Veille** : case à cocher dans l'application (nouveaux fichiers analysés
toutes les 60 s tant que la page est ouverte) ou `--veille N` en ligne de
commande, pour un dossier alimenté par l'acquisition.

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
- Deux niveaux, en haut de la barre latérale : **Expert** (défaut, tous les
  réglages, bureau de l'Architecte) et **Découverte guidée** pour les
  non-physiciens : le résultat est lu en langage courant (`anemone_guide.py`),
  niveau de preuve en quatre paliers calculés avec les seuils de l'Architecte,
  points de vigilance (corrélation suspecte, épisode temporel), glossaire ;
  réglages techniques repliés, bureau de l'Architecte sur demande.
- Premier écran « 🚀 Commencer » : sans fichier chargé, trois boutons ouvrent
  en un clic l'exemple livré, la démo, ou un fichier réel du CERN (~1 Mo). La
  vue 4D et l'Architecte apparaissent dès qu'un fichier est ouvert ; l'analyse
  se relance d'elle-même à chaque changement de variable ou de réglage.

## Détection de l'inconnu

`detecter_inconnu(df, colonnes, contamination, seed)` : Isolation Forest sur
les variables choisies. Ajoute `Inconnu` (-1 = isolé, 1 = conforme) et
`Score_anomalie`. Le taux de contamination et la graine sont réglables.

## Run de découverte : de l'hypothèse à la thèse

Section « 🏁 Run de découverte » (ou `python anemone_decouverte.py DOSSIER
--hypothese "M ~ 91 ± 3"`). Une découverte en physique des particules est une
bosse sur un fond lisse, pas un événement isolé : l'outil chasse donc les bosses
(`anemone_bosse.py`) sur les masses invariantes, présentes ou calculées
(`M_paire`), puis cherche pour chacune les autres explications, chacune par un
calcul : fluctuation (5 σ après correction du nombre de fenêtres et de
variables), tenue dans chaque moitié du run, autre découpage, bord ou seuil,
présence dans le run de référence, coïncidence avec une résonance connue
(table PDG), étroitesse. L'hypothèse du physicien est testée à l'endroit exact
qu'il indique, sans facteur d'essais. La thèse (Markdown + JSON dans `theses/`)
rassemble données, empreintes, méthode, épreuves et ce que le physicien doit
vérifier : c'est un dossier de calculs, jamais une conclusion physique.

Validation à l'aveugle sur les données CMS 2011 du CERN : le run retrouve ω, φ,
J/ψ, ψ(2S), Υ(1S, 2S, 3S) et Z (dans μμ et ee) et conclut « instrument validé,
rien de nouveau » (`exemples/these_cms_2011.md`).

## Analyse à l'aveugle

Section « 🙈 Analyse à l'aveugle » (ou `python anemone_aveugle.py sceller
--variable M_paire --bas 88 --haut 94 --hypothese "…" run.csv`, puis `lever`).
La pratique des grandes collaborations : décider de tout avant de regarder la
région du signal. Le protocole est scellé (empreinte SHA-256, date, fichiers
engagés) ; la fenêtre est masquée dans tout l'outil tant que l'aveugle n'est
pas levé, seul le fond attendu y est consultable. Lever l'aveugle est unique
et irréversible : un seul test, sans facteur d'essais, au seuil de 5 σ, écrit
dans `theses/protocoles/` avec les empreintes des données utilisées. Un
protocole altéré ou déjà levé est refusé. Le run de découverte empile aussi la
même masse sur tous les runs (cumul) et montre l'excès run après run ; Albert
lance ce run dans sa recherche autonome.

## Vidéo de l'événement de collision

Sous la vue 4D, pour tout fichier qui décrit les impulsions des particules
(px, py, pz ou pt, η, φ, charge facultative) : trajectoires tracées depuis le
point de collision dans un schéma de détecteur (trajectographe, calorimètres,
chambres à muons, dimensions approximatives de CMS), hélices dans le champ
magnétique selon la charge (R = pt / 0,3 B), énergie transverse manquante en
pointillé, animation image par image (▶). L'événement se choisit parmi les
isolés, tous les événements, ou ceux d'une bosse du run de découverte : on
peut ainsi regarder un candidat Z → μμ réel se dérouler. Aucune simulation :
seules les impulsions mesurées sont utilisées.

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

- **⚠️ Objection** : cherche un biais instrumental, un épisode transitoire, et
  exige un test de robustesse au taux de contamination. Une corrélation forte
  entre la variable dominante et une autre n'est un biais que si elle est
  **propre aux anomalies** : si elle existe aussi chez les conformes (impulsion
  ↔ énergie d'une même particule, par exemple), c'est une propriété des
  données et l'Architecte le dit au lieu d'accuser. Seuils : |r| ≥ 0,5 chez les
  isolés et excès ≥ 0,3 par rapport aux conformes.
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
`objection`, `hypothese`, `defense`, `refutation`, `campagne`, `verdict`.
Albert y consigne ses observations, réfutations et campagnes comme un physicien.
Relations : `porte_sur`, `applique_a`, `conteste`, `repond_a`, `prolonge`,
`defend`, `refute`, `issu_de`.
