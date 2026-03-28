import asyncio
import logging
import os

import httpx
from fastmcp import FastMCP

from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed import TextEmbedding


# Configuración idéntica a tu script de ingesta
COLLECTION_NAME = "rag_metadata_demo"
# Apuntar al host desde Docker para ver el Qdrant real
QDRANT_URL = os.getenv("QDRANT_URL", "http://host.docker.internal:6333")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Inicialización
import qdrant_client as qc_module
# Usamos qdrant_client conectado al servidor real
qdrant_client = QdrantClient(url=QDRANT_URL)
# NO usamos :memory: porque estaría vacío

embedding_model = TextEmbedding(model_name=MODEL_NAME)

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

import importlib.metadata
try:
    version = importlib.metadata.version("qdrant-client")
except Exception:
    version = "unknown"

logger.info(f"🧩 Qdrant Version: {version}")
logger.info(f"🧩 Qdrant Module Attributes: {dir(qc_module)}")
logger.info(f"🧩 Qdrant Client Attributes: {dir(qdrant_client)}")

mcp = FastMCP("Currency MCP Server 💵")


@mcp.tool()
def get_table_schema(table_name: str) -> dict:
    """
    Busca en Qdrant el esquema técnico (payload) de una tabla específica.
    Usa esta herramienta cuando necesites conocer las columnas exactas (json_completo).
    """
    logger.info(f"--- 🔍 Buscando esquema para la tabla: {table_name} ---")
    
    try:
        # Generar vector para la búsqueda (debe coincidir con la ingesta)
        query_vector = list(embedding_model.embed([table_name]))[0]

        # Buscar con un filtro de nombre exacto para mayor precisión


        # Usamos el cliente global conectado al host
        # IMPORTANTE: Definir el nombre del vector coincidente con la ingesta
        VECTOR_NAME = "fast-paraphrase-multilingual-minilm-l12-v2"
        
        # Generar el vector de consulta
        query_vector = list(embedding_model.embed([table_name]))[0]

        search_result = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using=VECTOR_NAME,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="nombre_tabla",
                        match=models.MatchValue(value=table_name)
                    )
                ]
            ),
            limit=5
        ).points
        print(f"🔎 Resultados encontrados: {len(search_result)}")


        if not search_result:
            return {"error": f"No se encontró información para la tabla '{table_name}'"}

        # Retornamos el payload completo
        payload = search_result[0].payload
        logger.info(f"✅ Esquema recuperado para {table_name}")
        return payload

    except Exception as e:
        logger.error(f"❌ Error al consultar Qdrant: {e}")
        return {"error": str(e)}


@mcp.tool()
def search_relevant_tables(query: str, limit: int = 5) -> list[dict]:
    """
    Busca tablas relevantes basadas en una consulta de lenguaje natural.
    Retorna una lista de tablas con su metadata completa (payload).
    """
    logger.info(f"--- 🧠 Buscando tablas relevantes para: '{query}' ---")

    try:
        # 1. Vectorizar la consulta
        query_vector = list(embedding_model.embed([query]))[0]

        # 2. Definir nombre del vector (debe coincidir con ingesta)
        VECTOR_NAME = "fast-paraphrase-multilingual-minilm-l12-v2"

        # 3. Buscar en Qdrant usando query_points (compatible con versiones recientes)
        points = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using=VECTOR_NAME,
            limit=limit,
            with_payload=True
        ).points

        results = []
        for point in points:
            results.append({
                "score": point.score,
                "payload": point.payload
            })
            
        logger.info(f"✅ Encontradas {len(results)} tablas relevantes")
        return results

    except Exception as e:
        logger.error(f"❌ Error en búsqueda semántica: {e}")
        return [{"error": str(e)}]


if __name__ == "__main__":
    logger.info(f"🚀 MCP server started on port {os.getenv('PORT', 8080)}")
    # Could also use 'sse' transport, host="0.0.0.0" required for Cloud Run.
    asyncio.run(
        mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=os.getenv("PORT", 8080),
        )
    )
