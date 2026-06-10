"""Detecção de oportunidades (preços anormalmente baixos) nas rotas monitoradas."""

import logging
from dataclasses import dataclass
from datetime import date

from config import MINIMO_HISTORICO_QUEDA, QUEDA_MINIMA_PERCENT, Rota
from storage import calcular_media_historica

logger = logging.getLogger(__name__)

REGRA_QUEDA_PERCENTUAL = "queda_percentual"
REGRA_TETO_ABSOLUTO = "teto_absoluto"


@dataclass(frozen=True)
class Oportunidade:
    """Representa uma oportunidade de preço encontrada para uma rota+data."""

    origem: str
    destino: str
    data_voo: date
    preco_atual: float
    media_historica: float | None
    queda_percentual: float | None
    regras_disparadas: list[str]


def analisar_precos(rota: Rota, precos: dict[date, float]) -> list[Oportunidade]:
    """Analisa os preços coletados para uma rota e retorna as oportunidades encontradas.

    Regra 1 (queda percentual): preço atual < média histórica × (1 - QUEDA_MINIMA_PERCENT/100).
    Só é aplicada quando há pelo menos MINIMO_HISTORICO_QUEDA registros históricos.

    Regra 2 (teto absoluto): preço atual < teto definido na rota.

    As duas regras são independentes: qualquer uma que disparar gera uma oportunidade.
    """
    oportunidades = []

    for data_voo, preco_atual in precos.items():
        media_historica, qtd_historico = calcular_media_historica(rota.origem, rota.destino, data_voo)

        regras_disparadas = []
        queda_percentual = None

        if media_historica is not None:
            queda_percentual = (1 - preco_atual / media_historica) * 100

        if qtd_historico >= MINIMO_HISTORICO_QUEDA:
            limite_queda = media_historica * (1 - QUEDA_MINIMA_PERCENT / 100)
            if preco_atual < limite_queda:
                regras_disparadas.append(REGRA_QUEDA_PERCENTUAL)

        if rota.teto_preco is not None and preco_atual < rota.teto_preco:
            regras_disparadas.append(REGRA_TETO_ABSOLUTO)

        if regras_disparadas:
            logger.info(
                "Oportunidade encontrada: %s -> %s em %s (R$ %.2f, regras: %s)",
                rota.origem, rota.destino, data_voo, preco_atual, ", ".join(regras_disparadas),
            )
            oportunidades.append(
                Oportunidade(
                    origem=rota.origem,
                    destino=rota.destino,
                    data_voo=data_voo,
                    preco_atual=preco_atual,
                    media_historica=media_historica,
                    queda_percentual=queda_percentual,
                    regras_disparadas=regras_disparadas,
                )
            )

    return oportunidades
