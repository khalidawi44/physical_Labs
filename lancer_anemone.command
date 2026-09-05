#!/usr/bin/env bash
# Lanceur macOS — double-cliquer dans le Finder.
# (Le Finder ouvre les .command dans le Terminal ; il délègue au script commun.)
# Si macOS refuse l'ouverture (« développeur non identifié ») : clic droit → Ouvrir.
cd "$(dirname "$0")" || exit 1
if [ ! -f lancer_anemone.sh ]; then
    # Fichier téléchargé seul : on récupère le lanceur commun, qui récupérera le reste.
    echo "[INFO] Téléchargement du lanceur commun ..."
    curl -fsSL "https://raw.githubusercontent.com/khalidawi44/physical_labs/main/lancer_anemone.sh" -o lancer_anemone.sh \
        || { echo "[ERREUR] Téléchargement impossible. Vérifiez la connexion internet."; read -r -p "Entrée pour fermer." _; exit 1; }
fi
exec bash ./lancer_anemone.sh
