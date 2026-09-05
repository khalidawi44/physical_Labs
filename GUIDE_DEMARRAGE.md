# A.N.E.M.O.N.E — Guide de démarrage (une page)

Outil d'exploration de matrices de physique (fichiers ROOT ou CSV) : isolation
non supervisée de l'inconnu, cartographie 4D, dialogue avec un Architecte
critique dont chaque réplique est calculée depuis vos données et consignée
dans un graphe de connaissances.

## 1. Prérequis

- Un ordinateur Windows 10/11, macOS ou Linux.
- **Python 3.11 ou plus récent**. Sous Windows, le lanceur propose de
  l'installer automatiquement s'il manque. Sinon :
  https://www.python.org/downloads/ (cocher « Add python.exe to PATH »).
- Une connexion internet **uniquement lors du premier lancement** (téléchargement
  des bibliothèques scientifiques). Ensuite, l'outil fonctionne hors ligne.

## 2. Lancer l'outil

1. Placer ce que vous avez reçu où vous voulez (Documents, Bureau, clé USB…) :
   soit le dossier complet dézippé, soit **un seul fichier lanceur**. Dans ce
   second cas, le lanceur télécharge l'outil complet dans un dossier `ANEMONE`
   à côté de lui au premier double-clic.
2. Double-cliquer :
   - **Windows** : `lancer_anemone.bat`
   - **macOS** : `lancer_anemone.command` (si macOS refuse : clic droit → Ouvrir)
   - **Linux** : `lancer_anemone.sh` (ou dans un terminal : `bash lancer_anemone.sh`)
3. Une fenêtre de console s'ouvre et affiche l'avancement en trois étapes.
   **Le premier lancement prend 3 à 5 minutes** : c'est normal, les
   bibliothèques se téléchargent. Les lancements suivants prennent quelques
   secondes.
4. Le navigateur s'ouvre sur `http://localhost:8501`. Si ce n'est pas le cas,
   ouvrir cette adresse à la main.

Pour **arrêter** l'outil : fermer la fenêtre de console.

## 2 bis. Pas physicien ? Le mode découverte guidée

En haut de la barre latérale, « Niveau » : **Découverte guidée** ou **Expert**.
Au premier écran, le bouton « 🧭 Je ne suis pas physicien : guide-moi » fait
la même chose. En mode guidé, l'outil explique ce qu'il a trouvé en langage
courant : combien d'événements, combien d'isolés, la variable qui les
distingue, un niveau de preuve en quatre paliers (⚪ insuffisant, 🟡 faible,
🟠 net, 🔴 très net), les points de vigilance (lien suspect entre deux
variables, isolés concentrés dans le temps) et quoi faire ensuite. Un glossaire
définit chaque mot. Rien n'est caché : les réglages sont dans « Réglages
avancés » et le bureau de l'Architecte s'affiche d'une case à cocher.

## 2 ter. Faire un run de découverte

