from app.domain.sped.reader import resumir_registros_sped_bytes, resumir_registros_sped_bytes_polars
import pytest


def test_sped_polars_equivalente_ao_parser_atual(fixtures_dir):
    pytest.importorskip("polars")
    conteudo = (fixtures_dir / "sped_valido.txt").read_bytes()

    atual = resumir_registros_sped_bytes(conteudo)
    otimizado = resumir_registros_sped_bytes_polars(conteudo)

    assert otimizado == atual
