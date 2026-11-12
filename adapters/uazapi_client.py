import logging
import time
from typing import List, Dict, Any
import requests

logger = logging.getLogger("UazapiClient")

class UazapiClient:
    """
    Adaptador HTTP para a API Uazapi v2.6.9+.
    """
    def __init__(self, server_url: str, admin_token: str, timeout: int = 15):
        self.server_url = server_url.strip().rstrip("/")
        self.admin_token = admin_token.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "admintoken": self.admin_token,
            "User-Agent": "MonitorChips/2.1 (Clean Architecture)"
        })

    def fetch_all_instances(self) -> List[Dict[str, Any]]:
        """Consulta GET /instance/all para obter todas as instâncias do servidor."""
        endpoint = f"{self.server_url}/instance/all"

        for attempt in range(1, 4):
            try:
                response = self.session.get(endpoint, timeout=self.timeout)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2))
                    logger.warning(f"Rate limit da API atingido. Aguardando {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                if response.status_code == 401:
                    raise PermissionError("ADMIN_TOKEN inválido ou não autorizado neste servidor.")

                if response.status_code == 404:
                    raise FileNotFoundError(f"Endpoint não encontrado: {endpoint}. Verifique a SERVER_URL.")

                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("instances", data.get("data", []))
                return []

            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt}/3 falhou em {endpoint}: {e}")
                if attempt == 3:
                    raise
                time.sleep(attempt * 2)

        return []

