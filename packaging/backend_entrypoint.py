"""Entrada do backend headless empacotado pelo PyInstaller.

O processo é iniciado pelo shell Electron com ``--port``, ``--token``,
``--spa-dir`` e ``--app-icon``. A porta efetiva é impressa em stdout como
``FGH_PORT=<n>`` para o processo pai.
"""

from free_games_hub.api.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
