#!/usr/bin/env bash
# Lanceur en un clic — Projet A.N.E.M.O.N.E (macOS / Linux)
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then
    echo "[1/3] Création de l'environnement isolé .venv ..."
    "$PY" -m venv .venv
fi
echo "[2/3] Vérification des dépendances ..."
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
echo "[3/3] Ouverture de A.N.E.M.O.N.E dans le navigateur ..."
exec .venv/bin/python -m streamlit run anemone_master.py
