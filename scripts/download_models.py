from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga explicitamente modelos Hugging Face declarados.")
    parser.add_argument("model", choices=("multilingual-e5-base", "bge-reranker-v2-m3"))
    parser.add_argument("--config", type=Path, default=Path("config/resources.local.json"))
    parser.add_argument("--manifest", type=Path, default=Path("manifests/models.json"))
    args = parser.parse_args()
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit("Instale huggingface_hub para descargar modelos: pip install huggingface_hub") from exc
    root = Path(json.loads(args.config.read_text(encoding="utf-8"))["storage_root"])
    model = next(item for item in json.loads(args.manifest.read_text(encoding="utf-8"))["models"] if item["logical_name"] == args.model)
    destination = root / model["destination"]
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"Destino ya contiene archivos: {destination}. Valide o elimine manualmente antes de descargar.")
    snapshot_download(repo_id=model["repository_id"], revision=model["revision"], local_dir=destination)


if __name__ == "__main__":
    main()
