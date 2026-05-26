from datetime import date
from decimal import Decimal

import pytest

from app.domain.nfe.extractor import ItemNota, NotaExtraida
from app.services.fiscal_analysis import (
    FiscalDimensionConfig,
    _adicionar_limite,
    _construir_case_categoria_fiscal,
    obter_regiao_por_uf,
)
from app.services.nfe.nfe_consulta_service import NFeConsultaService
from app.services.nfe.nfe_itens_service import _limitar_texto
from app.services.nfe.nfe_notas_service import NFeNotasService
from app.services.reforma_tributaria.reforma_tributaria_sync_service import ReformaTributariaSyncService
from app.services.sped.sped_importacao_service import SpedImportacaoService


def _sped_importacao_service() -> SpedImportacaoService:
    service = object.__new__(SpedImportacaoService)
    service._cache_municipios = {}
    service._municipios_por_codigo = {
        "3550308": "Sao Paulo",
        "4205407": "Florianopolis",
    }
    return service


def _nfe_consulta_service() -> NFeConsultaService:
    return object.__new__(NFeConsultaService)


def _nfe_notas_service() -> NFeNotasService:
    return object.__new__(NFeNotasService)


def _reforma_sync_service() -> ReformaTributariaSyncService:
    return object.__new__(ReformaTributariaSyncService)


def _nota(*cfops: str) -> NotaExtraida:
    itens = [
        ItemNota(
            numero_item=index + 1,
            codigo_produto=f"P{index + 1}",
            descricao="Produto",
            ncm="12345678",
            cfop=cfop,
            unidade="UN",
            quantidade=Decimal("1"),
            valor_unitario=Decimal("10"),
            valor_total=Decimal("10"),
        )
        for index, cfop in enumerate(cfops)
    ]
    return NotaExtraida(
        chave="chave",
        numero_nf=1,
        emitente_cnpj="12345678000190",
        modelo="55",
        data_emissao=date(2025, 3, 1),
        natureza_operacao="Venda",
        destinatario_documento="99999999000199",
        destinatario_nome="Cliente",
        destinatario_cidade="Sao Paulo",
        destinatario_uf="SP",
        valor_total_nf=Decimal("10"),
        valor_icms=Decimal("1"),
        valor_ipi=Decimal("0"),
        valor_pis=Decimal("0"),
        valor_cofins=Decimal("0"),
        valor_produtos=Decimal("10"),
        valor_desconto=Decimal("0"),
        valor_frete=Decimal("0"),
        itens=itens,
    )


def test_sped_importacao_normalizadores_preservam_documentos_e_cnpj():
    service = _sped_importacao_service()

    assert service._normalizar_cnpj("12.345.678/0001-90") == "12345678000190"
    assert service._normalizar_cnpj("123") is None
    assert service._normalizar_documento("123.456.789-00") == "12345678900"
    assert service._normalizar_documento("abc") is None


def test_sped_importacao_extrai_cnpj_do_registro_0000_em_latin1():
    service = _sped_importacao_service()
    conteudo = "\n|9999|ignorado|\n|0000|018|0|01012025|31012025|EMPRESA|12.345.678/0001-90|\n".encode("latin-1")

    assert service._extrair_cnpj_sped(conteudo) == "12345678000190"
    assert service._extrair_cnpj_sped(b"|C100|sem registro 0000|") is None


def test_sped_importacao_conversoes_numericas_e_data_sao_tolerantes():
    service = _sped_importacao_service()

    assert service._to_int(" 42 ") == 42
    assert service._to_int("abc") is None
    assert service._to_decimal("1.234,56") == Decimal("1234.56")
    assert service._to_decimal("invalido") == Decimal("0")
    assert service._calcular_valor_unitario(Decimal("10"), Decimal("2")) == Decimal("5")
    assert service._calcular_valor_unitario(Decimal("10"), Decimal("0")) == Decimal("0")
    assert service._to_date("01032025") == date(2025, 3, 1)
    assert service._to_date("20250301") is None


def test_sped_importacao_municipio_e_uf_preservam_fallbacks():
    service = _sped_importacao_service()

    assert service._extrair_uf_de_cod_municipio("3550308") == "SP"
    assert service._extrair_uf_de_cod_municipio("4205407") == "SC"
    assert service._extrair_uf_de_cod_municipio("99") is None
    assert service._obter_nome_municipio("3550308") == "Sao Paulo"
    assert service._obter_nome_municipio("0000000") is None


def test_nfe_consulta_normaliza_cnpj_filtro_e_rejeita_zerado():
    service = _nfe_consulta_service()

    assert service._normalizar_cnpj_filtro("12.345.678/0001-90") == "12345678000190"
    assert service._normalizar_cnpj_filtro("00.000.000/0000-00") is None
    assert service._normalizar_cnpj_filtro("00.000.000/0000-00", permitir_zerado=True) == "00000000000000"
    assert service._normalizar_cnpj_filtro("123") == "123"


def test_nfe_consulta_monta_filtros_vendas_itens_com_periodo():
    service = _nfe_consulta_service()

    where_clause, params = service._montar_filtros_vendas_itens(
        "12.345.678/0001-90",
        periodo_ano=2025,
        periodo_mes=3,
    )

    assert "regexp_replace(COALESCE(n.emitente_cnpj, ''), '\\D', '', 'g') = %s" in where_clause
    assert "LEFT(regexp_replace(COALESCE(i.cfop, ''), '\\D', '', 'g'), 1) IN ('5','6','7')" in where_clause
    assert "EXTRACT(YEAR FROM n.data_emissao) = %s" in where_clause
    assert "EXTRACT(MONTH FROM n.data_emissao) = %s" in where_clause
    assert params == ["12345678000190", 2025, 3]


