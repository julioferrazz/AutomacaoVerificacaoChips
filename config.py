import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    """
    Configurações da aplicação validadas em tempo de inicialização (Fail-Fast).
    """
    server_url: str
    admin_token: str
    filter_keywords: List[str] = field(default_factory=lambda: ["NIO", "BMG"])
    ignore_keywords: List[str] = field(default_factory=lambda: ["BAN", "ANALISE", "ANÁLISE", "BANIDO", "DESCARTE"])
    check_interval_minutes: int = 20
    status_file: str = "chips_status.json"
    log_file: str = "monitor.log"

    @classmethod
    def load(cls, env_path: str = ".env") -> "Settings":
        load_dotenv(env_path)

        server_url = os.getenv("SERVER_URL", "").strip().rstrip("/")
        admin_token = os.getenv("ADMIN_TOKEN", "").strip()

        # Palavras-chave para incluir no monitoramento
        filter_raw = os.getenv("FILTER_KEYWORDS", "NIO,BMG")
        filter_keywords = [k.strip().upper() for k in filter_raw.split(",") if k.strip()]

        # Palavras-chave para IGNORAR (ex: BAN EM ANÁLISE)
        ignore_raw = os.getenv("IGNORE_KEYWORDS", "BAN,ANALISE,ANÁLISE,BANIDO,DESCARTE")
        ignore_keywords = [k.strip().upper() for k in ignore_raw.split(",") if k.strip()]

        # Intervalo de checagem
        try:
            interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "20"))
            if interval <= 0:
                interval = 20
        except ValueError:
            interval = 20

        status_file = os.getenv("STATUS_FILE", "chips_status.json")
        log_file = os.getenv("LOG_FILE", "monitor.log")

        return cls(
            server_url=server_url,
            admin_token=admin_token,
            filter_keywords=filter_keywords,
            ignore_keywords=ignore_keywords,
            check_interval_minutes=interval,
            status_file=status_file,
            log_file=log_file
        )

    def validate(self):
        """Verifica se os campos obrigatórios estão preenchidos."""
        errors = []
        if not self.server_url:
            errors.append("SERVER_URL não configurada no arquivo .env.")
        elif not (self.server_url.startswith("http://") or self.server_url.startswith("https://")):
            errors.append("SERVER_URL deve iniciar com http:// ou https://.")

        if not self.admin_token:
            errors.append("ADMIN_TOKEN não configurado no arquivo .env.")

        if errors:
            raise ValueError("Erro de configuração:\n" + "\n".join(f" - {e}" for e in errors))

