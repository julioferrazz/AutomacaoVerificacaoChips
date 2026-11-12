import base64
import subprocess
import logging
from typing import List
from ports.notifier import Notifier
from core.models import ChipTransition

logger = logging.getLogger("WindowsNotifier")

class WindowsToastNotifier(Notifier):
    """
    Adaptador de notificações nativas para Windows.
    Garante que a notificação NÃO desapareça imediatamente:
    - Usa Toast persistente com scenario="reminder" (fica fixo na tela até o usuário interagir).
    - Salva na Central de Notificações com expiração de 4 horas.
    - Mantém o Balão da Barra de Tarefas aberto por 25 segundos em processo assíncrono (sem travar o monitor).
    - Toca alerta sonoro nativo.
    """
    def __init__(self, app_title: str = "Monitor de Chips Uazapi"):
        self.app_title = app_title

    def _dispatch_windows(self, title: str, message: str, is_warning: bool = True) -> bool:
        # Escapa caracteres para PowerShell e XML
        safe_title = title.replace('"', '`"').replace("'", "''")
        safe_msg = message.replace('"', '`"').replace("'", "''")

        xml_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        xml_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        icon_type = "Warning" if is_warning else "Info"
        sound_type = "Exclamation" if is_warning else "Asterisk"
        scenario_attr = 'scenario="reminder"' if is_warning else ''

        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing

        # 1. Alerta sonoro do sistema
        try {{ [System.Media.SystemSounds]::{sound_type}.Play() }} catch {{}}

        # 2. Toast Moderno Persistente (permanece na tela e na Central de Ações até ser dispensado)
        try {{
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xmlText = '<toast {scenario_attr}><visual><binding template="ToastGeneric"><text>{xml_title}</text><text>{xml_msg}</text></binding></visual><actions><action content="Dispensar" arguments="dismiss" activationType="background"/></actions></toast>'
            $xml.LoadXml($xmlText)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            $toast.ExpirationTime = [DateTimeOffset]::Now.AddHours(4)

            $appId = "{{1AC14E77-02E7-4E60-B747-A35370A4F2C0}}\\WindowsPowerShell\\v1.0\\powershell.exe"
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
        }} catch {{}}

        # 3. Balão na Barra de Tarefas mantido por 25 segundos (não fecha após 1s)
        try {{
            $balloon = New-Object System.Windows.Forms.NotifyIcon
            $balloon.Icon = [System.Drawing.SystemIcons]::{icon_type}
            $balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::{icon_type}
            $balloon.BalloonTipTitle = "{safe_title}"
            $balloon.BalloonTipText = "{safe_msg}"
            $balloon.Visible = $True
            $balloon.ShowBalloonTip(25000)
            Start-Sleep -Seconds 25
            $balloon.Dispose()
        }} catch {{}}
        """

        try:
            encoded_cmd = base64.b64encode(ps_script.encode("utf-16le")).decode("utf-8")
            # Dispara em background desacoplado (non-blocking) sem janela preta
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_cmd],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"Notificação persistente disparada em background: {title}")
            return True
        except Exception as e:
            logger.error(f"Falha ao acionar notificação do Windows: {e}")
            return False

    def notify_disconnections(self, drops: List[ChipTransition]) -> bool:
        if not drops:
            return True

        linhas = []
        for t in drops[:4]:
            c = t.chip
            line = f"• {c.name} ({c.number})"
            if c.last_disconnect_reason:
                line += f" - Motivo: {c.last_disconnect_reason}"
            linhas.append(line)

        total = len(drops)
        msg = f"ATENÇÃO: {total} chip(s) DESCONECTADO(S)!\n" + "\n".join(linhas)
        if total > 4:
            msg += f"\n(+ {total - 4} outros)"

        return self._dispatch_windows("Alerta: Chip Desconectado!", msg, is_warning=True)

    def notify_reconnections(self, reconnected: List[ChipTransition]) -> bool:
        if not reconnected:
            return True

        nomes = ", ".join([f"{t.chip.name} ({t.chip.number})" for t in reconnected[:3]])
        msg = f"Chip(s) reconectado(s) com sucesso: {nomes}"
        return self._dispatch_windows("Chip Reconectado", msg, is_warning=False)

    def notify_error(self, title: str, message: str) -> bool:
        return self._dispatch_windows(f"Erro: {title}", message[:150], is_warning=True)
