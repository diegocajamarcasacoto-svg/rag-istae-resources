"""Arma el paquete de datos para levantar rag-istae-query en otra máquina.

Copia desde ``storage/`` **solo lo que necesita la consulta** y genera un
manifiesto con el sha256 de cada archivo. No modifica nada en ``storage/``.

Incluye:
- ``models/multilingual-e5-base/`` (embeddings de consulta);
- ``models/bge-reranker-base/`` sin ``onnx/`` ni ``pytorch_model.bin`` (copias
  del mismo modelo en otro formato; se usa ``model.safetensors``);
- ``vector_store/qdrant/`` (colección ``istae_chunks_e5_base``, sin ``.lock``);
- ``outputs/units.jsonl`` (índice chunk → artículo);
- ``catalog/catalogo_normativo.json`` (rangos y relaciones entre normas).

No incluye el corpus, el Gold Standard, ``bge-reranker-v2-m3`` ni los modelos de Docling.

Uso (con cualquier Python 3.11; solo usa la biblioteca estándar):

    python .\\scripts\\build_data_bundle.py --out D:\\paquetes [--storage <ruta a storage>] [--zip]

Resultado: ``<out>/storage/`` con ``MANIFEST.json`` y ``LEEME.txt`` y, con
``--zip``, ``<out>/rag-istae-storage-<version>.zip`` (carpeta raíz ``storage/``).
Qdrant local es de un solo proceso: detenga el servicio y los scripts de
consulta antes de armar el paquete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "resources.local.json"
COLLECTION = "istae_chunks_e5_base"
BUNDLE_VERSION = "LB1"

# (ruta relativa en storage, nombres excluidos en cualquier nivel)
ITEMS: list[tuple[str, set[str]]] = [
    ("models/multilingual-e5-base", {".cache", ".gitattributes"}),
    ("models/bge-reranker-base", {".cache", ".gitattributes", "onnx", "pytorch_model.bin"}),
    ("vector_store/qdrant", {".lock"}),
    ("outputs/units.jsonl", set()),
    ("catalog/catalogo_normativo.json", set()),
]
CHUNK = 1 << 20

LEEME = """Paquete de datos de rag-istae-query (versión {version}, {created})

Contenido: modelos E5 y bge-reranker-base, índice Qdrant ({collection}),
units.jsonl y catalogo_normativo.json. MANIFEST.json lista el sha256 de cada archivo.

Descomprima de modo que exista C:\\RAG-ISTAE\\storage\\ (o la ruta que indique en
config\\local.json) y siga docs\\guia_ambiente_local.md del repositorio rag-istae-query.

Valores esperados (deben coincidir con GET /health del servicio, campo index_version):
  units_sha256   = {units_sha256}
  catalog_sha256 = {catalog_sha256}
"""


def storage_from_config(path: Path) -> Path:
    if not path.is_file():
        raise SystemExit(f"Indique --storage o cree {path} (copie config/resources.example.json).")
    return Path(json.loads(path.read_text(encoding="utf-8"))["storage_root"])


def ensure_qdrant_free(qdrant_dir: Path) -> None:
    """Falla si otro proceso tiene abierta la colección (servicio o script de consulta)."""
    lock = qdrant_dir / ".lock"
    if not lock.exists():
        return
    with lock.open("a+b") as handle:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            raise SystemExit(
                "Qdrant está en uso por otro proceso. Detenga el servicio /retrieve y los scripts de consulta."
            ) from None


def files_to_copy(storage: Path) -> list[Path]:
    selected: list[Path] = []
    for relative, excluded in ITEMS:
        source = storage / relative
        if not source.exists():
            raise SystemExit(f"Falta en storage: {relative}")
        if source.is_file():
            selected.append(source)
            continue
        for path in sorted(source.rglob("*")):
            parts = path.relative_to(source).parts
            if path.is_file() and not any(part in excluded for part in parts):
                selected.append(path)
    return selected


def copy_with_hash(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as reader, target.open("wb") as writer:
        for block in iter(lambda: reader.read(CHUNK), b""):
            digest.update(block)
            writer.write(block)
    shutil.copystat(source, target)
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Arma el paquete de datos de rag-istae-query.")
    parser.add_argument("--out", type=Path, required=True, help="Carpeta de salida (se crea <out>/storage).")
    parser.add_argument("--storage", type=Path, help="storage/ de origen (por defecto, el de resources.local.json).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--version", default=BUNDLE_VERSION, help="Etiqueta del paquete (por defecto LB1).")
    parser.add_argument("--zip", action="store_true", help="Además, crea rag-istae-storage-<version>.zip.")
    parser.add_argument("--force", action="store_true", help="Reemplaza <out>/storage si ya existe.")
    args = parser.parse_args()

    storage = (args.storage or storage_from_config(args.config)).resolve()
    out_storage = (args.out / "storage").resolve()
    if out_storage == storage or storage in out_storage.parents:
        raise SystemExit("La salida no puede estar dentro de storage/.")
    if out_storage.exists():
        if not args.force:
            raise SystemExit(f"{out_storage} ya existe; use --force para reemplazarlo.")
        shutil.rmtree(out_storage)
    ensure_qdrant_free(storage / "vector_store" / "qdrant")

    files = files_to_copy(storage)
    total = sum(path.stat().st_size for path in files)
    print(f"Copiando {len(files)} archivos ({total / 1e9:.2f} GB) a {out_storage}")
    manifest_files = []
    copied = 0
    for path in files:
        relative = path.relative_to(storage).as_posix()
        sha = copy_with_hash(path, out_storage / relative)
        copied += path.stat().st_size
        manifest_files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha})
        if path.stat().st_size > 50_000_000:
            print(f"  {relative} ({path.stat().st_size / 1e9:.2f} GB) · {copied / total:.0%}")

    # Verificación: el archivo copiado debe tener el mismo sha256 que el origen.
    for entry in manifest_files:
        if file_sha256(out_storage / entry["path"]) != entry["sha256"]:
            raise SystemExit(f"La copia de {entry['path']} no coincide con el origen.")

    by_path = {entry["path"]: entry["sha256"] for entry in manifest_files}
    created = datetime.now().isoformat(timespec="seconds")
    manifest = {
        "bundle": "rag-istae-storage",
        "version": args.version,
        "created": created,
        "collection": COLLECTION,
        "index_version": {
            "collection": COLLECTION,
            "units_sha256": by_path["outputs/units.jsonl"],
            "catalog_sha256": by_path["catalog/catalogo_normativo.json"],
        },
        "total_bytes": total,
        "files": manifest_files,
    }
    (out_storage / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_storage / "LEEME.txt").write_text(
        LEEME.format(version=args.version, created=created, collection=COLLECTION,
                     units_sha256=manifest["index_version"]["units_sha256"],
                     catalog_sha256=manifest["index_version"]["catalog_sha256"]),
        encoding="utf-8",
    )
    print(f"Manifiesto: {out_storage / 'MANIFEST.json'}")
    print(f"units_sha256   = {manifest['index_version']['units_sha256']}")
    print(f"catalog_sha256 = {manifest['index_version']['catalog_sha256']}")

    if args.zip:
        zip_path = args.out.resolve() / f"rag-istae-storage-{args.version}.zip"
        print(f"Comprimiendo en {zip_path} …")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1,
                             allowZip64=True) as archive:
            for path in sorted(out_storage.rglob("*")):
                if path.is_file():
                    archive.write(path, Path("storage") / path.relative_to(out_storage))
        print(f"Zip: {zip_path} ({zip_path.stat().st_size / 1e9:.2f} GB)")


if __name__ == "__main__":
    sys.exit(main())
