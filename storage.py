"""Camada de persistência em SQLite para o histórico de preços e alertas."""

import logging
import sqlite3
from datetime import date, datetime, timedelta

from config import CAMINHO_BANCO

logger = logging.getLogger(__name__)


db = sqlite3.connect(CAMINHO_BANCO)
banco = db.cursor()


def inicializar_banco():
    """Cria as tabelas do banco de dados, caso ainda não existam."""
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origem TEXT NOT NULL,
            destino TEXT NOT NULL,
            data_voo DATE NOT NULL,
            preco REAL NOT NULL,
            coletado_em DATETIME NOT NULL
        )
        """
    )
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origem TEXT NOT NULL,
            destino TEXT NOT NULL,
            data_voo DATE NOT NULL,
            preco REAL NOT NULL,
            enviado_em DATETIME NOT NULL
        )
        """
    )
    banco.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_price_history_rota_data
        ON price_history (origem, destino, data_voo)
        """
    )
    banco.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alerts_sent_rota_data
        ON alerts_sent (origem, destino, data_voo)
        """
    )
    logger.info("Banco de dados '%s' inicializado", CAMINHO_BANCO)


def salvar_precos(origem: str, destino: str, precos: dict[date, float]):
    """Salva no histórico os preços coletados para uma rota."""
    if not precos:
        return

    coletado_em = datetime.now().isoformat(timespec="seconds")
    banco.executemany(
        """
        INSERT INTO price_history (origem, destino, data_voo, preco, coletado_em)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (origem, destino, data_voo.isoformat(), preco, coletado_em)
            for data_voo, preco in precos.items()
        ],
    )
    logger.info("%d preço(s) salvo(s) no histórico para %s -> %s", len(precos), origem, destino)
    db.commit()


def buscar_historico(origem: str, destino: str, data_voo: date) -> list[float]:
    """Retorna a lista de preços já coletados para a rota e data informadas."""
    linhas = banco.execute(
        """
        SELECT preco FROM price_history
        WHERE origem = ? AND destino = ? AND data_voo = ?
        ORDER BY coletado_em
        """,
        (origem, destino, data_voo.isoformat()),
    ).fetchall()
    return [preco for (preco,) in linhas]



def calcular_media_historica(origem: str, destino: str, data_voo: date) -> tuple[float | None, int]:
    """Calcula a média histórica de preços para a rota e data informadas.

    Retorna uma tupla (média, quantidade_de_registros). A média é ``None``
    quando ainda não há nenhum registro histórico.
    """
    historico = buscar_historico(origem, destino, data_voo)
    if not historico:
        return None, 0
    return sum(historico) / len(historico), len(historico)


def registrar_alerta(origem: str, destino: str, data_voo: date, preco: float):
    """Registra que um alerta foi enviado para a rota, data e preço informados."""
    enviado_em = datetime.now().isoformat(timespec="seconds")
    banco.execute(
        """
        INSERT INTO alerts_sent (origem, destino, data_voo, preco, enviado_em)
        VALUES (?, ?, ?, ?, ?)
        """,
        (origem, destino, data_voo.isoformat(), preco, enviado_em),
    )
    logger.info("Alerta registrado para %s -> %s em %s (R$ %.2f)", origem, destino, data_voo, preco)
    db.commit()

def alerta_ja_enviado(origem: str, destino: str, data_voo: date, horas: int) -> bool:
    """Verifica se já foi enviado um alerta para a rota e data dentro da janela de horas."""
    limite = (datetime.now() - timedelta(hours=horas)).isoformat(timespec="seconds")
    linha = banco.execute(
        """
        SELECT 1 FROM alerts_sent
        WHERE origem = ? AND destino = ? AND data_voo = ? AND enviado_em >= ?
        LIMIT 1
        """,
        (origem, destino, data_voo.isoformat(), limite),
    ).fetchone()
    return linha is not None
