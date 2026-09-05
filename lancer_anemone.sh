#!/usr/bin/env bash
# ============================================================
#  Lanceur en un clic — Projet A.N.E.M.O.N.E (Linux / macOS)
#  Double-cliquer (ou : bash lancer_anemone.sh). Il :
#    1. trouve Python 3.11+,
#    2. crée un environnement isolé .venv dans ce dossier,
#    3. installe les dépendances (3 à 5 minutes la première fois),
#    4. ouvre l'outil dans le navigateur (http://localhost:8501).
#  Rien n'est installé ailleurs que dans ce dossier.
# ============================================================
set -u
cd "$(dirname "$0")" || exit 1

echo
echo " ===== Projet A.N.E.M.O.N.E ====="
echo

version_ok() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; }

PY=""
for candidat in "${PYTHON:-}" python3.14 python3.13 python3.12 python3.11 python3 python; do
    [ -n "$candidat" ] || continue
    command -v "$candidat" >/dev/null 2>&1 || continue
    if version_ok "$candidat"; then PY="$candidat"; break; fi
done

if [ -z "$PY" ]; then
    echo "[ERREUR] Python 3.11 ou plus récent est introuvable."
    if [ "$(uname)" = "Darwin" ]; then
        echo "         macOS : installez-le depuis https://www.python.org/downloads/"
        echo "         (ou : brew install python@3.12), puis relancez ce fichier."
    elif [ -f /etc/debian_version ]; then
        echo "         Debian / Ubuntu : sudo apt install python3 python3-venv python3-pip"
    elif [ -f /etc/fedora-release ] || [ -f /etc/redhat-release ]; then
        echo "         Fedora / RHEL : sudo dnf install python3"
    else
        echo "         Installez Python 3.11+ avec le gestionnaire de paquets de votre système."
    fi
    echo
    read -r -p "Appuyez sur Entrée pour fermer." _
    exit 1
fi
echo "[OK] Python trouvé : $PY ($("$PY" -c 'import sys; print(sys.version.split()[0])'))"

# Un .venv créé avec un Python trop ancien est recréé.
if [ -x .venv/bin/python ] && ! version_ok .venv/bin/python; then
    echo "[INFO] L'environnement .venv existant est trop ancien, il est recréé."
    rm -rf .venv
fi

if [ ! -x .venv/bin/python ]; then
    echo "[1/3] Création de l'environnement isolé .venv ..."
    if ! "$PY" -m venv .venv; then
        echo
        echo "[ERREUR] Impossible de créer l'environnement .venv."
        if [ -f /etc/debian_version ]; then
            echo "         Sur Debian / Ubuntu, le module venv est un paquet séparé :"
            echo "         sudo apt install python3-venv"
            echo "         puis relancez ce fichier."
        fi
        read -r -p "Appuyez sur Entrée pour fermer." _
        exit 1
    fi
fi

echo "[2/3] Installation / vérification des dépendances ..."
echo "      Première fois : 3 à 5 minutes selon la connexion. Ensuite, quelques secondes."
if ! .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt; then
    echo
    echo "[ERREUR] Installation des dépendances échouée. Vérifiez la connexion internet"
    echo "         puis relancez ce fichier. Le détail de l'erreur est affiché ci-dessus."
    read -r -p "Appuyez sur Entrée pour fermer." _
    exit 1
fi

echo "[3/3] Ouverture de A.N.E.M.O.N.E dans le navigateur ..."
echo "      Si rien ne s'ouvre, allez sur http://localhost:8501"
echo "      Pour arrêter l'outil : fermez cette fenêtre (ou Ctrl+C)."
echo
exec .venv/bin/python -m streamlit run anemone_master.py
