import re


def _normalizar_espacos(valor: str | None) -> str:
    return " ".join((valor or "").strip().split())


def normalizar_nome_cliente(nome: str | None) -> str:
    valor = _normalizar_espacos(nome)
    if not valor:
        return ""

    valor = re.sub(r"^\d+\s*/\s*", "", valor)
    valor = valor.replace("/", " ")
    return _normalizar_espacos(valor)


def normalizar_descricao_produto(descricao: str | None) -> str:
    valor = _normalizar_espacos(descricao)
    if not valor:
        return ""

    valor = re.sub(r"\s*\(\s*[-N]\s*\)\s*", " ", valor, flags=re.IGNORECASE)
    valor = valor.replace("**", " ")
    valor = re.sub(r"\s-\s.*$", "", valor)
    return _normalizar_espacos(valor).strip(" -")
