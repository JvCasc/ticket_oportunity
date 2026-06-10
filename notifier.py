"""Envio de notificações de oportunidades via API REST do Telegram."""

import logging
import os
import urllib.parse
from datetime import date

import requests

from analyzer import Oportunidade
from config import MOEDA

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

MESES_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


def _formatar_data(data_voo: date) -> str:
    """Formata a data no padrão '10 de agosto de 2026'."""
    return f"{data_voo.day} de {MESES_PT[data_voo.month]} de {data_voo.year}"


def _formatar_preco(preco: float) -> str:
    """Formata um preço em reais no padrão 'R$ 1.950'."""
    return f"R$ {preco:,.0f}".replace(",", ".")


def montar_link_google_flights(origem: str, destino: str, data_voo: date) -> str:
    """Monta um link de busca direto (somente ida) para a rota e data no Google Flights.

    Sem `curr`/`hl`/`gl`, o Google mostra preços na moeda/região do visitante,
    que pode divergir bastante do preço (em `MOEDA`) encontrado pela busca.
    """
    consulta = f"one-way flights from {origem} to {destino} on {data_voo.isoformat()}"
    parametros = {
        "q": consulta,
        "curr": MOEDA,
        "hl": "pt-BR",
        "gl": "BR",
    }
    return f"https://www.google.com/travel/flights?{urllib.parse.urlencode(parametros)}"


def _montar_mensagem(oportunidade: Oportunidade) -> str:
    """Monta o texto (Markdown) da mensagem a partir de uma oportunidade."""
    linhas = [
        "✈️ *OPORTUNIDADE ENCONTRADA*",
        "",
        f"*{oportunidade.origem} → {oportunidade.destino}*",
        f"📅 {_formatar_data(oportunidade.data_voo)}",
        f"💰 {_formatar_preco(oportunidade.preco_atual)}",
    ]

    if oportunidade.media_historica is not None and oportunidade.queda_percentual is not None:
        linhas.append(
            f"📉 {oportunidade.queda_percentual:.0f}% abaixo da média histórica "
            f"(média: {_formatar_preco(oportunidade.media_historica)})"
        )
    else:
        linhas.append("📉 Preço abaixo do teto configurado para a rota")

    link = montar_link_google_flights(oportunidade.origem, oportunidade.destino, oportunidade.data_voo)
    linhas.append(f"🔗 [Ver no Google Flights]({link})")

    return "\n".join(linhas)


def enviar_alerta(oportunidade: Oportunidade) -> bool:
    """Envia uma notificação via Telegram para a oportunidade informada.

    Retorna True se a mensagem foi enviada com sucesso, False caso contrário.
    """
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error("TELEGRAM_TOKEN e/ou TELEGRAM_CHAT_ID não configurados; alerta não enviado")
        return False

    mensagem = _montar_mensagem(oportunidade)
    url = TELEGRAM_API_URL.format(token=token)

    try:
        resposta = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": mensagem,
                "parse_mode": "Markdown",
            },
            timeout=15,
        )
        resposta.raise_for_status()
    except requests.RequestException as erro:
        logger.error(
            "Falha ao enviar alerta via Telegram para %s -> %s em %s: %s",
            oportunidade.origem, oportunidade.destino, oportunidade.data_voo, erro,
        )
        return False

    logger.info(
        "Alerta enviado via Telegram para %s -> %s em %s",
        oportunidade.origem, oportunidade.destino, oportunidade.data_voo,
    )
    return True
