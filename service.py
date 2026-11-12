import logging
from core.models import EvaluationReport
from core.evaluator import MonitorEvaluator
from ports.notifier import Notifier
from ports.repository import StateRepository
from adapters.uazapi_client import UazapiClient

logger = logging.getLogger("ChipMonitorService")

class ChipMonitorService:
    """
    Serviço de Aplicação (Use Case Orquestrador).
    Coordena a leitura da API, avaliação de transições, persistência e notificações.
    """
    def __init__(
        self,
        client: UazapiClient,
        evaluator: MonitorEvaluator,
        repository: StateRepository,
        notifier: Notifier
    ):
        self.client = client
        self.evaluator = evaluator
        self.repository = repository
        self.notifier = notifier

    def run_cycle(self) -> EvaluationReport:
        """Executa um ciclo completo de verificação e notificação."""
        logger.info("Executando ciclo de verificação dos chips...")

        # 1. Carrega histórico de estado anterior
        previous_state = self.repository.load_state()

        # 2. Busca instâncias atuais da API
        raw_instances = self.client.fetch_all_instances()

        # 3. Executa avaliação de domínio pura
        report = self.evaluator.evaluate(raw_instances, previous_state)

        # 4. Persiste o novo estado dos chips monitorados
        self.repository.save_state(report.all_monitored)

        # 5. Dispara notificações apenas para quem caiu AGORA (evita repetições)
        if report.just_disconnected:
            logger.warning(f"{len(report.just_disconnected)} chip(s) caíram neste ciclo. Disparando notificação.")
            self.notifier.notify_disconnections(report.just_disconnected)
        elif report.still_disconnected:
            logger.info(f"{len(report.still_disconnected)} chip(s) permanecem desconectados (alerta já enviado anteriormente, ignorando spam).")

        # 6. Notifica reconexões se houver
        if report.reconnected:
            logger.info(f"{len(report.reconnected)} chip(s) restabeleceram conexão.")
            self.notifier.notify_reconnections(report.reconnected)

        return report

