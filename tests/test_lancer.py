# -*- coding: utf-8 -*-
"""Lanceur : port libre, instance déjà en marche rouverte au lieu de « Port 8501 is not available »."""
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)

from outils import lancer  # noqa: E402


class _Sante(BaseHTTPRequestHandler):
    def do_GET(self):
        corps = b"ok" if self.path == "/_stcore/health" else b"?"
        self.send_response(200 if corps == b"ok" else 404)
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):  # silencieux
        pass


@pytest.fixture
def faux_streamlit():
    serveur = HTTPServer(("localhost", 0), _Sante)
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    yield serveur.server_address[1]
    serveur.shutdown()


def test_choisir_port_saute_un_port_occupe():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        s.listen(1)
        occupe = s.getsockname()[1]
        assert not lancer.port_libre(occupe)
        assert lancer.choisir_port(debut=occupe, fin=occupe + 20) > occupe


def test_instance_active_seulement_si_le_serveur_repond(tmp_path, faux_streamlit):
    fichier = str(tmp_path / ".anemone_port")
    assert lancer.instance_active(fichier) is None                 # pas de fichier
    (tmp_path / ".anemone_port").write_text(str(faux_streamlit))
    assert lancer.instance_active(fichier) == faux_streamlit       # le serveur répond « ok »
    (tmp_path / ".anemone_port").write_text(str(lancer.choisir_port(debut=faux_streamlit + 1, fin=faux_streamlit + 30)))
    assert lancer.instance_active(fichier) is None                 # port noté mais rien n'écoute


def test_main_rouvre_le_navigateur_si_deja_lance(tmp_path, monkeypatch, faux_streamlit, capsys):
    monkeypatch.setattr(lancer, "FICHIER_PORT", str(tmp_path / ".anemone_port"))
    (tmp_path / ".anemone_port").write_text(str(faux_streamlit))
    ouverts = []
    monkeypatch.setattr(lancer.webbrowser, "open", lambda url: ouverts.append(url) or True)
    monkeypatch.setattr(lancer, "executer", lambda *a, **k: pytest.fail("streamlit ne doit pas être relancé"))
    assert lancer.main([]) == 0
    assert ouverts == [f"http://localhost:{faux_streamlit}"]
    assert "tourne deja" in capsys.readouterr().out


def test_main_lance_streamlit_sur_un_port_libre_et_nettoie(tmp_path, monkeypatch):
    fichier = str(tmp_path / ".anemone_port")
    monkeypatch.setattr(lancer, "FICHIER_PORT", fichier)
    appels = []

    def faux_call(args):
        appels.append(args)
        assert os.path.isfile(fichier) and int(open(fichier).read()) == int(args[args.index("--server.port") + 1])
        os.remove(fichier)   # ce que fait `executer` à l'arrêt de Streamlit
        return 0

    monkeypatch.setattr(lancer, "executer", faux_call)
    assert lancer.main([]) == 0
    assert appels and appels[0][1:5] == ["-m", "streamlit", "run", "alliance_cartographie.py"]
    assert lancer.port_libre(int(appels[0][appels[0].index("--server.port") + 1]))
    assert not os.path.exists(fichier)                             # le port noté est effacé à l'arrêt


@pytest.mark.skipif(os.name == "nt", reason="Windows : fermer la console tue tout l'arbre de processus, sans signal")
def test_executer_arrete_streamlit_sur_signal_et_efface_le_port(tmp_path, monkeypatch):
    """SIGTERM sur le lanceur (fenêtre fermée) : l'enfant est arrêté et le port noté effacé, pas d'orphelin sur 8501."""
    import signal
    import subprocess
    import time

    fichier = str(tmp_path / ".anemone_port")
    monkeypatch.setattr(lancer, "FICHIER_PORT", fichier)
    open(fichier, "w").write("8501")
    lanceur = subprocess.Popen([sys.executable, "-c",
                                f"import sys; sys.path.insert(0, {RACINE!r}); from outils import lancer; "
                                f"lancer.FICHIER_PORT = {fichier!r}; "
                                f"lancer.executer([sys.executable, '-c', 'import time; time.sleep(60)'])"])
    time.sleep(2)
    lanceur.send_signal(signal.SIGTERM)
    assert lanceur.wait(timeout=10) is not None
    assert not os.path.exists(fichier)
