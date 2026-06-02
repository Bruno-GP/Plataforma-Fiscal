from pathlib import Path

from alembic import command
from alembic.config import Config


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    config = Config(str(app_dir / "alembic.ini"))
    config.set_main_option("script_location", str(app_dir / "alembic"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
