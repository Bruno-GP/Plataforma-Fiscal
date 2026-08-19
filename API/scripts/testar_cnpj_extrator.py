from __future__ import annotations

import argparse
import json
import re
import sys

import httpx

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def normalizar_cnpj(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Testa extracao de CNPJ + CNAE via BrasilAPI.",
    )
    parser.add_argument("cnpj", help="CNPJ da empresa (com ou sem mascara)")
    return parser.parse_args()


def consultar(cnpj: str) -> dict:
    resposta = httpx.get(BRASILAPI_URL.format(cnpj=cnpj), timeout=10.0)
    resposta.raise_for_status()
    return resposta.json()


def main() -> None:
    args = parse_args()
    cnpj = normalizar_cnpj(args.cnpj)

    if len(cnpj) != 14:
        print(f"CNPJ invalido: {args.cnpj}", file=sys.stderr)
        sys.exit(1)

    try:
        resultado = consultar(cnpj)
    except httpx.HTTPStatusError as erro:
        print(f"Falha na consulta: HTTP {erro.response.status_code}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as erro:
        print(f"Falha na consulta: {erro}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
