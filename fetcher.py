"""Busca de preços de passagens aéreas no Google Flights via lib `flights` (fli)."""

import logging
import time
from datetime import date, datetime, timedelta

from fli.core import build_date_search_segments
from fli.models import Airport, DateSearchFilters, MaxStops, PassengerInfo, SeatType
from fli.search import SearchDates

from config import JANELA_DIAS, MOEDA

logger = logging.getLogger(__name__)

MAX_TENTATIVAS = 3
ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = 5


def buscar_precos(origem: str, destino: str) -> dict[date, float]:
    """Busca o preço mais barato de cada dia da janela configurada.

    Retorna um dicionário {data_voo: preco_em_reais}. Em caso de falha em
    todas as tentativas, ou se a busca não retornar resultados, retorna um
    dicionário vazio.
    """
    aeroporto_origem = getattr(Airport, origem)
    aeroporto_destino = getattr(Airport, destino)

    data_inicio = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    data_fim = (datetime.now() + timedelta(days=JANELA_DIAS)).strftime("%Y-%m-%d")

    logger.info("Buscando preços %s -> %s entre %s e %s", origem, destino, data_inicio, data_fim)

    segmentos, tipo_viagem = build_date_search_segments(
        origin=aeroporto_origem,
        destination=aeroporto_destino,
        start_date=data_inicio,
        is_round_trip=False,
    )

    filtros = DateSearchFilters(
        trip_type=tipo_viagem,
        passenger_info=PassengerInfo(adults=1),
        flight_segments=segmentos,
        stops=MaxStops.ANY,
        seat_type=SeatType.ECONOMY,
        from_date=data_inicio,
        to_date=data_fim,
    )

    cliente = SearchDates()
    resultados = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resultados = cliente.search(filtros, currency=MOEDA)
            break
        except Exception as erro:
            logger.warning(
                "Tentativa %d/%d de busca %s -> %s falhou: %s",
                tentativa, MAX_TENTATIVAS, origem, destino, erro,
            )
            if tentativa < MAX_TENTATIVAS:
                time.sleep(ESPERA_ENTRE_TENTATIVAS_SEGUNDOS)

    if resultados is None:
        logger.error("Falha ao buscar preços para %s -> %s após %d tentativas", origem, destino, MAX_TENTATIVAS)
        return {}

    if not resultados:
        logger.warning("Nenhum preço encontrado para %s -> %s", origem, destino)
        return {}

    precos = {resultado.date[0].date(): resultado.price for resultado in resultados}

    logger.info("%d preço(s) encontrado(s) para %s -> %s", len(precos), origem, destino)
    return precos
