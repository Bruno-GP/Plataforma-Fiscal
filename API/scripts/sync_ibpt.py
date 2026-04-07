from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BASE_DIR / "app"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(APP_DIR / ".env")

from app.services.NCM.ibpt_sync_service import IBPTSyncService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza dados do IBPT para o banco da Plataforma Fiscal.",
    )
    parser.add_argument(
        "--uf",
        default="SC",
        help="UF para sincronizacao quando --todas-ufs nao for informado.",
    )
    parser.add_argument(
        "--todas-ufs",
        action="store_true",
        help="Sincroniza todas as UFs.",
    )
    parser.add_argument(
        "--ncm",
        help="Sincroniza apenas um NCM especifico.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    resultados = IBPTSyncService().sincronizar(
        uf=args.uf,
        todas_ufs=args.todas_ufs,
        ncm=args.ncm,
    )

    logging.info(
        "Sincronizacao IBPT concluida. UFs=%s registros=%s",
        len(resultados),
        sum(item.registros_recebidos for item in resultados),
    )

    for item in resultados:
        logging.info(
            "UF=%s registros=%s catalogo=%s tributacao=%s",
            item.uf,
            item.registros_recebidos,
            item.catalogo_sincronizado,
            item.tributacao_sincronizada,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
