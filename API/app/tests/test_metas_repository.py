from app.repositories.metas.metas_repository import MetasRepository


class _FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConn:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows

    def cursor(self):
        return _FakeCursor(row=self._row, rows=self._rows)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_obter_filtra_por_empresa_id(monkeypatch):
    repo = MetasRepository()
    row = {"id": 1, "empresa_id": 1, "titulo": "Meta X"}
    fake_conn = _FakeConn(row=row)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.obter(meta_id=1, empresa_id=1)

    assert resultado == row


def test_obter_retorna_none_quando_nao_encontrado(monkeypatch):
    repo = MetasRepository()
    fake_conn = _FakeConn(row=None)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.obter(meta_id=999, empresa_id=1)

    assert resultado is None


def test_listar_retorna_linhas(monkeypatch):
    repo = MetasRepository()
    rows = [{"id": 1, "empresa_id": 1}, {"id": 2, "empresa_id": 1}]
    fake_conn = _FakeConn(rows=rows)
    monkeypatch.setattr(repo, "_connect", lambda: fake_conn)

    resultado = repo.listar(empresa_id=1, status=None, indicador_id=None)

    assert resultado == rows
