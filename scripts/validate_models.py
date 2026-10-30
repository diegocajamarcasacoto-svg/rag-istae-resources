from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida archivos esenciales de los modelos.")
    parser.add_argument("--config", type=Path, default=Path("config/resources.local.json"))
    parser.add_argument("--manifest", type=Path, default=Path("manifests/models.json"))
    args = parser.parse_args()
    root = Path(json.loads(args.config.read_text(encoding="utf-8"))["storage_root"])
    models = json.loads(args.manifest.read_text(encoding="utf-8"))["models"]
    for model in models:
        location = root / model["destination"]
        absent = [name for name in model["integrity_files"] if not any(location.rglob(name))]
        if absent:
            raise SystemExit(f"{model['logical_name']}: faltan {', '.join(absent)}")
        print(f"{model['logical_name']}: disponible en {location}")
        for weight in location.rglob("*.safetensors"):
            print(f"  sha256 {weight.name}: {digest(weight)}")


if __name__ == "__main__":
    main()
