from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = ("models", "corpus", "outputs", "vector_store/qdrant")


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida la estructura de recursos compartidos.")
    parser.add_argument("--config", type=Path, default=Path("config/resources.local.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    root = Path(config["storage_root"])
    missing = [item for item in REQUIRED if not (root / item).exists()]
    if missing:
        raise SystemExit(f"Recursos ausentes: {', '.join(missing)}")
    print(f"Recursos disponibles en: {root}")


if __name__ == "__main__":
    main()
