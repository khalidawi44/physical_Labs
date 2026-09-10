# Alliance Groupe — Guide de démarrage (une page)

La cartographie 4D d'Alliance Groupe (`alliance_cartographie.py`) : elle montre
à des experts toute la mécanique d'Alliance — GitHub ⇆ repo local synchronisés,
intégration continue, site en production, audit web **AG-Audit** et audit expert
**AG-Kali**, livrables — sous forme d'un graphe stratifié animé. Rien n'est
scanné en direct : c'est un modèle éditable.

## 1. Prérequis

- Un ordinateur Windows 10/11, macOS ou Linux.
- **Python 3.11 ou plus récent**. Sous Windows, le lanceur propose de
  l'installer automatiquement s'il manque. Sinon :
  https://www.python.org/downloads/ (cocher « Add python.exe to PATH »).
- Une connexion internet **uniquement au premier lancement** (téléchargement
  des bibliothèques). Ensuite, l'outil fonctionne hors ligne.

## 2. Lancer l'outil

**Le plus simple (Windows) : `Alliance.bat`.** Un raccourci à double-cliquer,
à poser sur le Bureau ou dans le dossier. Il démarre l'application sans le
prompt e-mail de Streamlit et ouvre le navigateur sur `http://localhost:8502`.

**Ou les lanceurs multi-systèmes :**

1. Placer ce que vous avez reçu où vous voulez : soit le dossier complet
   dézippé, soit **un seul fichier lanceur** (qui télécharge alors l'outil
   complet dans un dossier `ANEMONE` à côté de lui au premier double-clic).
2. Double-cliquer :
   - **Windows** : `lancer_anemone.bat`
   - **macOS** : `lancer_anemone.command` (si macOS refuse : clic droit → Ouvrir)
   - **Linux** : `lancer_anemone.sh` (ou : `bash lancer_anemone.sh`)
3. **Le premier lancement prend 1 à 3 minutes** (les bibliothèques se
   téléchargent). Les lancements suivants prennent quelques secondes.
4. Le navigateur s'ouvre sur l'adresse affichée dans la console.

Pour **arrêter** l'outil : fermer la fenêtre de console.

## 3. Les cinq vues

Dans le menu de gauche (« Vue ») :

- **Présentation (plein écran)** — le mode démo : la carte se raconte étape par
  étape, narration bien visible, boutons *Précédent / Suivant / Recommencer*.
  Idéal pour pitcher devant un expert. C'est la vue par défaut.
- **Carte complète (4D)** — tout allumé : nœuds par couche, liens par nature.
- **Rejeu animé (vidéo)** — la « vidéo » des interactions, du push à la
  remédiation (▶ Lire / Pause / curseur).
- **Parcours étape par étape** — une étape isolée à la fois.
- **Rapport d'exemple (livrable)** — un exemple *fictif* du rapport remis en fin
  d'audit : constats par gravité, devis chiffré, et le **rapport Word brandé
  téléchargeable**. Montre à un prospect ce qu'il recevrait.

## 4. Modifier ce qui est montré

Tout vient de `alliance_modele.py` : les composants (`NOEUDS`), leurs
interactions (`ARETES`), les étapes du rejeu (`SEQUENCE`), la chaîne d'outils
Kali (`OUTILS_KALI`) et le rapport d'exemple (`FINDINGS_DEMO`, `DEVIS_DEMO`).
Modifier ce fichier suffit à changer la carte.

## 5. Mises à jour

À chaque lancement (via les lanceurs `lancer_anemone.*`), l'outil vérifie si une
nouvelle version est publiée et propose « Installer maintenant ? [O/n] » —
Entrée = oui. Le `.venv` et vos fichiers locaux sont conservés. Sans connexion,
l'outil démarre normalement.

## 6. Où vont vos données

**Tout reste sur votre machine.** L'outil n'envoie rien à l'extérieur et n'est
visible que depuis votre ordinateur (écoute sur `localhost` uniquement). Aucune
donnée métier n'est collectée.

## 7. Désinstaller

Supprimer le dossier. Rien n'a été installé ailleurs (l'environnement Python
isolé `.venv` est à l'intérieur du dossier).

## 8. En cas de problème

Si l'application ne démarre pas : ouvrir un terminal dans le dossier et taper
`python outils/diagnostic.py` (écrit `diagnostic_alliance.txt`), puis envoyer ce
fichier au support.

| Symptôme | Cause probable | Que faire |
|---|---|---|
| « Python est introuvable » | Python absent ou trop ancien | Installer Python 3.11+ puis relancer |
| La console reste longtemps sans rien afficher au premier lancement | Téléchargement des bibliothèques | Attendre 1 à 3 minutes |
| « Installation des dépendances échouée » | Pas de connexion internet ou proxy | Vérifier la connexion, relancer |
| Linux : « Impossible de créer l'environnement .venv » | Paquet `python3-venv` absent (Debian/Ubuntu) | `sudo apt install python3-venv` puis relancer |
| macOS : « développeur non identifié » | Protection Gatekeeper | Clic droit sur `lancer_anemone.command` → Ouvrir |
| Windows : « Avertissement de sécurité » à l'ouverture du .bat | Fichier téléchargé depuis internet | Cliquer sur « Exécuter » |
| La vue Rapport plante au clic | `python-docx` pas installé | Le lanceur l'installe ; sinon `pip install python-docx` dans le `.venv` |
| Le navigateur ne s'ouvre pas | Navigateur par défaut non détecté | Ouvrir à la main l'adresse affichée dans la console |
