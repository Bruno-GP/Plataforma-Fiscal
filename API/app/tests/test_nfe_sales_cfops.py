from app.services.nfe.nfe_consulta_service import obter_cfops_faturamento_venda


def test_cfops_faturamento_venda_inclui_vendas_comuns():
    cfops = set(obter_cfops_faturamento_venda())

    assert "5101" in cfops
    assert "5102" in cfops
    assert "6101" in cfops
    assert "6102" in cfops


def test_cfops_faturamento_venda_exclui_transferencias():
    cfops = set(obter_cfops_faturamento_venda())

    assert "5152" not in cfops
    assert "6152" not in cfops
    assert "5151" not in cfops
    assert "6151" not in cfops
