from abc import ABC, abstractmethod
from typing import Dict, List
from core.models import Chip

class StateRepository(ABC):
    """
    Porta (Interface) para persistência do estado dos chips.
    Desacopla o armazenamento (JSON local, SQLite, Redis) do núcleo da aplicação.
    """
    @abstractmethod
    def load_state(self) -> Dict[str, Chip]:
        """Recupera o último estado persistido dos chips."""
        pass

    @abstractmethod
    def save_state(self, chips: List[Chip]) -> None:
        """Persiste o estado atual dos chips monitorados."""
        pass

