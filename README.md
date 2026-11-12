# Monitor de Chips Uazapi (Clean Architecture)

Automação em **Clean Architecture** e **Módulos Profundos** para monitorar o status dos chips WhatsApp conectados na Uazapi via API HTTP oficial, com alertas visuais e sonoros no **Windows**.

---

## 🏛️ Arquitetura do Sistema

O projeto segue os princípios de **Clean Code** e **Ports & Adapters**:

```
Automação Chips/
├── config.py                 # Configurações com validação Fail-Fast (.env)
├── core/                     # NÚCLEO PURO DE DOMÍNIO (Zero dependências externas)
│   ├── models.py             # Entidades tipadas: Chip, ChipStatus, EvaluationReport
│   └── evaluator.py          # Avaliador de regras de transição de status e filtros
├── ports/                    # INTERFACES FORMAIS (Contratos)
│   ├── notifier.py           # Interface Notifier
│   └── repository.py         # Interface StateRepository
├── adapters/                 # ADAPTADORES CONCRETOS
│   ├── uazapi_client.py      # Cliente HTTP para API Uazapi v2.6.9+
│   ├── windows_notifier.py   # Notificador Windows (Balão + Toast + Som)
│   └── json_repository.py    # Persistência atômica em chips_status.json
├── service.py                # ChipMonitorService (Use Case / Orquestrador)
├── monitor_chips.py          # Entrypoint de execução CLI
└── tests/                    # Testes Unitários de Domínio
```

---

## 🔔 Regras de Notificação & Prevenção de Spam

1. **Alerta Apenas na Primeira Queda (*Edge-Triggered*)**:
   * Quando um chip cai (`connected` &rarr; `disconnected`), o Windows emite o alerta imediatamente.
   * Nos ciclos seguintes (20min, 40min, etc.), se o chip **continuar desconectado**, ele é marcado como `[DESCONECTADO (Silenciado)]` no terminal e **NÃO gera notificações repetidas**, evitando spam.
2. **Silenciamento por Nome (`IGNORE_KEYWORDS`)**:
   * Se você editar o nome da instância no painel adicionando termos como `BAN`, `ANÁLISE`, `ANALISE` ou `BANIDO` (ex: `NIO 01 BAN EM ANÁLISE`), a automação **ignora automaticamente** o chip, sem monitorá-lo nem disparar alertas.
3. **Notificação Visual Garantida no Windows**:
   * O novo adaptador combina:
     * **Balão do Sistema na Barra de Tarefas (System Tray)**: 100% visível independente do Assistente de Foco/Não Perturbe.
     * **Notificação Toast moderna** na Central de Ações do Windows.
     * **Alerta sonoro** nativo do sistema para chamar a atenção imediatamente.

---

## 🚀 Como Executar

### 1. Configurar o `.env`
Defina a URL do seu servidor e o token de administração:
```env
SERVER_URL=https://seu-servidor.uazapi.com
ADMIN_TOKEN=seu_admin_token_do_painel
FILTER_KEYWORDS=NIO,BMG
IGNORE_KEYWORDS=BAN,ANALISE,ANÁLISE,BANIDO,DESCARTE
CHECK_INTERVAL_MINUTES=20
```

### 2. Rodar o Monitor
```powershell
python monitor_chips.py
```

### 3. Rodar os Testes Unitários
Para validar que a lógica de negócio está 100% íntegra:
```powershell
python -m unittest discover tests
```
