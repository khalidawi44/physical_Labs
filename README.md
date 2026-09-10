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

## Cinq vues, dans le menu de gauche

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

## Lancement en un clic

**Le plus simple : `Alliance.bat`** (Windows) — un raccourci à double-cliquer,
à poser sur le Bureau ou dans le dossier. Il trouve tout seul le dossier de
l'outil et le bon Python, installe `python-docx` si besoin, démarre
l'application **sans le prompt e-mail de Streamlit** et ouvre le navigateur sur
`http://localhost:8502`.

**Ou les lanceurs multi-systèmes** (`lancer_anemone.bat` pour Windows,
`lancer_anemone.command` pour macOS, `lancer_anemone.sh` pour Linux).
Double-cliqué seul, un lanceur télécharge l'outil complet dans un dossier
`ANEMONE` à côté de lui, puis démarre.

**Ou le dossier complet :**

1. Télécharger le dépôt : bouton vert **Code → Download ZIP** sur GitHub, puis
   dézipper où vous voulez.
2. **Windows** : double-cliquer sur `lancer_anemone.bat`.
   **macOS** : double-cliquer sur `lancer_anemone.command` (si macOS refuse :
   clic droit → Ouvrir).
   **Linux** : double-cliquer sur `lancer_anemone.sh`, ou dans un terminal :
   `bash lancer_anemone.sh`.

Le lanceur cherche Python 3.11+ (sous Windows, il propose de l'installer via
`winget` s'il manque), crée un environnement isolé `.venv` dans le dossier,
installe les dépendances au premier démarrage (1 à 3 minutes, ensuite quelques
secondes), puis ouvre l'outil dans le navigateur. Rien n'est installé hors du
dossier : pour désinstaller, supprimer le dossier.

Seul prérequis : **Python 3.11 ou plus récent**
(https://www.python.org/downloads/, cocher « Add python.exe to PATH »).
Le pas-à-pas complet est dans `GUIDE_DEMARRAGE.md`, l'historique des versions
dans `CHANGELOG.md`, la charte produit dans `PRODUCT.md`.

## Modifier le modèle

Toute la mécanique montrée par la carte vient de `alliance_modele.py`, un
schéma éditable — aucun système n'est scanné :

- `COUCHES` / `COULEURS` : les couches de l'infrastructure et leur couleur ;
- `NOEUDS` : les composants (repo local, GitHub, CI, site, AG-Audit, AG-Kali,
  outils Kali, livrables…) ;
- `ARETES` : les interactions entre composants (synchronisation, flux, audit,
  livrable) ;
- `SEQUENCE` : les étapes du rejeu animé et du mode présentation ;
- `OUTILS_KALI` : la chaîne d'outils de l'audit expert ;
- `FINDINGS_DEMO` / `DEVIS_DEMO` : les constats et le devis d'exemple du rapport.

`alliance_modele.valider()` renvoie la liste des incohérences (couche inconnue,
arête vers un nœud absent, gravité invalide…) et doit renvoyer une liste vide.

## Configuration livrée

`.streamlit/config.toml` s'applique automatiquement au lancement :

- pas d'invite « Email » de Streamlit au premier démarrage, aucune statistique
  d'usage envoyée ;
- l'outil n'écoute que sur `localhost` : invisible depuis le réseau.

## Mises à jour automatiques

La branche `main` est la version publiée. À chaque lancement, le lanceur
compare le fichier `VERSION` local à celui de `main` et, s'il est plus récent,
propose d'installer la nouvelle version (Entrée = oui). Le `.venv` et les
fichiers créés localement ne sont jamais touchés. Hors ligne, l'outil démarre
normalement.

**Pour publier une mise à jour** (côté mainteneur) :

1. Incrémenter `VERSION` et compléter `CHANGELOG.md`.
2. Fusionner sur `main` : les tests GitHub Actions doivent être verts
   (Windows, macOS, Linux, lanceurs compris).
3. Tous les utilisateurs se voient proposer la mise à jour au prochain lancement.

Variables : `ANEMONE_SANS_MAJ=1` désactive la vérification,
`ANEMONE_MAJ_AUTO=1` installe sans demander.

## Diagnostic

En cas de problème, un rapport (versions, système, fichiers présents ; aucune
donnée métier) :

```bash
python outils/diagnostic.py     # écrit diagnostic_alliance.txt dans le dossier
```

## Installation manuelle

```bash
git clone https://github.com/khalidawi44/physical_labs && cd physical_labs
pip install -r requirements.txt
streamlit run alliance_cartographie.py
```

`requirements.txt` fige les versions exactes testées sous Python 3.11+.

Tests :

```bash
pip install pytest
python -m pytest tests -q
```
