import os
import json
import logging
from datetime import datetime
from typing import Dict, List
from ports.repository import StateRepository
from core.models import Chip

logger = logging.getLogger("JsonRepository")

class JsonFileRepository(StateRepository):
    """
    Adaptador de persistência baseado em arquivo JSON local.
    """
    def __init__(self, file_path: str = "chips_status.json"):
        self.file_path = file_path

    def load_state(self) -> Dict[str, Chip]:
        if not os.path.exists(self.file_path):
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_chips = data.get("chips", {})
                return {key: Chip.from_dict(val) for key, val in raw_chips.items()}
        except Exception as e:
            logger.warning(f"Erro ao ler '{self.file_path}': {e}. Iniciando com estado vazio.")
            return {}

    def save_state(self, chips: List[Chip]) -> None:
        try:
            payload = {
                "last_check": datetime.now().isoformat(),
                "chips": {chip.key: chip.to_dict() for chip in chips}
            }
            # Gravação atômica em arquivo temporário antes de substituir
            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.file_path)
        except Exception as e:
            logger.error(f"Erro ao salvar estado em '{self.file_path}': {e}")

