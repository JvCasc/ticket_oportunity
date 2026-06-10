# Flight Monitor ✈️

Sistema de monitoramento de preços de passagens aéreas com notificações via
Telegram. Roda localmente 2x por dia (via Agendador de Tarefas do Windows),
busca os preços das rotas configuradas, salva o histórico em SQLite, detecta
quedas anormais de preço e envia um alerta no Telegram quando encontra uma
oportunidade.

## Como funciona

1. **fetcher.py** busca, para cada rota configurada, o preço mais barato de
   cada dia dentro de uma janela de `JANELA_DIAS` dias (usando a lib
   [`flights`](https://github.com/punitarani/fli), wrapper do Google Flights).
2. **analyzer.py** compara o preço atual de cada data com a média histórica
   salva no banco e com o teto de preço configurado para a rota. Duas regras
   independentes podem disparar um alerta:
   - **Queda percentual**: preço atual `< média histórica × (1 - QUEDA_MINIMA_PERCENT/100)`.
     Só é avaliada quando já existem pelo menos `MINIMO_HISTORICO_QUEDA`
     registros históricos para aquela rota+data (evita falsos positivos no
     início).
   - **Teto absoluto**: preço atual `< teto_preco` definido na rota.
3. **notifier.py** envia uma mensagem formatada em Markdown para o Telegram
   com o preço, a data, a comparação com a média histórica e um link direto
   para a busca no Google Flights.
4. **storage.py** salva o histórico de preços (`price_history`) e registra os
   alertas enviados (`alerts_sent`) em `prices.db` (SQLite), evitando
   re-alertar a mesma rota+data dentro de `ANTI_SPAM_HORAS` horas.
5. **main.py** orquestra todo o fluxo, com logs com timestamp em cada etapa.

## Estrutura do projeto

```
flight-monitor/
├── config.py       # rotas monitoradas e parâmetros (janela, limiares, etc.)
├── fetcher.py       # busca de preços no Google Flights
├── storage.py        # persistência em SQLite (histórico e alertas)
├── analyzer.py        # regras de detecção de oportunidades
├── notifier.py         # envio de notificações via Telegram
├── main.py              # orquestração e logs
├── monitorar.ps1         # script para execução local (Agendador de Tarefas)
├── pyproject.toml
├── uv.lock
└── .env.example
```

## Configuração das rotas

As rotas monitoradas ficam em [`config.py`](config.py), na lista `ROTAS`:

```python
ROTAS = [
    Rota(origem="GRU", destino="LIS", teto_preco=2500.0),
    Rota(origem="GRU", destino="MIA", teto_preco=2200.0),
]
```

- `origem` / `destino`: códigos IATA dos aeroportos (devem existir no enum
  `Airport` da lib `fli`).
- `teto_preco`: opcional. Se definido, qualquer preço abaixo desse valor já
  dispara um alerta (regra do teto absoluto), independente da média
  histórica.

Outros parâmetros ajustáveis em `config.py`:

| Parâmetro | Descrição | Padrão |
|---|---|---|
| `JANELA_DIAS` | Quantos dias à frente buscar preços | 90 |
| `QUEDA_MINIMA_PERCENT` | Queda mínima (%) abaixo da média histórica para alertar | 20 |
| `MINIMO_HISTORICO_QUEDA` | Registros históricos mínimos antes de aplicar a regra de queda percentual | 7 |
| `ANTI_SPAM_HORAS` | Horas para não re-alertar a mesma rota+data | 48 |
| `MOEDA` | Moeda usada nas buscas | BRL |

## Rodando localmente

### Pré-requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) instalado

### Instalação

```bash
# Clonar o repositório e entrar na pasta
cd flight-monitor

# Instalar as dependências (cria o .venv automaticamente)
uv sync
```

### Configurar as variáveis de ambiente

Copie o arquivo de exemplo e preencha com seu token e chat ID do Telegram:

```bash
cp .env.example .env
```

```
TELEGRAM_TOKEN=seu_token_do_botfather
TELEGRAM_CHAT_ID=seu_chat_id
```

Para obter essas informações:

1. Crie um bot com o [@BotFather](https://t.me/BotFather) e copie o token
   gerado em `TELEGRAM_TOKEN`.
2. Envie uma mensagem qualquer para o seu bot e acesse
   `https://api.telegram.org/bot<TELEGRAM_TOKEN>/getUpdates` para descobrir o
   `chat.id` da conversa — copie esse valor em `TELEGRAM_CHAT_ID`.

### Executar

```bash
uv run python main.py
```

Na primeira execução o banco `prices.db` é criado automaticamente (se ainda
não existir), com as tabelas `price_history` e `alerts_sent`.

## Automação local (Agendador de Tarefas do Windows)

O script [`monitorar.ps1`](monitorar.ps1) entra na pasta do projeto, roda
`uv run python main.py` e anexa toda a saída (logs) em `monitor.log`.

### 1. Testar o script manualmente

```powershell
.\monitorar.ps1
```

Confira o resultado em `monitor.log`. Tanto `prices.db` quanto `monitor.log`
ficam só na sua máquina (estão no `.gitignore`).

### 2. Registrar a tarefa agendada (7h e 19h)

Abra o PowerShell **como Administrador**, navegue até a pasta do projeto e
rode:

```powershell
$acao = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PWD\monitorar.ps1`""

$gatilho7h  = New-ScheduledTaskTrigger -Daily -At 7:00am
$gatilho19h = New-ScheduledTaskTrigger -Daily -At 7:00pm

Register-ScheduledTask -TaskName "FlightMonitor" `
    -Action $acao `
    -Trigger @($gatilho7h, $gatilho19h) `
    -Description "Monitoramento de precos de passagens aereas (2x/dia)"
```

Alternativamente, pela interface gráfica: abra o **Agendador de Tarefas**,
crie uma tarefa básica que execute `powershell.exe` com o argumento
`-NoProfile -ExecutionPolicy Bypass -File "C:\caminho\completo\monitorar.ps1"`,
com dois gatilhos diários (7h e 19h).

### 3. Verificar / remover a tarefa

```powershell
Get-ScheduledTask -TaskName "FlightMonitor"
Unregister-ScheduledTask -TaskName "FlightMonitor" -Confirm:$false
```

## Dependências

Gerenciadas via `uv` e declaradas em `pyproject.toml` / `uv.lock`:

- [`flights`](https://github.com/punitarani/fli) — busca de preços no Google Flights
- `requests` — chamadas à API do Telegram
- `python-dotenv` — carregamento de variáveis de ambiente locais (`.env`)
- `sqlite3` — nativo do Python, usado para persistência