def test_nfe_consulta_monta_filtros_vendas_itens_exige_cnpj_valido():
    service = _nfe_consulta_service()

    with pytest.raises(ValueError, match="emitente_cnpj"):
        service._montar_filtros_vendas_itens("00000000000000")


def test_nfe_notas_normaliza_cfop_e_filtra_por_tabela_de_referencia(monkeypatch):
    service = _nfe_notas_service()
    monkeypatch.setattr(service, "obter_cfops_venda", lambda conn: {"5102"})

    notas = [
        _nota("5.102"),
        _nota("1102"),
        _nota("6108"),
    ]

    filtradas = service.filtrar_notas_com_cfop_venda(conn=object(), notas=notas)

    assert [nota.itens[0].cfop for nota in filtradas] == ["5.102"]
    assert service._normalizar_cfop("5.102") == "5102"
    assert service._normalizar_cfop(None) == ""


def test_nfe_notas_filtra_por_prefixo_quando_cfop_referencia_vazio(monkeypatch):
    service = _nfe_notas_service()
    monkeypatch.setattr(service, "obter_cfops_venda", lambda conn: set())

    filtradas = service.filtrar_notas_com_cfop_venda(
        conn=object(),
        notas=[_nota("1102"), _nota("5102"), _nota("6108"), _nota("7101")],
    )

    assert [nota.itens[0].cfop for nota in filtradas] == ["5102", "6108", "7101"]


def test_nfe_itens_limitar_texto_preserva_truncamento():
    assert _limitar_texto(None, 5) == ""
    assert _limitar_texto(" abc ", 5) == "abc"
    assert _limitar_texto("abcdef", 3) == "abc"


def test_reforma_sync_xml_helpers_preservam_busca_por_nome_local():
    service = _reforma_sync_service()
    root = service._parse_xml_importado(
        memoryview(
            b"""
            <nfe:root xmlns:nfe="http://www.portalfiscal.inf.br/nfe">
              <nfe:det>
                <nfe:prod>
                  <nfe:cProd>001</nfe:cProd>
                </nfe:prod>
              </nfe:det>
              <nfe:det><nfe:prod><nfe:cProd>002</nfe:cProd></nfe:prod></nfe:det>
            </nfe:root>
            """
        )
    )

    det = service._encontrar_elemento_local(root, "det")
    prod = service._encontrar_filho_local(det, "prod")

    assert root is not None
    assert service._nome_local(root) == "root"
    assert service._nome_local(None) == ""
    assert service._texto_filho_local(prod, "cProd") == "001"
    assert len(service._encontrar_filhos_local(root, "det")) == 2
    assert service._parse_xml_importado(b"<xml") is None


def test_reforma_sync_normaliza_numero_nf_preserva_zeros_e_texto():
    service = _reforma_sync_service()

    assert service._normalizar_numero_nf("000123") == "123"
    assert service._normalizar_numero_nf("0000") == "0"
    assert service._normalizar_numero_nf("ABC001") == "ABC001"
    assert service._normalizar_numero_nf("") == ""


class FakeResumoCursor:
    def __init__(self, values):
        self.values = list(values)
        self.queries = []

    def execute(self, sql, params):
        self.queries.append((sql, params))

    def fetchone(self):
        return [self.values.pop(0)]


def test_reforma_sync_coletar_resumo_periodo_preserva_ordem_dos_contadores():
    service = _reforma_sync_service()
    cur = FakeResumoCursor([2, 5, 7, 3, 11, 1])

    resumo = service._coletar_resumo_periodo(cur, "12345678000190", 2025, 3, "xml")

    assert resumo == {
        "documentos_tributos": 2,
        "itens_tributos": 5,
        "debitos": 7,
        "creditos": 3,
        "memorias": 11,
        "apuracoes": 1,
    }
    assert len(cur.queries) == 6
    assert cur.queries[0][1] == ("12345678000190", 2025, 3, "xml")
    assert cur.queries[-1][1] == ("12345678000190", 2025, 3)


def test_fiscal_analysis_helpers_preservam_limite_regiao_e_case_categoria():
    sql, params = _adicionar_limite("SELECT 1", ["a"], 10)
    sem_limite_sql, sem_limite_params = _adicionar_limite("SELECT 1", ["a"], None)
    config = FiscalDimensionConfig(
        from_clause="public.notas",
        company_filter_expr="n.cnpj",
        date_expr="n.data_emissao",
        document_id_expr="n.id",
        amount_expr="n.valor",
        dimension_code_count_expr="i.cfop",
        dimension_code_display_expr="i.cfop",
        dimension_description_expr="c.descricao",
        category_description_expr="c.descricao",
        category_fallback_description_expr="n.natureza_operacao",
        sale_condition_expr="i.cfop LIKE '5%'",
    )
    case_sql = _construir_case_categoria_fiscal(config)

    assert sql == "SELECT 1\nLIMIT %s"
    assert params == ["a", 10]
    assert sem_limite_sql == "SELECT 1"
    assert sem_limite_params == ["a"]
    assert obter_regiao_por_uf(" sp ") == "Sudeste"
    assert obter_regiao_por_uf("xx") is None
    assert "COALESCE(c.descricao, n.natureza_operacao, '')" in case_sql
    assert "Venda" in case_sql
    assert "Bonifica" in case_sql
