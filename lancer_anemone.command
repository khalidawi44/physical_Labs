#!/usr/bin/env bash
# Lanceur macOS — double-cliquer dans le Finder.
# (Le Finder ouvre les .command dans le Terminal ; il délègue au script commun.)
# Si macOS refuse l'ouverture (« développeur non identifié ») : clic droit → Ouvrir.
cd "$(dirname "$0")" || exit 1
exec bash ./lancer_anemone.sh
