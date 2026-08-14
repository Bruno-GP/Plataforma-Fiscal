from app.repositories.metas.indicadores_repository import IndicadoresRepository


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_listar_filtra_por_perfil(monkeypatch):
    repo = IndicadoresRepository()
    fake_rows = [
        {"id": 1, "chave": "faturamento", "nome": "Faturamento", "unidade": "moeda", "direcao_boa": "maior_melhor", "perfil": "xml"}
    ]
    fake_conn = _FakeConn(fake_rows)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.listar(perfil="xml")

    assert resultado == fake_rows


def test_historico_retorna_lista_vazia_sem_dado(monkeypatch):
    repo = IndicadoresRepository()
    fake_conn = _FakeConn([])
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.historico(empresa_id=1, indicador_id=1, meses=12)

    assert resultado == []
