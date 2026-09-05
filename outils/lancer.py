# -*- coding: utf-8 -*-
"""Démarre A.N.E.M.O.N.E sur un port libre, ou rouvre l'instance déjà en marche.

Appelé par les lanceurs (.bat / .sh) à la place de `streamlit run` directement :

- si un A.N.E.M.O.N.E lancé depuis ce dossier tourne déjà (fichier `.anemone_port`
  et serveur qui répond), on ouvre simplement le navigateur dessus ;
- sinon on prend le premier port libre à partir de 8501 (Streamlit refuse de
  démarrer si le port de sa configuration est occupé : « Port 8501 is not
  available ») et on note ce port dans `.anemone_port` le temps de l'exécution.

Bibliothèque standard uniquement.
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import urllib.request
import webbrowser
from typing import Optional

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER_PORT = os.path.join(RACINE, ".anemone_port")
PORT_DEBUT = 8501
PORT_FIN = 8530
ADRESSE = "localhost"


def port_libre(port: int, adresse: str = ADRESSE) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((adresse, port))
            return True
        except OSError:
            return False


def choisir_port(debut: int = PORT_DEBUT, fin: int = PORT_FIN, adresse: str = ADRESSE) -> int:
    for port in range(debut, fin + 1):
        if port_libre(port, adresse):
            return port
    raise RuntimeError(f"aucun port libre entre {debut} et {fin}")


def serveur_repond(port: int, adresse: str = ADRESSE, delai: float = 1.5) -> bool:
    """Vrai si un serveur Streamlit répond sur ce port (point de santé `_stcore/health`)."""
    sans_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # jamais via le proxy du labo
    try:
        with sans_proxy.open(f"http://{adresse}:{port}/_stcore/health", timeout=delai) as rep:
            return rep.status == 200 and rep.read().strip().lower() == b"ok"
    except Exception:
        return False


def port_note(fichier: Optional[str] = None) -> Optional[int]:
    try:
        with open(fichier or FICHIER_PORT, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def instance_active(fichier: Optional[str] = None, adresse: str = ADRESSE) -> Optional[int]:
    """Port de l'A.N.E.M.O.N.E déjà lancé depuis ce dossier, s'il répond encore."""
    port = port_note(fichier)
    if port is not None and serveur_repond(port, adresse):
        return port
    return None


def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    os.chdir(RACINE)
    deja = instance_active()
    if deja is not None:
        url = f"http://{ADRESSE}:{deja}"
        print(f"[INFO] A.N.E.M.O.N.E tourne deja : {url} (fermez son autre fenetre pour le relancer).")
        print("       Ouverture du navigateur ...")
        webbrowser.open(url)
        return 0
    port = choisir_port()
    if port != PORT_DEBUT:
        print(f"[INFO] Le port {PORT_DEBUT} est occupe par un autre programme : port {port} utilise.")
    print(f"[3/3] Ouverture de A.N.E.M.O.N.E dans le navigateur : http://{ADRESSE}:{port}")
    print("      Si rien ne s'ouvre, copiez cette adresse dans votre navigateur.")
    print("      Pour arreter l'outil : fermez cette fenetre.")
    print()
    with open(FICHIER_PORT, "w", encoding="utf-8") as f:
        f.write(str(port))
    commande = [sys.executable, "-m", "streamlit", "run", "anemone_master.py",
                "--server.port", str(port), "--server.address", ADRESSE] + argv
    return executer(commande)


def executer(commande: list) -> int:
    """Lance Streamlit, l'arrête si ce programme est interrompu (fenêtre fermée, Ctrl+C), efface le port noté."""
    enfant = subprocess.Popen(commande)

    def arreter(*_):
        if enfant.poll() is None:
            enfant.terminate()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, arreter)
        except (ValueError, OSError):  # pragma: no cover - hors du fil principal
            pass
    try:
        return enfant.wait()
    finally:
        arreter()
        try:
            os.remove(FICHIER_PORT)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
