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

## 3. Charger vos données

Dans la barre latérale, trois modes :

- **Fichier téléversé** : glisser un `.root`, `.csv`, `.tsv`, `.txt` ou `.dat`
  (jusqu'à 4 Go). Pour un `.root`, choisir ensuite la table (TTree / RNTuple).
- **Chemin local** : coller le chemin complet du fichier sur votre disque.
  Aucune limite de taille, aucune copie du fichier.
- **Démo synthétique** : données fictives, clairement étiquetées sans valeur
  physique, pour découvrir l'interface.

Le champ « Événements max » permet de ne lire qu'une partie d'un gros fichier.

## 4. Mises à jour

À chaque lancement, l'outil vérifie si une nouvelle version est publiée. Si
oui, la console affiche « Nouvelle version disponible » et demande
« Installer maintenant ? [O/n] ». Appuyer sur Entrée installe la mise à jour,
puis l'outil démarre. Vos observations, votre graphe de connaissances et vos
exports sont conservés. Taper `n` reporte la mise à jour au prochain lancement.
Sans connexion, l'outil démarre normalement.

## 5. Où vont vos données

- **Tout reste sur votre machine.** L'outil n'envoie rien à l'extérieur et
  n'est visible que depuis votre ordinateur (écoute sur `localhost` uniquement).
- Le graphe de connaissances (vos observations, les objections et hypothèses de
  l'Architecte, vos réfutations) est sauvegardé dans `anemone_graphe.json`
  dans le dossier de l'outil. Vous pouvez l'exporter, l'importer ou changer
  ce chemin depuis la barre latérale.
- Vos fichiers de données ne sont jamais modifiés.

## 6. Désinstaller

Supprimer le dossier. Rien n'a été installé ailleurs (l'environnement Python
isolé `.venv` est à l'intérieur du dossier).

## 7. En cas de problème

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
| Le navigateur ne s'ouvre pas | Navigateur par défaut non détecté | Ouvrir `http://localhost:8501` à la main |
| Fichier trop volumineux au téléversement | Limite 4 Go du navigateur | Utiliser le mode **Chemin local** |
