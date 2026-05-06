from collections import Counter
from pathlib import Path
from io import StringIO

def resumir_registros_sped(arquivo_sped: str) -> tuple[Counter, int]:
  caminho = Path(arquivo_sped)
  if not caminho.exists() or not caminho.is_file():
    raise FileNotFoundError(f"Arquivo SPED não encontrado: {arquivo_sped}")
  
  return resumir_registros_sped_bytes(caminho.read_bytes())

def resumir_registros_sped_bytes(conteudo: bytes) -> tuple[Counter, int]:
  linhas = conteudo.decode("latin-1", errors="ignore").splitlines()

  contagem_registros: Counter = Counter()
  total_linhas = 0

  for linha in linhas:
    linha = linha.strip()
    if not linha:
      continue

    total_linhas += 1
    if linha.startswith("|"):
      partes = linha.split("|")
      if len(partes) > 2 and partes[1]:
        contagem_registros[partes[1]] += 1

  return contagem_registros, total_linhas


def resumir_registros_sped_bytes_polars(conteudo: bytes) -> tuple[Counter, int]:
  """Resumo tabular opcional para benchmark/equivalencia, sem alterar regra fiscal."""
  import polars as pl

  texto = conteudo.decode("latin-1", errors="ignore")
  linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
  if not linhas:
    return Counter(), 0

  df = pl.read_csv(
    StringIO("\n".join(linhas)),
    has_header=False,
    separator="|",
    infer_schema_length=0,
    truncate_ragged_lines=True,
  )

  if "column_2" not in df.columns:
    return Counter(), len(linhas)

  registros = (
    df.select(pl.col("column_2").alias("registro"))
    .filter(pl.col("registro").is_not_null() & (pl.col("registro") != ""))
    .group_by("registro")
    .len()
  )

  return Counter({row["registro"]: int(row["len"]) for row in registros.iter_rows(named=True)}), len(linhas)
