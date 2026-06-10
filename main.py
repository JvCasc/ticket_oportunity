"""Ponto de entrada do sistema de monitoramento de preços de passagens aéreas."""

import logging
from datetime import datetime

from dotenv import load_dotenv

from analyzer import analisar_precos
from config import ANTI_SPAM_HORAS, ROTAS
from fetcher import buscar_precos
from notifier import enviar_alerta
from storage import alerta_ja_enviado, inicializar_banco, registrar_alerta, salvar_precos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Executa um ciclo completo de monitoramento de preços para todas as rotas."""
    load_dotenv()

    inicio = datetime.now()
    logger.info("=== Iniciando monitoramento de preços de passagens ===")

    inicializar_banco()

    total_alertas = 0

    for rota in ROTAS:
        logger.info("--- Processando rota %s -> %s ---", rota.origem, rota.destino)

        precos = buscar_precos(rota.origem, rota.destino)
        if not precos:
            logger.warning("Nenhum preço obtido para %s -> %s; pulando rota", rota.origem, rota.destino)
            continue

        oportunidades = analisar_precos(rota, precos)
        logger.info(
            "%d oportunidade(s) encontrada(s) para %s -> %s",
            len(oportunidades), rota.origem, rota.destino,
        )

        for oportunidade in oportunidades:
            if alerta_ja_enviado(rota.origem, rota.destino, oportunidade.data_voo, ANTI_SPAM_HORAS):
                logger.info(
                    "Alerta já enviado nas últimas %dh para %s -> %s em %s; ignorando",
                    ANTI_SPAM_HORAS, rota.origem, rota.destino, oportunidade.data_voo,
                )
                continue

            if enviar_alerta(oportunidade):
                registrar_alerta(rota.origem, rota.destino, oportunidade.data_voo, oportunidade.preco_atual)
                total_alertas += 1

        salvar_precos(rota.origem, rota.destino, precos)

    duracao = (datetime.now() - inicio).total_seconds()
    logger.info(
        "=== Monitoramento concluído em %.1fs - %d alerta(s) enviado(s) ===",
        duracao, total_alertas,
    )


if __name__ == "__main__":
    main()
