from app.workers import metas_tasks


class FakeEmpresasRepository:
    def __init__(self, empresas):
        self._empresas = empresas

    def listar_empresas_xml_ativas(self):
        return self._empresas


def test_materializa_todas_empresas_xml(monkeypatch):
    monkeypatch.setattr(
        metas_tasks,
        "_repositorio_empresas",
        lambda: FakeEmpresasRepository([(1, "11111111000191"), (2, "22222222000192")]),
    )

    chamadas = []
    monkeypatch.setattr(
        metas_tasks,
        "_materializar_empresa",
        lambda empresa_id, cnpj: chamadas.append((empresa_id, cnpj)) or 4,
    )

    resultado = metas_tasks.materializar_indicadores_historico_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_processadas"] == 2
    assert resultado["linhas_gravadas"] == 8
    assert chamadas == [(1, "11111111000191"), (2, "22222222000192")]


def test_falha_em_uma_empresa_nao_aborta_as_demais(monkeypatch):
    monkeypatch.setattr(
        metas_tasks,
        "_repositorio_empresas",
        lambda: FakeEmpresasRepository([(1, "11111111000191"), (2, "22222222000192")]),
    )

    def _materializar(empresa_id, cnpj):
        if empresa_id == 2:
            raise RuntimeError("falha de conexao")
        return 4

    monkeypatch.setattr(metas_tasks, "_materializar_empresa", _materializar)

    resultado = metas_tasks.materializar_indicadores_historico_task.run()

    assert resultado["status"] == "SUCCESS"
    assert resultado["empresas_processadas"] == 1
    assert resultado["empresas_falha"] == 1
