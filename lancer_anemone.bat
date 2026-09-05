@echo off
REM ============================================================
REM  Lanceur en un clic - Projet A.N.E.M.O.N.E (Windows)
REM  Double-cliquer sur ce fichier. Il :
REM    1. trouve Python 3.11+ (ou propose de l'installer),
REM       et, si ce fichier a ete telecharge seul, recupere l'outil complet
REM       dans un dossier ANEMONE a cote de lui,
REM    2. propose la mise a jour si une nouvelle version est publiee,
REM    3. cree un environnement isole .venv dans ce dossier,
REM    4. installe les dependances (3 a 5 minutes la premiere fois),
REM    5. ouvre l'outil dans le navigateur (http://localhost:8501).
REM  Rien n'est installe ailleurs que dans ce dossier.
REM  Variables utiles : ANEMONE_SANS_MAJ=1 (pas de verification de mise a jour),
REM  ANEMONE_TEST_LANCEUR=1 (s'arrete apres l'installation, pour les tests).
REM ============================================================
setlocal
title Projet A.N.E.M.O.N.E
cd /d "%~dp0"

echo.
echo  ===== Projet A.N.E.M.O.N.E =====
echo.

set "PY="
call :chercher_python

if not defined PY (
    echo [INFO] Python 3.11 ou plus recent est introuvable sur cette machine.
    where winget >nul 2>nul
    if errorlevel 1 goto :sans_python
    echo [INFO] Installation automatique de Python 3.12 via winget ...
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    call :chercher_python
    if not defined PY (
        echo.
        echo [INFO] Python vient d'etre installe. Fermez cette fenetre puis
        echo        double-cliquez a nouveau sur lancer_anemone.bat.
        pause
        exit /b 0
    )
)

echo [OK] Python trouve : %PY%

REM --- Ce lanceur a ete telecharge seul (sans le projet) : on recupere l'outil ---
if exist "anemone_master.py" goto :dossier_ok
if exist "ANEMONE\lancer_anemone.bat" goto :deleguer
echo [INFO] Ce fichier a ete telecharge seul. Telechargement de l'outil complet
echo        dans le dossier ANEMONE, a cote de ce fichier (quelques secondes) ...
%PY% -c "import os,io,shutil,zipfile,urllib.request;u=os.environ.get('ANEMONE_MAJ_URL_ZIP','https://github.com/khalidawi44/physical_labs/archive/refs/heads/main.zip');z=zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u,timeout=120).read()));z.extractall('.anemone_tmp');s=os.path.join('.anemone_tmp',os.listdir('.anemone_tmp')[0]);shutil.copytree(s,'ANEMONE',dirs_exist_ok=True);shutil.rmtree('.anemone_tmp');print('[OK] Outil telecharge dans le dossier ANEMONE')"
if errorlevel 1 (
    echo.
    echo [ERREUR] Telechargement impossible. Verifiez la connexion internet, ou
    echo          telechargez le ZIP complet : https://github.com/khalidawi44/physical_labs
    pause
    exit /b 1
)
:deleguer
call "ANEMONE\lancer_anemone.bat"
exit /b %errorlevel%
:dossier_ok

REM --- Mise a jour (bibliotheque standard seulement, avant le .venv) ---
if "%ANEMONE_SANS_MAJ%"=="1" goto :apres_maj
if not exist "outils\mise_a_jour.py" goto :apres_maj
%PY% outils\mise_a_jour.py
if errorlevel 20 goto :relancer
:apres_maj

REM --- Un .venv cree avec un Python trop ancien est recree ---
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
    if errorlevel 1 (
        echo [INFO] L'environnement .venv existant est trop ancien, il est recree.
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creation de l'environnement isole .venv ...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement .venv.
        pause
        exit /b 1
    )
)

echo [2/3] Installation / verification des dependances ...
echo       Premiere fois : 3 a 5 minutes selon la connexion. Ensuite, quelques secondes.
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERREUR] Installation des dependances echouee. Verifiez la connexion internet
    echo          puis relancez ce fichier. Le detail de l'erreur est affiche ci-dessus.
    pause
    exit /b 1
)

if not "%ANEMONE_TEST_LANCEUR%"=="1" goto :lancer
echo [TEST] Mode test : verification de l'import de l'application, sans navigateur.
".venv\Scripts\python.exe" -c "import anemone_master; print('[TEST] import OK, version', anemone_master.VERSION_OUTIL)"
exit /b %errorlevel%
:lancer

echo [3/3] Ouverture de A.N.E.M.O.N.E dans le navigateur ...
echo       Si rien ne s'ouvre, allez sur http://localhost:8501
echo       Pour arreter l'outil : fermez cette fenetre.
echo.
".venv\Scripts\python.exe" -m streamlit run anemone_master.py
pause
exit /b 0

REM ------------------------------------------------------------
REM  Sous-programmes
REM ------------------------------------------------------------
:chercher_python
call :essayer "py -3.13"
call :essayer "py -3.12"
call :essayer "py -3.11"
call :essayer "py -3"
call :essayer "python"
call :essayer "python3"
exit /b

:essayer
if defined PY exit /b
%~1 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
exit /b

:relancer
REM Le lanceur lui-meme a change : on installe la nouvelle version et on
REM redemarre dessus. Un .bat ne doit pas etre reecrit pendant qu'il tourne :
REM le remplacement est la toute derniere instruction de cette ligne.
echo [MAJ] Lanceur mis a jour, redemarrage ...
echo.
set "ANEMONE_SANS_MAJ=1"
move /y ".anemone_maj\lancer_anemone.bat" "%~f0" >nul & rmdir ".anemone_maj" 2>nul & call "%~f0" & exit /b

:sans_python
echo.
echo [ERREUR] Python 3.11+ est absent et winget n'est pas disponible.
echo          Installez Python depuis https://www.python.org/downloads/
echo          en cochant "Add python.exe to PATH", puis relancez ce fichier.
pause
exit /b 1
