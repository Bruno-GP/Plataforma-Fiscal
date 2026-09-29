from app.services.cnpj.cnae_classifier_service import (
    CnaeClassificationRule,
    CnaeClassifierService,
    normalizar_cnae,
)


def test_normalizar_cnae_mantem_apenas_digitos():
    assert normalizar_cnae("47.11-3/02") == "4711302"
    assert normalizar_cnae(4711302) == "4711302"
    assert normalizar_cnae(None) == ""


def test_classificar_comercio_varejista_por_prefixo():
    resultado = CnaeClassifierService().classificar("4711-3/02")

    assert resultado.cnae_codigo == "4711302"
    assert resultado.segmento_chave == "comercio_varejista"
    assert resultado.segmento_nome == "Comercio varejista"
    assert resultado.cnae_prefixo == "47"
    assert resultado.confianca == 0.8


def test_classificar_industria_transporte_e_servicos_por_prefixo():
    service = CnaeClassifierService()

    assert service.classificar("1091101").segmento_chave == "industria"
    assert service.classificar("4930202").segmento_chave == "transporte_logistica"
    assert service.classificar("7020400").segmento_chave == "servicos_profissionais"


def test_classificar_prioriza_codigo_exato_sobre_prefixo():
    service = CnaeClassifierService(
        rules=(
            CnaeClassificationRule(
                segmento_chave="comercio_varejista",
                segmento_nome="Comercio varejista",
                cnae_prefixo="47",
                prioridade=100,
            ),
            CnaeClassificationRule(
                segmento_chave="alimentacao",
                segmento_nome="Alimentacao",
                cnae_codigo="4711302",
                prioridade=10,
            ),
        )
    )

    resultado = service.classificar("4711302")

    assert resultado.segmento_chave == "alimentacao"
    assert resultado.segmento_nome == "Alimentacao"
    assert resultado.confianca == 1.0


def test_classificar_cnae_desconhecido_retorna_sem_segmento():
    resultado = CnaeClassifierService().classificar("0111301")

    assert resultado.cnae_codigo == "0111301"
    assert resultado.segmento_chave is None
    assert resultado.segmento_nome is None
    assert resultado.confianca == 0.0
