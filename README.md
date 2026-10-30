# RAG ISTAE Resources

Administra los recursos persistentes compartidos. Git versiona solo esta administracion; `storage/` contiene modelos, corpus, salidas y Qdrant y esta excluido.

## Preparacion

1. Cree un entorno Python y, solo para descargas, instale `huggingface_hub`.
2. Copie `config/resources.example.json` como `config/resources.local.json` y establezca una ruta absoluta para `storage_root`.
3. Cree dentro de esa ruta `models/`, `corpus/`, `outputs/` y `vector_store/qdrant/`, o traslade una instalacion existente verificada.
4. Ejecute `python scripts/validate_resources.py` y `python scripts/validate_models.py`.

En la instalacion actual, el almacenamiento unico es `storage/` dentro de este repositorio. Los repositorios de codigo deben usar la misma ruta mediante sus configuraciones locales y nunca rutas relativas entre repositorios.

## Modelos

El manifiesto documenta los modelos y consumidores. Para una instalacion vacia, descargue explicitamente los modelos Hugging Face:

```powershell
python .\scripts\download_models.py multilingual-e5-base
python .\scripts\download_models.py bge-reranker-v2-m3
```

No hay descarga implicita desde Ingestion ni Query. Las revisiones de las copias heredadas no son verificables: deben fijarse en `manifests/models.json` despues de una descarga controlada. Los directorios Docling detectados son artefactos del runtime `docling==2.144.0`; su fuente/revision exacta no puede deducirse de forma fiable y no se descarga mediante este script.

## Operacion y respaldo

Antes de mover o respaldar `vector_store/qdrant`, cierre todo proceso que lo use. No modifique, reconstruya ni copie parcialmente una coleccion activa. Respalde `storage/` como una unidad consistente. Para trabajar offline, valide previamente los modelos y configure Ingestion/Query con rutas absolutas al almacenamiento ya disponible.
