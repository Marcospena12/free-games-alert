"""Cliente HTTP para a GamerPower API com retry, backoff e tratamento seguro de status."""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from ..config import REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

GAMERPOWER_BASE_URL = "https://www.gamerpower.com/api"
DEFAULT_USER_AGENT = "FreeGamesHub/0.1 (+https://github.com/Marcos/free-games-hub)"


class GamerPowerApiError(RuntimeError):
    """Erro ao consultar ou interpretar a GamerPower API."""


class GamerPowerClient:
    """Cliente para a API REST da GamerPower.com."""

    def __init__(
        self,
        base_url: str = GAMERPOWER_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        max_retries: int = 3,
        http_requester: Optional[Callable[[str], tuple[int, bytes]]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.http_requester = http_requester

    def get_giveaways(
        self,
        platforms: Optional[list[str]] = None,
        types: Optional[list[str]] = None,
        sort_by: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Consulta ofertas na GamerPower API.

        Se houver múltiplas plataformas ou tipos, usa o endpoint `/filter`.
        Caso contrário, usa `/giveaways`.
        """
        params: dict[str, str] = {}
        use_filter = False

        if platforms:
            if len(platforms) > 1:
                # Usar '.' que é aceito nativamente pelo backend GamerPower sem ambiguidades de decodificação
                params["platform"] = ".".join(platforms)
                use_filter = True
            else:
                params["platform"] = platforms[0]

        if types:
            if len(types) > 1:
                params["type"] = ".".join(types)
                use_filter = True
            else:
                params["type"] = types[0]

        if sort_by:
            params["sort-by"] = sort_by

        endpoint = "/filter" if use_filter else "/giveaways"
        url = f"{self.base_url}{endpoint}"
        if params:
            # urlencode assegura parâmetros seguros
            url = f"{url}?{urllib.parse.urlencode(params)}"

        return self._request_json_list(url)

    def _request_json_list(self, url: str) -> list[dict[str, Any]]:
        """Executa a requisição com retries, jitter e validação do payload."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                if self.http_requester is not None:
                    status, raw_bytes = self.http_requester(url)
                    raw_data = raw_bytes.decode("utf-8", errors="replace")
                else:
                    with urllib.request.urlopen(req, timeout=self.timeout) as response:
                        status = response.status
                        raw_data = response.read().decode("utf-8", errors="replace")

                # Status 201: Nenhum giveaway ativo (esperado, NÃO é erro)
                if status == 201:
                    logger.debug("GamerPower retornou 201 (sem ofertas ativas para o filtro).")
                    return []

                if status != 200:
                    raise GamerPowerApiError(f"Status HTTP {status} inesperado ao acessar {url}")

                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError as exc:
                    raise GamerPowerApiError(f"Resposta JSON inválida da GamerPower: {exc}") from exc

                if isinstance(data, list):
                    return data

                # Se vier um objeto com mensagem de ausência de ofertas
                if isinstance(data, dict):
                    if data.get("status") == 0:
                        return []
                    raise GamerPowerApiError(f"Formato JSON inesperado retornado: {data}")

                raise GamerPowerApiError(f"Esperada lista de ofertas, obtido: {type(data).__name__}")

            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 201:
                    return []
                # Erros 4xx (exceto 429) não devem ser re-tentados
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise GamerPowerApiError(f"HTTP {exc.code} ao acessar {url}: {exc.reason}") from exc
                # Erro 5xx ou 429 -> tentar novamente
                logger.warning("Erro HTTP %s na tentativa %d/%d ao acessar GamerPower: %s", exc.code, attempt + 1, self.max_retries, exc)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                logger.warning("Falha de rede na tentativa %d/%d ao acessar GamerPower: %s", attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                # Backoff exponencial com jitter
                delay = (0.5 * (2 ** attempt)) + random.uniform(0.1, 0.4)
                time.sleep(delay)

        raise GamerPowerApiError(f"Falha após {self.max_retries} tentativas ao acessar {url}: {last_error}")
