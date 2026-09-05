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

1. Dézipper le dossier reçu où vous voulez (Documents, Bureau, clé USB…).
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

## 3. Charger vos données

Dans la barre latérale, trois modes :

- **Fichier téléversé** : glisser un `.root`, `.csv`, `.tsv`, `.txt` ou `.dat`
  (jusqu'à 4 Go). Pour un `.root`, choisir ensuite la table (TTree / RNTuple).
- **Chemin local** : coller le chemin complet du fichier sur votre disque.
  Aucune limite de taille, aucune copie du fichier.
- **Démo synthétique** : données fictives, clairement étiquetées sans valeur
  physique, pour découvrir l'interface.

Le champ « Événements max » permet de ne lire qu'une partie d'un gros fichier.

## 4. Où vont vos données

- **Tout reste sur votre machine.** L'outil n'envoie rien à l'extérieur et
  n'est visible que depuis votre ordinateur (écoute sur `localhost` uniquement).
- Le graphe de connaissances (vos observations, les objections et hypothèses de
  l'Architecte, vos réfutations) est sauvegardé dans `anemone_graphe.json`
  dans le dossier de l'outil. Vous pouvez l'exporter, l'importer ou changer
  ce chemin depuis la barre latérale.
- Vos fichiers de données ne sont jamais modifiés.

## 5. Désinstaller

Supprimer le dossier. Rien n'a été installé ailleurs (l'environnement Python
isolé `.venv` est à l'intérieur du dossier).

## 6. En cas de problème

| Symptôme | Cause probable | Que faire |
|---|---|---|
| « Python est introuvable » | Python absent ou trop ancien | Installer Python 3.11+ puis relancer |
| La console reste longtemps sans rien afficher au premier lancement | Téléchargement des bibliothèques | Attendre 3 à 5 minutes |
| « Installation des dépendances échouée » | Pas de connexion internet ou proxy du labo | Vérifier la connexion, relancer ; hors ligne, demander l'archive avec les bibliothèques incluses |
| Linux : « Impossible de créer l'environnement .venv » | Paquet `python3-venv` absent (Debian/Ubuntu) | `sudo apt install python3-venv` puis relancer |
| macOS : « impossible d'ouvrir, développeur non identifié » | Protection Gatekeeper | Clic droit sur `lancer_anemone.command` → Ouvrir |
| Le navigateur ne s'ouvre pas | Navigateur par défaut non détecté | Ouvrir `http://localhost:8501` à la main |
| Fichier trop volumineux au téléversement | Limite 4 Go du navigateur | Utiliser le mode **Chemin local** |
