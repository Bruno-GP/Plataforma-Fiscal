from decimal import Decimal
from typing import List
from collections import defaultdict
import logging
import psycopg
from psycopg.types.json import Json

from app.domain.nfe.extractor import NotaExtraida
from app.models.nfe.schemas import KPIsRelatorio
from app.services.nfe.postres_config import carregar_config_postgres

logger = logging.getLogger("KPICalculator")
logger.setLevel(logging.INFO)

def _serializar_decimais(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, list):
        return [_serializar_decimais(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _serializar_decimais(v) for k, v in valor.items()}
    return valor


class KPICalculator:
    def __init__(self):
        config = carregar_config_postgres()
        self.conn_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": config["user"],
            "password": config["password"],
            "connect_timeout": 5,
        }

    # =========================
    # CÁLCULO DOS KPIs
    # =========================
    def calcular(self, notas: List[NotaExtraida]) -> KPIsRelatorio:
        if not notas:
            return KPIsRelatorio()

        quantidade_notas = len(notas)
        total_vendas = sum(n.valor_total_nf for n in notas)
        valores = [n.valor_total_nf for n in notas]

        ticket_medio = (
            total_vendas / quantidade_notas
            if quantidade_notas else Decimal("0.00")
        )

        total_icms = sum(n.valor_icms for n in notas)
        total_ipi = sum(n.valor_ipi for n in notas)
        total_pis = sum(n.valor_pis for n in notas)
        total_cofins = sum(n.valor_cofins for n in notas)

        def percentual(v):
            return (v / total_vendas * 100) if total_vendas else Decimal("0")

        clientes = defaultdict(Decimal)
        for n in notas:
            nome = n.destinatario_nome or "CLIENTE NÃO IDENTIFICADO"
            cliente = nome.split("/", 1)[-1].strip()
            clientes[cliente] += n.valor_total_nf

        produtos = defaultdict(Decimal)
        for n in notas:
            for item in n.itens:
                produtos[item.descricao] += item.valor_total

        cidades = defaultdict(Decimal)
        for n in notas:
            cidade = (n.destinatario_cidade or "").strip()
            if not cidade:
                cidade = "Cidade não identificada"
            cidades[cidade] += n.valor_total_nf

        return KPIsRelatorio(
            total_vendas=total_vendas,
            quantidade_notas=quantidade_notas,
            ticket_medio=ticket_medio,
            maior_nota=max(valores),
            menor_nota=min(valores),
            total_icms=total_icms,
            total_ipi=total_ipi,
            total_pis=total_pis,
            total_cofins=total_cofins,
            top_clientes=[
                {"cliente": k, "valor_total": v, "percentual": percentual(v)}
                for k, v in sorted(clientes.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
            top_produtos=[
                {"produto": k, "valor_total": v, "percentual": percentual(v)}
                for k, v in sorted(produtos.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
            top_cidades=[
                {"cidade": k, "valor_total": v, "percentual": percentual(v)}
                for k, v in sorted(cidades.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
        )

    # =========================
    # REGISTRO DOS KPIs
    # =========================
    def registrar_kpis(
        self,
        processamento_id: int,
        emitente_cnpj: str,
        periodo_ano: int,
        periodo_mes: int,
        kpis: KPIsRelatorio,
        conn: psycopg.Connection | None = None
    ) -> int:
        sql = """
            INSERT INTO public.nfe_kpis (
                processamento_id,
                emitente_cnpj,
                periodo_ano,
                periodo_mes,
                total_vendas,
                quantidade_notas,
                ticket_medio,
                maior_nota,
                menor_nota,
                total_icms,
                total_ipi,
                total_pis,
                total_cofins,
                top_clientes,
                top_produtos,
                top_cidades
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (emitente_cnpj, periodo_ano, periodo_mes) DO UPDATE
            SET
                processamento_id = EXCLUDED.processamento_id,
                total_vendas = EXCLUDED.total_vendas,
                quantidade_notas = EXCLUDED.quantidade_notas,
                ticket_medio = EXCLUDED.ticket_medio,
                maior_nota = EXCLUDED.maior_nota,
                menor_nota = EXCLUDED.menor_nota,
                total_icms = EXCLUDED.total_icms,
                total_ipi = EXCLUDED.total_ipi,
                total_pis = EXCLUDED.total_pis,
                total_cofins = EXCLUDED.total_cofins,
                top_clientes = EXCLUDED.top_clientes,
                top_produtos = EXCLUDED.top_produtos,
                top_cidades = EXCLUDED.top_cidades;
        """

        payload = _serializar_decimais({
            "top_clientes": kpis.top_clientes,
            "top_produtos": kpis.top_produtos,
            "top_cidades": kpis.top_cidades,
        })

        valores = (
            processamento_id,
            emitente_cnpj,
            periodo_ano,
            periodo_mes,
            kpis.total_vendas,
            kpis.quantidade_notas,
            kpis.ticket_medio,
            kpis.maior_nota,
            kpis.menor_nota,
            kpis.total_icms,
            kpis.total_ipi,
            kpis.total_pis,
            kpis.total_cofins,
            Json(payload["top_clientes"]),
            Json(payload["top_produtos"]),
            Json(payload["top_cidades"]),
        )

        if conn is None:
            with psycopg.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, valores)
                    return cur.rowcount

        with conn.cursor() as cur:
            cur.execute(sql, valores)
            return cur.rowcount