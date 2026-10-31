"""Garante uma única instância do aplicativo por sessão."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QCoreApplication, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "FreeGamesHub"
QUIT_ARG = "--quit"
QUIT_MESSAGE = b"quit"


class SingleInstance(QObject):
    """Servidor local que avisa a instância existente para abrir ou encerrar."""

    activation_requested = Signal()
    quit_requested = Signal()

    def __init__(self, name: str = SERVER_NAME, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._name = name
        self._server: Optional[QLocalServer] = None
        self._connections: list[QLocalSocket] = []

    def acquire(self, *, activate_existing: bool = True) -> bool:
        """Retorna True se esta for a primeira instância.

         Quando já existe outra, envia ``show`` (ou ``noop`` no auto-start) e
         retorna False.
         """
        if self._notify_existing(b"show" if activate_existing else b"noop"):
            return False

        QLocalServer.removeServer(self._name)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        if self._server.listen(self._name):
            return True

        # Outra instância pode ter vencido a corrida entre o teste e o listen.
        if self._notify_existing(b"show" if activate_existing else b"noop"):
            return False
        raise RuntimeError(
            f"Não foi possível iniciar o servidor de instância única: "
            f"{self._server.errorString()}"
        )

    def send_quit(self) -> bool:
        """Pede o encerramento da instância existente e aguarda sua saída.

        Retorna False quando não há outra instância. Levanta RuntimeError se
        houver uma instância mas ela não confirmar o encerramento.
        """
        if not self._notify_existing(QUIT_MESSAGE, wait_for_disconnect=True):
            return False
        return True

    def _notify_existing(
        self, payload: bytes, *, wait_for_disconnect: bool = False
    ) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._name)
        if not socket.waitForConnected(500):
            return False
        socket.write(payload)
        socket.flush()
        # QLocalSocket no Windows pode manter os bytes em buffer até o loop
        # processar eventos; waitForBytesWritten nem sempre faz esse flush.
        QCoreApplication.processEvents()
        if wait_for_disconnect and not socket.waitForDisconnected(10_000):
            socket.disconnectFromServer()
            raise RuntimeError("A instância existente não encerrou a tempo.")
        socket.disconnectFromServer()
        return True

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            self._connections.append(socket)
            socket.readyRead.connect(lambda s=socket: self._on_ready_read(s))
            socket.disconnected.connect(lambda s=socket: self._cleanup(s))

    def _on_ready_read(self, socket: QLocalSocket) -> None:
        data = bytes(socket.readAll()).strip()
        if data == b"show":
            self.activation_requested.emit()
        elif data == QUIT_MESSAGE:
            self.quit_requested.emit()

    def _cleanup(self, socket: QLocalSocket) -> None:
        if socket in self._connections:
            self._connections.remove(socket)
        socket.deleteLater()
