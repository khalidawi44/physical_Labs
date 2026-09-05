#!/usr/bin/env bash
# ============================================================
#  Lanceur en un clic — Projet A.N.E.M.O.N.E (Linux / macOS)
#  Double-cliquer (ou : bash lancer_anemone.sh). Il :
#    1. trouve Python 3.11+ et, si ce fichier a été téléchargé seul,
#       récupère l'outil complet dans un dossier ANEMONE à côté de lui,
#    2. propose la mise à jour si une nouvelle version est publiée,
#    3. crée un environnement isolé .venv dans ce dossier,
#    4. installe les dépendances (3 à 5 minutes la première fois),
#    5. ouvre l'outil dans le navigateur (http://localhost:8501).
#  Rien n'est installé ailleurs que dans ce dossier.
#  Variables utiles : ANEMONE_SANS_MAJ=1 (pas de vérification de mise à jour),
#  ANEMONE_TEST_LANCEUR=1 (s'arrête après l'installation, pour les tests).
# ============================================================
set -u
cd "$(dirname "$0")" || exit 1

echo
echo " ===== Projet A.N.E.M.O.N.E ====="
echo

version_ok() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; }
attendre() { [ "${ANEMONE_TEST_LANCEUR:-}" = "1" ] || read -r -p "Appuyez sur Entrée pour fermer." _; }

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
    attendre
    exit 1
fi
echo "[OK] Python trouvé : $PY ($("$PY" -c 'import sys; print(sys.version.split()[0])'))"

# --- Ce lanceur a été téléchargé seul (sans le projet) : on récupère l'outil ---
if [ ! -f anemone_master.py ]; then
    if [ ! -f ANEMONE/lancer_anemone.sh ]; then
        echo "[INFO] Ce fichier a été téléchargé seul. Téléchargement de l'outil complet"
        echo "       dans le dossier ANEMONE, à côté de ce fichier (quelques secondes) ..."
        if ! "$PY" - <<'PYEOF'
import os, io, shutil, zipfile, urllib.request
u = os.environ.get("ANEMONE_MAJ_URL_ZIP", "https://github.com/khalidawi44/physical_labs/archive/refs/heads/main.zip")
z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=120).read()))
z.extractall(".anemone_tmp")
s = os.path.join(".anemone_tmp", os.listdir(".anemone_tmp")[0])
shutil.copytree(s, "ANEMONE", dirs_exist_ok=True)
shutil.rmtree(".anemone_tmp")
for n in ("lancer_anemone.sh", "lancer_anemone.command"):
    p = os.path.join("ANEMONE", n)
    if os.path.exists(p):
        os.chmod(p, 0o755)
print("[OK] Outil téléchargé dans le dossier ANEMONE")
PYEOF
        then
            echo
            echo "[ERREUR] Téléchargement impossible. Vérifiez la connexion internet, ou"
            echo "         téléchargez le ZIP complet : https://github.com/khalidawi44/physical_labs"
            attendre
            exit 1
        fi
    fi
    exec bash ANEMONE/lancer_anemone.sh
fi

# --- Mise à jour (bibliothèque standard seulement, avant le .venv) ---
if [ "${ANEMONE_SANS_MAJ:-}" != "1" ] && [ -f outils/mise_a_jour.py ]; then
    "$PY" outils/mise_a_jour.py
    code=$?
    if [ "$code" -eq 20 ]; then
        # Le lanceur lui-même a changé : on l'installe et on redémarre dessus.
        if [ -f .anemone_maj/lancer_anemone.sh ]; then
            mv -f .anemone_maj/lancer_anemone.sh ./lancer_anemone.sh && chmod +x ./lancer_anemone.sh
        fi
        rmdir .anemone_maj 2>/dev/null
        echo "[MAJ] Lanceur mis à jour, redémarrage ..."
        echo
        ANEMONE_SANS_MAJ=1 exec bash ./lancer_anemone.sh
    fi
fi

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
        attendre
        exit 1
    fi
fi

echo "[2/3] Installation / vérification des dépendances ..."
echo "      Première fois : 3 à 5 minutes selon la connexion. Ensuite, quelques secondes."
if ! .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt; then
    echo
    echo "[ERREUR] Installation des dépendances échouée. Vérifiez la connexion internet"
    echo "         puis relancez ce fichier. Le détail de l'erreur est affiché ci-dessus."
    attendre
    exit 1
fi

if [ "${ANEMONE_TEST_LANCEUR:-}" = "1" ]; then
    echo "[TEST] Mode test : vérification de l'import de l'application, sans navigateur."
    exec .venv/bin/python -c "import anemone_master; print('[TEST] import OK, version', anemone_master.VERSION_OUTIL)"
fi

echo "[3/3] Ouverture de A.N.E.M.O.N.E dans le navigateur ..."
echo "      Si rien ne s'ouvre, allez sur http://localhost:8501"
echo "      Pour arrêter l'outil : fermez cette fenêtre (ou Ctrl+C)."
echo
exec .venv/bin/python -m streamlit run anemone_master.py
