"""Exportador JSON. Ponto de extensao: plugue aqui o exporter da plataforma
fiscal final implementando a mesma interface (`export(data, output_dir)`).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class JsonExporter:
    def export(self, data: dict[str, list[BaseModel]], output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for resource_name, items in data.items():
            path = output_dir / f"{resource_name}.json"
            payload = [item.model_dump(mode="json") for item in items]
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def export_consolidado(self, data: dict[str, list[BaseModel]], output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            resource_name: [item.model_dump(mode="json") for item in items]
            for resource_name, items in data.items()
        }
        (output_dir / "consolidado.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
