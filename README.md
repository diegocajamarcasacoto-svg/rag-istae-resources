# RAG ISTAE Resources

Administra los recursos persistentes compartidos por `rag_istae_ingestion` y `rag-istae-query` (`rag-istae-api` no los usa; ver más abajo). Git versiona solo esta administración (configuración, manifiesto y scripts); `storage/` contiene modelos, corpus, salidas y Qdrant y está excluido.

## Estructura de `storage/`

```text
storage/
├── models/
│   ├── multilingual-e5-base/     # embeddings (ingestión y consulta)
│   ├── bge-reranker-base/        # reranker en uso por rag-istae-query
│   ├── bge-reranker-v2-m3/       # reranker anterior, conservado localmente
│   └── docling/                  # artefactos del runtime Docling (ingestión)
├── corpus/
│   ├── EXTERNOS/                 # 13 documentos EXT01–EXT13 (PDF)
│   ├── INTERNOS/                 # 33 documentos INT01–INT33 (DOCX y PDF)
│   ├── GOLD STANDARD/            # batería de preguntas y acta de validación para la evaluación
│   └── Matriz_Reglamentos_TESIS_ISTAE_v5.xlsx
├── outputs/                      # salidas de rag_istae_ingestion (chunks.jsonl, inventario, manifiesto, texto extraído)
└── vector_store/qdrant/          # persistencia Qdrant local, colección istae_chunks_e5_base
```

El prefijo `EXT##` / `INT##` del nombre de cada documento se usa como `document_id` durante la ingestión; no renombre los archivos del corpus sin reindexar.

`GOLD STANDARD` no forma parte del corpus consultable; `rag_istae_ingestion` la excluye mediante `exclude_directory_names`.

**`rag-istae-api` no consume `storage/`.** Este backend FastAPI del chat es un repositorio externo y, para este proyecto, de solo lectura. Usa su propia copia en `data/`:
- `document_mapping.jsonl` y `extracted_text/`, iguales a los de `storage/outputs`;
- `catalogo_normativo.json`, generado desde `corpus/Matriz_Reglamentos_TESIS_ISTAE_v5.xlsx`.

Si cambian el corpus, la matriz o las salidas de ingestión, esa copia debe regenerarse en ese repositorio. No es necesario mover ni respaldar nada de `storage/` para la API.

`rag-istae-web` (frontend Next.js del chat, externo y de solo lectura) tampoco usa `storage/`: solo se comunica con `rag-istae-api`.

## Preparación

1. Cree un entorno Python y, solo para descargas, instale `huggingface_hub`.
2. Copie `config/resources.example.json` como `config/resources.local.json` y establezca una ruta absoluta para `storage_root`.
3. Cree dentro de esa ruta `models/`, `corpus/`, `outputs/` y `vector_store/qdrant/`, o traslade una instalación existente verificada.
4. Ejecute las validaciones:

```powershell
python .\scripts\validate_resources.py   # comprueba que existan models, corpus, outputs y vector_store/qdrant
python .\scripts\validate_models.py      # comprueba los archivos de integridad del manifiesto e imprime el SHA-256 de cada .safetensors
```

En la instalación actual, el almacenamiento único es `storage/` dentro de este repositorio. Los repositorios de código deben usar la misma ruta mediante sus configuraciones locales (`config/config.json` y `config/rag_config.json` en ingestión, `config/local.json` en consulta) y nunca rutas relativas entre repositorios.

## Modelos

`manifests/models.json` documenta los modelos, su origen y sus consumidores:

| Nombre lógico | Repositorio Hugging Face | Consumidores |
|---|---|---|
| `multilingual-e5-base` | `intfloat/multilingual-e5-base` | ingestión, consulta |
| `bge-reranker-base` | `BAAI/bge-reranker-base` | consulta |
| `bge-reranker-v2-m3` | `BAAI/bge-reranker-v2-m3` | ninguno (reranker anterior, conservado para evaluaciones comparativas) |
| `docling-runtime-models` | — (runtime `docling==2.144.0`) | ingestión |

Para una instalación vacía, descargue explícitamente los modelos Hugging Face:

```powershell
python .\scripts\download_models.py multilingual-e5-base
python .\scripts\download_models.py bge-reranker-base
```

`download_models.py` acepta también `bge-reranker-v2-m3`. El script se detiene si el destino ya contiene archivos. `validate_models.py` valida todos los modelos del manifiesto, incluido `bge-reranker-v2-m3`.

No hay descarga implícita desde Ingestion ni Query. Las revisiones de las copias heredadas no son verificables: deben fijarse en `manifests/models.json` después de una descarga controlada. Los directorios Docling detectados (`docling-layout-heron`, `docling-layout-heron-onnx`, `docling-models`, `RapidOcr`) son artefactos del runtime `docling==2.144.0`; su fuente/revisión exacta no puede deducirse de forma fiable y no se descargan mediante este script.

## Operación y respaldo

Qdrant local solo admite un proceso a la vez sobre la misma persistencia. Antes de mover o respaldar `vector_store/qdrant`, cierre todo proceso que lo use. No modifique, reconstruya ni copie parcialmente una colección activa. Respalde `storage/` como una unidad consistente. Para trabajar offline, valide previamente los modelos y configure Ingestion/Query con rutas absolutas al almacenamiento ya disponible.
