import unittest
from core.models import Chip, ChipStatus, TransitionType
from core.evaluator import MonitorEvaluator

class TestMonitorEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = MonitorEvaluator(
            filter_keywords=["NIO", "BMG"],
            ignore_keywords=["BAN", "ANALISE", "ANÁLISE", "BANIDO"]
        )

    def test_filter_keywords(self):
        """Verifica se apenas NIO e BMG são incluídos no monitoramento."""
        raw_instances = [
            {"id": "1", "name": "Chip NIO 01", "owner": "5511999990001", "status": "connected"},
            {"id": "2", "name": "Chip BMG 02", "owner": "5511999990002", "status": "connected"},
            {"id": "3", "name": "Outro Chip Teste", "owner": "5511999990003", "status": "connected"}
        ]
        report = self.evaluator.evaluate(raw_instances, previous_state={})
        monitored_names = [c.name for c in report.all_monitored]

        self.assertIn("Chip NIO 01", monitored_names)
        self.assertIn("Chip BMG 02", monitored_names)
        self.assertNotIn("Outro Chip Teste", monitored_names)

    def test_ignore_keywords_ban_em_analise(self):
        """Verifica se chips com 'BAN' ou 'ANÁLISE' são ignorados mesmo tendo NIO ou BMG."""
        raw_instances = [
            {"id": "1", "name": "NIO 01", "owner": "5511999990001", "status": "connected"},
            {"id": "2", "name": "NIO 02 BAN EM ANÁLISE", "owner": "5511999990002", "status": "disconnected"},
            {"id": "3", "name": "BMG 03 BANIDO", "owner": "5511999990003", "status": "disconnected"}
        ]
        report = self.evaluator.evaluate(raw_instances, previous_state={})

        monitored_names = [c.name for c in report.all_monitored]
        ignored_names = [c.name for c in report.ignored_chips]

        self.assertEqual(monitored_names, ["NIO 01"])
        self.assertIn("NIO 02 BAN EM ANÁLISE", ignored_names)
        self.assertIn("BMG 03 BANIDO", ignored_names)

        # Não deve haver alertas para chips ignorados
        self.assertEqual(len(report.just_disconnected), 0)

    def test_alert_only_on_new_disconnection(self):
        """Verifica se um chip desconectado só dispara alerta uma vez (sem spam nos ciclos seguintes)."""
        raw_cycle_1 = [
            {"id": "1", "name": "NIO 01", "owner": "5511999990001", "status": "connected"}
        ]
        # Ciclo 1: Chip está conectado
        report_1 = self.evaluator.evaluate(raw_cycle_1, previous_state={})
        state_1 = {c.key: c for c in report_1.all_monitored}
        self.assertEqual(len(report_1.just_disconnected), 0)

        # Ciclo 2: Chip CAIU (connected -> disconnected)
        raw_cycle_2 = [
            {"id": "1", "name": "NIO 01", "owner": "5511999990001", "status": "disconnected", "lastDisconnectReason": "401"}
        ]
        report_2 = self.evaluator.evaluate(raw_cycle_2, previous_state=state_1)
        state_2 = {c.key: c for c in report_2.all_monitored}

        # DEVE alertar no ciclo 2!
        self.assertEqual(len(report_2.just_disconnected), 1)
        self.assertEqual(report_2.just_disconnected[0].chip.name, "NIO 01")
        self.assertEqual(report_2.just_disconnected[0].transition_type, TransitionType.JUST_DISCONNECTED)

        # Ciclo 3: 20 minutos depois, chip CONTINUA desconectado
        raw_cycle_3 = [
            {"id": "1", "name": "NIO 01", "owner": "5511999990001", "status": "disconnected", "lastDisconnectReason": "401"}
        ]
        report_3 = self.evaluator.evaluate(raw_cycle_3, previous_state=state_2)

        # NÃO DEVE alertar no ciclo 3 (spam evitado)!
        self.assertEqual(len(report_3.just_disconnected), 0)
        self.assertEqual(len(report_3.still_disconnected), 1)
        self.assertEqual(report_3.still_disconnected[0].transition_type, TransitionType.STILL_DISCONNECTED)

    def test_reconnection_detection(self):
        """Verifica a detecção de reconexão de um chip."""
        chip_prev = Chip(
            id="1",
            name="BMG 01",
            number="5511999990001",
            status=ChipStatus.DISCONNECTED
        )
        previous_state = {chip_prev.key: chip_prev}

        raw_cycle = [
            {"id": "1", "name": "BMG 01", "owner": "5511999990001", "status": "connected"}
        ]
        report = self.evaluator.evaluate(raw_cycle, previous_state=previous_state)

        self.assertEqual(len(report.reconnected), 1)
        self.assertEqual(report.reconnected[0].chip.name, "BMG 01")
        self.assertEqual(report.reconnected[0].transition_type, TransitionType.RECONNECTED)

if __name__ == "__main__":
    unittest.main()

