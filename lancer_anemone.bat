@echo off
REM ============================================================
REM  Lanceur en un clic — Projet A.N.E.M.O.N.E (Windows)
REM  Double-cliquer sur ce fichier : installe les dependances
REM  dans un environnement isole (.venv) puis ouvre l'outil.
REM ============================================================
title Projet A.N.E.M.O.N.E
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python est introuvable. Installez-le depuis https://www.python.org/downloads/
    echo          en cochant "Add python.exe to PATH", puis relancez ce fichier.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creation de l'environnement isole .venv ...
    python -m venv .venv
    if errorlevel 1 ( echo [ERREUR] Impossible de creer .venv & pause & exit /b 1 )
)

echo [2/3] Verification des dependances ...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo [ERREUR] Installation des dependances echouee & pause & exit /b 1 )

echo [3/3] Ouverture de A.N.E.M.O.N.E dans le navigateur ...
".venv\Scripts\python.exe" -m streamlit run anemone_master.py --server.headless false
pause
