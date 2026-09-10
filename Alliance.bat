@echo off
setlocal enabledelayedexpansion
title Alliance Groupe - Cartographie 4D
chcp 65001 >nul

REM ==== Trouver le dossier de l'outil (marche depuis le Bureau ou depuis le dossier) ====
set "ROOT="
if exist "%~dp0alliance_cartographie.py" set "ROOT=%~dp0"
if not defined ROOT if exist "%USERPROFILE%\Desktop\Alliance_Graph\alliance_cartographie.py" set "ROOT=%USERPROFILE%\Desktop\Alliance_Graph\"
if not defined ROOT if exist "%USERPROFILE%\OneDrive\Desktop\Alliance_Graph\alliance_cartographie.py" set "ROOT=%USERPROFILE%\OneDrive\Desktop\Alliance_Graph\"
if not defined ROOT if exist "%USERPROFILE%\OneDrive\Bureau\Alliance_Graph\alliance_cartographie.py" set "ROOT=%USERPROFILE%\OneDrive\Bureau\Alliance_Graph\"
if not defined ROOT if exist "%USERPROFILE%\Bureau\Alliance_Graph\alliance_cartographie.py" set "ROOT=%USERPROFILE%\Bureau\Alliance_Graph\"
if not defined ROOT (
  echo.
  echo   Impossible de trouver alliance_cartographie.py
  echo   Placez ce fichier dans le dossier Alliance_Graph, ou sur le Bureau a cote.
  echo.
  pause
  exit /b 1
)
cd /d "%ROOT%"

REM ==== Trouver Python (venv ANEMONE, sinon venv local, sinon systeme) ====
set "PY="
if exist "%ROOT%ANEMONE\.venv\Scripts\python.exe" set "PY=%ROOT%ANEMONE\.venv\Scripts\python.exe"
if not defined PY if exist "%ROOT%.venv\Scripts\python.exe" set "PY=%ROOT%.venv\Scripts\python.exe"
if not defined PY set "PY=python"

REM ==== S'assurer que python-docx est present (pour la vue Rapport) ====
"%PY%" -c "import docx" 2>nul || "%PY%" -m pip install python-docx

REM ==== Ouvrir le navigateur apres 6 secondes (le temps que le serveur demarre) ====
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 6; Start-Process 'http://localhost:8502'"

echo.
echo   Demarrage de la cartographie Alliance Groupe...
echo   Le navigateur va s'ouvrir sur http://localhost:8502
echo   (Laissez cette fenetre ouverte. Fermez-la pour arreter l'outil.)
echo.

REM ==== Lancer l'app sans le prompt e-mail (headless) ====
"%PY%" -m streamlit run alliance_cartographie.py --server.port 8502 --server.address localhost --server.headless true

echo.
echo   L'outil s'est arrete. Appuyez sur une touche pour fermer.
pause >nul
