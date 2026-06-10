"""Configurações centrais do sistema de monitoramento de passagens aéreas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rota:
    """Representa uma rota de voo monitorada."""

    origem: str
    destino: str
    teto_preco: float | None = None


# Rotas monitoradas. "teto_preco" é opcional: quando definido, qualquer preço
# abaixo desse valor já é considerado uma oportunidade (regra do teto absoluto).
ROTAS = [
    Rota(origem="GRU", destino="AMS", teto_preco=1700.0),
    Rota(origem="GRU", destino="CUZ", teto_preco=800.0),
]

# Quantidade de dias à frente (a partir de amanhã) para buscar preços.
JANELA_DIAS = 180

# Percentual mínimo de queda em relação à média histórica da rota+data
# para considerar o preço uma oportunidade (regra da queda percentual).
QUEDA_MINIMA_PERCENT = 40

# Quantidade mínima de registros históricos (rota+data) necessária antes de
# aplicar a regra de queda percentual. Evita falsos positivos quando o
# histórico ainda é pequeno (início de operação do sistema).
MINIMO_HISTORICO_QUEDA = 7

# Janela, em horas, durante a qual a mesma rota+data não gera um novo alerta.
ANTI_SPAM_HORAS = 48

# Moeda usada nas buscas de preço.
MOEDA = "BRL"

# Caminho do arquivo do banco de dados SQLite.
CAMINHO_BANCO = "prices.db"
