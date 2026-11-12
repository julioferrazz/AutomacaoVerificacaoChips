from abc import ABC, abstractmethod
from typing import List
from core.models import ChipTransition

class Notifier(ABC):
    """
    Porta (Interface) para serviços de notificação de alertas.
    Permite desacoplar as regras de negócio dos canais de entrega (Windows, Telegram, Discord, etc).
    """
    @abstractmethod
    def notify_disconnections(self, drops: List[ChipTransition]) -> bool:
        """Dispara alerta para chips que acabaram de desconectar."""
        pass

    @abstractmethod
    def notify_reconnections(self, reconnected: List[ChipTransition]) -> bool:
        """Dispara aviso para chips que restabeleceram conexão."""
        pass

    @abstractmethod
    def notify_error(self, title: str, message: str) -> bool:
        """Dispara aviso de erro operacional no monitor."""
        pass

