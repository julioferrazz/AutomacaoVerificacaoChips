from datetime import datetime
from typing import List, Dict, Any, Tuple
from core.models import Chip, ChipStatus, TransitionType, ChipTransition, EvaluationReport

class MonitorEvaluator:
    """
    Módulo Profundo de Domínio (Pure Domain Service).
    Calcula transições de estado, aplica regras de filtragem e decide alertas sem efeitos colaterais.
    """
    def __init__(self, filter_keywords: List[str], ignore_keywords: List[str]):
        self.filter_keywords = [k.strip().upper() for k in filter_keywords if k.strip()]
        self.ignore_keywords = [k.strip().upper() for k in ignore_keywords if k.strip()]

    def _format_owner(self, owner_raw: Any) -> str:
        if not owner_raw:
            return "Sem Número"
        return str(owner_raw).split("@")[0].strip() or "Sem Número"

    def parse_instance(self, raw: Dict[str, Any]) -> Chip:
        """Converte o payload bruto da API em uma entidade Chip tipada."""
        instance_id = str(raw.get("id", ""))
        name = str(raw.get("name", "Sem Nome")).strip()
        number = self._format_owner(raw.get("owner"))
        status = ChipStatus.from_string(raw.get("status"))
        reason = raw.get("lastDisconnectReason")

        return Chip(
            id=instance_id,
            name=name,
            number=number,
            status=status,
            last_disconnect_reason=reason,
            last_seen=datetime.now().isoformat()
        )

    def should_monitor(self, chip: Chip) -> Tuple[bool, bool]:
        """
        Avalia se o chip deve ser monitorado.
        Retorna (matches_filter, is_ignored).
        """
        name_upper = chip.name.upper()

        # 1. Verifica se atende ao filtro principal (ex: NIO ou BMG)
        matches_filter = any(kw in name_upper for kw in self.filter_keywords)
        if not matches_filter:
            return False, False

        # 2. Verifica se possui palavras-chave para ignorar (ex: BAN EM ANÁLISE)
        is_ignored = any(kw in name_upper for kw in self.ignore_keywords)
        return True, is_ignored

    def evaluate(self, raw_instances: List[Dict[str, Any]], previous_state: Dict[str, Chip]) -> EvaluationReport:
        """
        Processa todas as instâncias e retorna o relatório consolidado de transições.
        """
        now = datetime.now()
        monitored_chips: List[Chip] = []
        ignored_chips: List[Chip] = []
        transitions: List[ChipTransition] = []

        for raw in raw_instances:
            chip = self.parse_instance(raw)
            matches_filter, is_ignored = self.should_monitor(chip)

            if not matches_filter:
                continue

            if is_ignored:
                ignored_chips.append(chip)
                continue

            monitored_chips.append(chip)

            # Avalia transição com base no histórico anterior
            prev_chip = previous_state.get(chip.key)
            prev_status = prev_chip.status if prev_chip else None

            if prev_status is None:
                # Primeiro ciclo deste chip
                t_type = TransitionType.NEW_DISCONNECTED if chip.is_disconnected else TransitionType.NEW_CONNECTED
            else:
                if chip.is_disconnected:
                    if prev_status == ChipStatus.DISCONNECTED:
                        t_type = TransitionType.STILL_DISCONNECTED  # Permanece desconectado (não repete alerta)
                    else:
                        t_type = TransitionType.JUST_DISCONNECTED  # Acabou de cair!
                elif chip.is_connected:
                    if prev_status == ChipStatus.DISCONNECTED:
                        t_type = TransitionType.RECONNECTED  # Voltou a conectar!
                    else:
                        t_type = TransitionType.STABLE_CONNECTED
                else:
                    t_type = TransitionType.STABLE_CONNECTED

            transitions.append(ChipTransition(
                chip=chip,
                previous_status=prev_status,
                transition_type=t_type
            ))

        return EvaluationReport(
            timestamp=now,
            all_monitored=monitored_chips,
            transitions=transitions,
            ignored_chips=ignored_chips
        )