Section « 🏁 Run de découverte », présente dès le premier écran. Écrivez une
hypothèse si vous en avez une (« M_paire ~ 91 ± 3 » est compris comme un
endroit précis à tester ; sinon texte libre), choisissez les données (le
fichier chargé, le dossier de la campagne, ou toutes les données réelles du
CERN que l'outil télécharge lui-même), cliquez. L'outil cherche les bosses sur
les masses, essaie de les expliquer autrement, teste votre hypothèse et écrit
une thèse dans `theses/`, aussi téléchargeable. Un verdict rouge « thèse
candidate » ne veut pas dire découverte : il veut dire qu'aucune explication
calculable n'a été trouvée, et qu'un physicien doit maintenant vérifier la
sélection, la simulation du fond et la résolution.

## 3. Charger vos données

Au premier écran, rien n'est chargé : la vue 4D n'apparaît qu'une fois un
fichier ouvert, et l'analyse se lance alors d'elle-même (il n'y a pas de bouton
« Analyser » : changer une variable ou un réglage relance le calcul). Le bloc
« 🚀 Commencer » propose trois départs en un clic : **l'exemple livré**
(`exemples/detecteur_demo.csv`, synthétique), la **démo synthétique**, ou un
**fichier réel du CERN** (candidats Z → μμ, ~1 Mo, téléchargé et vérifié).

Pour vos propres fichiers, dans la barre latérale (flèche » en haut à gauche
si elle est repliée), trois modes :

- **Fichier téléversé** : glisser un `.root`, `.csv`, `.tsv`, `.txt` ou `.dat`
  (jusqu'à 4 Go). Pour un `.root`, choisir ensuite la table (TTree / RNTuple).
- **Chemin local** : coller le chemin complet du fichier sur votre disque.
  Aucune limite de taille, aucune copie du fichier.
- **Démo synthétique** : données fictives, clairement étiquetées sans valeur
  physique, pour découvrir l'interface.

Le champ « Événements max » permet de ne lire qu'une partie d'un gros fichier.

## 4. Pas encore de données ? Des vraies, en un clic

Ouvrez « 🌐 Données réelles en un clic ». Le catalogue liste des fichiers
d'événements réels du détecteur CMS publiés par le CERN. Choisissez-en un et
cliquez « Télécharger et ouvrir » : il est téléchargé, vérifié, et s'ouvre dans
la vue interactive. « Tout télécharger → campagne » récupère tout le catalogue
et prépare une campagne sur dix tranches d'un même run avec le fichier complet
en référence.

## 5. Laisser l'outil travailler seul : la campagne

Vous avez un dossier de runs ? Ouvrez « 🧪 Campagne automatique », collez le
chemin du dossier (et, si vous en avez un, celui d'un run de calibration en
référence), puis « Analyser le dossier ». L'outil analyse chaque run, refait
lui-même les tests de robustesse, et vous rend une liste classée :

- 🟢 **solide** : à regarder en premier, la séparation tient à tout ;
- 🟠 **suspect** : nette mais corrélée à une autre variable (température ?) ou
  concentrée dans un épisode transitoire ;
- 🟡 **fragile** : change quand on fait varier les réglages ;
- ⚪ **queues du fond** / **faible** : rien de plus que le fond ;
- ⚫ **insuffisant**, 🔴 **erreur**.

Chaque verdict est accompagné de son « pourquoi » chiffré. Le rapport complet
est écrit dans le dossier `rapports/`. Cochez « Veille » pour que tout nouveau
fichier déposé dans le dossier soit analysé automatiquement tant que la page est
ouverte. Un run vous intrigue ? « Ouvrir » le charge dans la vue interactive
pour en débattre avec l'Architecte.

## 6. Albert, votre collègue robot (facultatif)

En haut de la barre latérale, choisissez « Avec Albert » ou « Fred seul avec
l'Architecte ». Avec Albert : il apprend de vos fichiers les relations entre
variables, débat avec l'Architecte à votre place quand il a une preuve, et vous
pose seulement les questions qu'il ne peut pas trancher (un clic : « Relation
connue » ou « Vrai biais »). « Albert, cherche seul » l'envoie explorer le
dossier de la campagne sous plusieurs stratégies ; il revient avec un cahier de
laboratoire et ne présente comme trouvaille que ce qui tient sous plusieurs
angles. Seul : Albert n'agit pas, l'outil ne retient que ce que vous avez
déclaré vous-même.

## 7. Mises à jour

À chaque lancement, l'outil vérifie si une nouvelle version est publiée. Si
oui, la console affiche « Nouvelle version disponible » et demande
« Installer maintenant ? [O/n] ». Appuyer sur Entrée installe la mise à jour,
puis l'outil démarre. Vos observations, votre graphe de connaissances et vos
exports sont conservés. Taper `n` reporte la mise à jour au prochain lancement.
Sans connexion, l'outil démarre normalement.

## 8. Où vont vos données

- **Tout reste sur votre machine.** L'outil n'envoie rien à l'extérieur et
  n'est visible que depuis votre ordinateur (écoute sur `localhost` uniquement).
- Le graphe de connaissances (vos observations, les objections et hypothèses de
  l'Architecte, vos réfutations) est sauvegardé dans `anemone_graphe.json`
  dans le dossier de l'outil. Vous pouvez l'exporter, l'importer ou changer
  ce chemin depuis la barre latérale.
- Vos fichiers de données ne sont jamais modifiés. Les rapports de campagne
  sont écrits dans `rapports/`, dans le dossier de l'outil.

## 9. Désinstaller

Supprimer le dossier. Rien n'a été installé ailleurs (l'environnement Python
isolé `.venv` est à l'intérieur du dossier).

## 10. En cas de problème

Depuis l'application : barre latérale → « 🩺 Diagnostic » → « Télécharger le
rapport », et envoyer le fichier au support. Si l'application ne démarre pas :
ouvrir un terminal dans le dossier et taper `python outils/diagnostic.py`.

| Symptôme | Cause probable | Que faire |
|---|---|---|
| « Python est introuvable » | Python absent ou trop ancien | Installer Python 3.11+ puis relancer |
| La console reste longtemps sans rien afficher au premier lancement | Téléchargement des bibliothèques | Attendre 3 à 5 minutes |
| « Installation des dépendances échouée » | Pas de connexion internet ou proxy du labo | Vérifier la connexion, relancer ; hors ligne, demander l'archive avec les bibliothèques incluses |
| Linux : « Impossible de créer l'environnement .venv » | Paquet `python3-venv` absent (Debian/Ubuntu) | `sudo apt install python3-venv` puis relancer |
| macOS : « impossible d'ouvrir, développeur non identifié » | Protection Gatekeeper | Clic droit sur `lancer_anemone.command` → Ouvrir |
| Windows : fenêtre « Avertissement de sécurité » à l'ouverture du .bat | Fichier téléchargé depuis internet | Cliquer sur « Exécuter » |
| La page s'ouvre mais pas de vue 4D ni d'analyse | Aucun fichier chargé : la vue 4D n'existe qu'avec des données | Cliquer un des trois boutons « Commencer », ou charger un fichier dans la barre latérale |
| « Port 8501 is not available » | Un A.N.E.M.O.N.E (ou un autre programme) occupe déjà le port ; corrigé en 0.6.3 | Mettre à jour (proposé au lancement) : le lanceur rouvre l'instance en marche ou prend le port suivant. Sinon, fermer l'autre fenêtre A.N.E.M.O.N.E |
| Le navigateur ne s'ouvre pas | Navigateur par défaut non détecté | Ouvrir à la main l'adresse affichée dans la console (`http://localhost:8501` en général) |
| Fichier trop volumineux au téléversement | Limite 4 Go du navigateur | Utiliser le mode **Chemin local** |
