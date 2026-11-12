import sys
import time
import logging
from datetime import datetime
from config import Settings
from core.models import TransitionType
from core.evaluator import MonitorEvaluator
from adapters.uazapi_client import UazapiClient
from adapters.json_repository import JsonFileRepository
from adapters.windows_notifier import WindowsToastNotifier
from service import ChipMonitorService

def setup_logging(log_file: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def render_table(report):
    print("\n" + "=" * 82)
    print(f" {'HORA':<8} | {'NOME DA INSTÂNCIA':<24} | {'NÚMERO':<18} | {'STATUS':<24}")
    print("-" * 82)

    now_str = datetime.now().strftime("%H:%M:%S")

    # Mapeia transições por chave
    transitions_map = {t.chip.key: t.transition_type for t in report.transitions}

    for chip in report.all_monitored:
        t_type = transitions_map.get(chip.key, TransitionType.STABLE_CONNECTED)

        if t_type in (TransitionType.JUST_DISCONNECTED, TransitionType.NEW_DISCONNECTED):
            status_text = "[NOVA QUEDA ⚠️]"
        elif t_type == TransitionType.STILL_DISCONNECTED:
            status_text = "[DESCONECTADO (Silenciado)]"
        elif t_type == TransitionType.RECONNECTED:
            status_text = "[RECONECTADO 🔄]"
        elif chip.is_connected:
            status_text = "[CONECTADO ✅]"
        else:
            status_text = f"[{chip.status.value.upper()}]"

        print(f" {now_str:<8} | {chip.name[:24]:<24} | {chip.number[:18]:<18} | {status_text:<24}")

    print("=" * 82)

    if report.ignored_chips:
        nomes_ign = ", ".join([c.name for c in report.ignored_chips[:3]])
        print(f"ℹ️  {len(report.ignored_chips)} chip(s) ignorados por conterem termo de exclusão (ex: BAN/ANÁLISE): {nomes_ign}")
    print()

def main():
    settings = Settings.load()

    # Valida configurações
    try:
        settings.validate()
    except ValueError as e:
        print("\n" + "=" * 70)
        print(" [ERRO DE CONFIGURAÇÃO]")
        print(e)
        print(" Abra o arquivo .env e configure a SERVER_URL e ADMIN_TOKEN.")
        print("=" * 70 + "\n")
        sys.exit(1)

    setup_logging(settings.log_file)
    logger = logging.getLogger("Main")

    print("=" * 82)
    print("      MONITOR DE CHIPS UAZAPI (CLEAN ARCHITECTURE v2.2)")
    print(f"      Servidor: {settings.server_url}")
    print(f"      Filtro: {', '.join(settings.filter_keywords)}")
    print(f"      Termos Ignorados: {', '.join(settings.ignore_keywords)}")
    print(f"      Intervalo: {settings.check_interval_minutes} minutos")
    print("=" * 82)

    # Injeção de Dependências
    client = UazapiClient(server_url=settings.server_url, admin_token=settings.admin_token)
    evaluator = MonitorEvaluator(filter_keywords=settings.filter_keywords, ignore_keywords=settings.ignore_keywords)
    repository = JsonFileRepository(file_path=settings.status_file)
    notifier = WindowsToastNotifier()

    service = ChipMonitorService(
        client=client,
        evaluator=evaluator,
        repository=repository,
        notifier=notifier
    )

    interval_seconds = settings.check_interval_minutes * 60

    while True:
        try:
            report = service.run_cycle()
            render_table(report)
        except Exception as e:
            logger.error(f"Erro inesperado no ciclo: {e}", exc_info=True)
            notifier.notify_error("Erro de Ciclo", str(e))

        logger.info(f"Próxima checagem em {settings.check_interval_minutes} minutos.")

        try:
            for remaining in range(interval_seconds, 0, -1):
                mins, secs = divmod(remaining, 60)
                sys.stdout.write(f"\r[Aguardando próximo ciclo: {mins:02d}:{secs:02d}]   ")
                sys.stdout.flush()
                time.sleep(1)
            print("\r" + " " * 45 + "\r", end="")
        except KeyboardInterrupt:
            print("\nMonitor encerrado pelo usuário.")
            break

if __name__ == "__main__":
    main()
