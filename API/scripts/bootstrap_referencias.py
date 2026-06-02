from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BASE_DIR / "app"
INSERT_DIR = BASE_DIR / "SQL" / "Insert"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(APP_DIR / ".env")

from app.services.nfe.postres_config import carregar_config_postgres, opcoes_conexao_postgres


DEFAULT_SEEDS = (
    "cfops_insert.sql",
    "municipios_catalogo_insert.sql",
    "ncm_catalogo_insert.sql",
)

logger = logging.getLogger("bootstrap_referencias")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carrega dados de referencia idempotentes da Plataforma Fiscal.",
    )
    parser.add_argument(
        "--arquivo",
        action="append",
        choices=DEFAULT_SEEDS,
        help="Executa apenas um arquivo de seed. Pode ser informado mais de uma vez.",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista os arquivos de seed conhecidos e encerra.",
    )
    return parser.parse_args()


def _connect() -> psycopg.Connection:
    config = carregar_config_postgres()
    last_error: Exception | None = None

    for options in opcoes_conexao_postgres(config):
        try:
            conn = psycopg.connect(**options)
            conn.autocommit = True
            return conn
        except psycopg.Error as exc:
            last_error = exc

    raise RuntimeError(f"Nao foi possivel conectar ao PostgreSQL: {last_error}") from last_error


def _executar_seed(conn: psycopg.Connection, filename: str) -> None:
    path = INSERT_DIR / filename
    sql = path.read_text(encoding="utf-8-sig")
    if filename == "cfops_insert.sql" and "ON CONFLICT (codigo)" not in sql:
        sql = sql.replace(
            ";\n\nCOMMIT;",
            "\nON CONFLICT (codigo) DO UPDATE\n"
            "SET descricao = EXCLUDED.descricao;\n\n"
            "COMMIT;",
            1,
        )

    logger.info("Aplicando seed %s", path.relative_to(BASE_DIR))
    with conn.cursor() as cur:
        cur.execute(sql)
    logger.info("Seed %s aplicado com sucesso", filename)


def main() -> int:
    args = parse_args()
    seeds = tuple(args.arquivo or DEFAULT_SEEDS)

    if args.listar:
        for seed in DEFAULT_SEEDS:
            print(seed)
        return 0

    missing = [seed for seed in seeds if not (INSERT_DIR / seed).is_file()]
    if missing:
        raise FileNotFoundError(f"Arquivo(s) de seed nao encontrado(s): {', '.join(missing)}")

    with _connect() as conn:
        for seed in seeds:
            _executar_seed(conn, seed)

    logger.info("Bootstrap de referencias concluido. Seeds=%s", len(seeds))
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    raise SystemExit(main())
