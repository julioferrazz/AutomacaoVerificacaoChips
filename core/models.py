from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict

class ChipStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HIBERNATED = "hibernated"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: Optional[str]) -> "ChipStatus":
        if not value:
            return cls.UNKNOWN
        val_clean = str(value).strip().lower()
        for member in cls:
            if member.value == val_clean:
                return member
        return cls.UNKNOWN

@dataclass(frozen=True)
class Chip:
    id: str
    name: str
    number: str
    status: ChipStatus
    last_disconnect_reason: Optional[str] = None
    last_seen: Optional[str] = None

    @property
    def key(self) -> str:
        """Chave de identificação única do chip."""
        return f"{self.id}_{self.name}"

    @property
    def is_connected(self) -> bool:
        return self.status == ChipStatus.CONNECTED

    @property
    def is_disconnected(self) -> bool:
        return self.status == ChipStatus.DISCONNECTED

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "numero": self.number,
            "status": self.status.value,
            "last_disconnect_reason": self.last_disconnect_reason or "",
            "last_seen": self.last_seen or datetime.now().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Chip":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Sem Nome"),
            number=data.get("numero", "Sem Número"),
            status=ChipStatus.from_string(data.get("status")),
            last_disconnect_reason=data.get("last_disconnect_reason"),
            last_seen=data.get("last_seen")
        )

class TransitionType(str, Enum):
    NEW_CONNECTED = "new_connected"
    NEW_DISCONNECTED = "new_disconnected"
    STABLE_CONNECTED = "stable_connected"
    JUST_DISCONNECTED = "just_disconnected"  # Caiu agora (Transição de connected -> disconnected)
    STILL_DISCONNECTED = "still_disconnected"  # Continua caído (Não deve gerar novo alerta de spam)
    RECONNECTED = "reconnected"  # Voltou a conectar (disconnected -> connected)

@dataclass(frozen=True)
class ChipTransition:
    chip: Chip
    previous_status: Optional[ChipStatus]
    transition_type: TransitionType

    @property
    def is_new_drop(self) -> bool:
        """Verifica se o chip acabou de desconectar."""
        return self.transition_type in (TransitionType.JUST_DISCONNECTED, TransitionType.NEW_DISCONNECTED)

@dataclass(frozen=True)
class EvaluationReport:
    timestamp: datetime
    all_monitored: List[Chip]
    transitions: List[ChipTransition]
    ignored_chips: List[Chip]

    @property
    def just_disconnected(self) -> List[ChipTransition]:
        """Apenas chips que caíram neste ciclo (devem disparar notificação)."""
        return [t for t in self.transitions if t.is_new_drop]

    @property
    def still_disconnected(self) -> List[ChipTransition]:
        """Chips que continuam desconectados de ciclos anteriores (não disparam spam)."""
        return [t for t in self.transitions if t.transition_type == TransitionType.STILL_DISCONNECTED]

    @property
    def reconnected(self) -> List[ChipTransition]:
        """Chips que foram reconectados com sucesso."""
        return [t for t in self.transitions if t.transition_type == TransitionType.RECONNECTED]

