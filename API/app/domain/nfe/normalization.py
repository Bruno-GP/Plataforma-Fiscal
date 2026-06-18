import re


def _normalizar_espacos(valor: str | None) -> str:
    return " ".join((valor or "").strip().split())


def _remover_blocos_hash_xprod(descricao: str) -> str:
    valor = _normalizar_espacos(descricao)
    if not valor:
        return ""

    valor = re.sub(r"^(?:#[^#\s]+)+#", "", valor)
    return _normalizar_espacos(valor)


def _eh_codigo_inicial_produto(token: str) -> bool:
    valor = (token or "").strip().upper()
    if not valor:
        return False

    if re.fullmatch(r"G\d+(?:/\d+)?", valor):
        return True

    if re.fullmatch(r"\d{2,8}", valor):
        return True

    if re.fullmatch(r"\d{2,8}/[A-Z0-9]+", valor):
        return True

    return False


def normalizar_nome_produto(descricao: str | None) -> str:
    valor = _normalizar_espacos(descricao)
    if not valor:
        return ""

    valor_original = valor
    valor = _remover_blocos_hash_xprod(valor)

    tokens = valor.split(" ")
    indice = 0

    while indice < len(tokens) and _eh_codigo_inicial_produto(tokens[indice]):
        indice += 1

    if indice > 0 and indice < len(tokens):
        valor = " ".join(tokens[indice:])

    valor = re.sub(r"\s*\(\s*[-N]\s*\)\s*", " ", valor, flags=re.IGNORECASE)
    valor = valor.replace("**", " ")
    valor = re.sub(r"\s-\s.*$", "", valor)
    valor = _normalizar_espacos(valor).strip(" -")

    if not valor:
        return valor_original

    return valor


def normalizar_descricao_produto(descricao: str | None) -> str:
    return normalizar_nome_produto(descricao)


def normalizar_nome_cliente(nome: str | None) -> str:
    valor = _normalizar_espacos(nome)
    if not valor:
        return ""

    valor = re.sub(r"^\d+\s*/\s*", "", valor)
    valor = valor.replace("/", " ")
    return _normalizar_espacos(valor)


def _remover_prefixos_tecnicos_xprod(descricao: str) -> str:
    # Compatibilidade interna para chamadas antigas enquanto a centralizacao
    # migra para normalizar_nome_produto.
    return normalizar_nome_produto(descricao)
