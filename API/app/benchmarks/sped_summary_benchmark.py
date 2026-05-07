from __future__ import annotations

import argparse
import time
import tracemalloc
from pathlib import Path

from app.domain.sped.reader import resumir_registros_sped_bytes, resumir_registros_sped_bytes_polars


def _medir(nome: str, func, conteudo: bytes) -> dict:
    tracemalloc.start()
    inicio = time.perf_counter()
    registros, total_linhas = func(conteudo)
    duracao_ms = round((time.perf_counter() - inicio) * 1000, 2)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "implementacao": nome,
        "duracao_ms": duracao_ms,
        "memoria_pico_kb": round(pico / 1024, 2),
        "total_linhas": total_linhas,
        "total_registros": sum(registros.values()),
        "registros_distintos": len(registros),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark simples do resumo tecnico SPED.")
    parser.add_argument("arquivo", type=Path)
    args = parser.parse_args()

    conteudo = args.arquivo.read_bytes()
    for resultado in (
        _medir("python_atual", resumir_registros_sped_bytes, conteudo),
        _medir("polars_opcional", resumir_registros_sped_bytes_polars, conteudo),
    ):
        print(resultado)


if __name__ == "__main__":
    main()
