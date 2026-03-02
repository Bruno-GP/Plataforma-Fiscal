from collections import Counter
from pathlib import Path

def resumir_registros_sped(arquivo_sped: str) -> tuple[Counter, int]:
  caminho = Path(arquivo_sped)
  if not caminho.exists() or not caminho.is_file():
    raise FileNotFoundError(f"Arquivo SPED não encontrado: {arquivo_sped}")

  contagem_registros: Counter = Counter()
  total_linhas = 0

  with caminho.open("r", encoding="latin-1") as file:
    for linha in file:
      linha = linha.strip()
      if not linha:
        continue
      total_linhas += 1
      if linha.startswith("|"):
        partes = linha.split("|")
        if len(partes) > 2 and partes[1]:
          contagem_registros[partes[1]] += 1

  return contagem_registros, total_linhas