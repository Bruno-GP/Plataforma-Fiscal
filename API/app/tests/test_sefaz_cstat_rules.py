from app.domain.sefaz.cstat_rules import MAX_ITERACOES_PAGINACAO, decidir_paginacao


def test_cstat_137_para_sem_bloqueio():
    decisao = decidir_paginacao(cstat=137, iteracao_atual=1)
    assert decisao.continuar is False
    assert decisao.bloqueado is False
    assert decisao.motivo == "sem_novidade"


def test_cstat_138_continua_paginando_abaixo_do_teto():
    decisao = decidir_paginacao(cstat=138, iteracao_atual=1)
    assert decisao.continuar is True
    assert decisao.bloqueado is False


def test_cstat_138_no_teto_de_iteracoes_para_sem_bloqueio():
    decisao = decidir_paginacao(cstat=138, iteracao_atual=MAX_ITERACOES_PAGINACAO)
    assert decisao.continuar is False
    assert decisao.bloqueado is False
    assert decisao.motivo == "teto_iteracoes"


def test_cstat_656_bloqueia():
    decisao = decidir_paginacao(cstat=656, iteracao_atual=1)
    assert decisao.continuar is False
    assert decisao.bloqueado is True
    assert decisao.motivo == "consumo_indevido"


def test_cstat_desconhecido_para_com_motivo_descritivo():
    decisao = decidir_paginacao(cstat=999, iteracao_atual=1)
    assert decisao.continuar is False
    assert decisao.bloqueado is False
    assert "999" in decisao.motivo
