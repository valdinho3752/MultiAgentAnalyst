import json
import vertexai
from vertexai.language_models import TextEmbeddingModel
from qdrant_client import QdrantClient
from qdrant_client.http import models

# ================= CONFIGURACIÓN =================
INPUT_FILE = "chunks_demo2.json"
COLLECTION_NAME = "rag_metadata_demo_vertex_3"
QDRANT_URL = "http://localhost:6333"

# Configuración GCP - ASEGÚRATE DE QUE ESTO SEA CORRECTO
# PROJECT_ID = "mcp-a2a-484414"  # <-- REEMPLAZAR CON TU PROJECT ID EN GCP
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mcp-a2a-484414")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = "gemini-embedding-001"
# MODEL_NAME = "text-embedding-004"
VECTOR_NAME = "gcp-vertex-embedding" 

# Inicializar Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)
embedding_model = TextEmbeddingModel.from_pretrained(MODEL_NAME)

client = QdrantClient(url=QDRANT_URL)

def get_embeddings_gcp(texts):
    """Obtiene embeddings de Vertex AI"""
    embeddings = embedding_model.get_embeddings(texts)
    return [embedding.values for embedding in embeddings]

def main():
    print(f"📖 Leyendo archivo: {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        return

    total_chunks = len(chunks)
    
    # 1. Preparar Colección
    print(f"📡 Conectando a Qdrant en {QDRANT_URL}...")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            VECTOR_NAME: models.VectorParams(
                size=3072, 
                distance=models.Distance.COSINE
            )
        }
    )
    print(f"✅ Colección '{COLLECTION_NAME}' reiniciada.")

    # 2. Vectorizar y Subir
    textos_todos = [c["texto"] for c in chunks]
    BATCH_SIZE = 50 
    
    print(f"🚀 Procesando {total_chunks} items en lotes de {BATCH_SIZE}...")
    
    for i in range(0, total_chunks, BATCH_SIZE):
        fin = min(i + BATCH_SIZE, total_chunks)
        batch_texts = textos_todos[i:fin]
        batch_chunks = chunks[i:fin]
        
        try:
            # Llamada a Google Cloud
            batch_vectores = get_embeddings_gcp(batch_texts)
            
            points = []
            for idx, vec in enumerate(batch_vectores):
                # Extraer y preparar payload
                payload_actual = batch_chunks[idx].get("payload", {})
                payload_actual["document"] = batch_chunks[idx]["texto"]

                points.append(models.PointStruct(
                    id=i + idx,
                    vector={VECTOR_NAME: vec}, # Usando Vector con Nombre
                    payload=payload_actual 
                ))
            
            # Subir a Qdrant
            operation_info = client.upsert(
                collection_name=COLLECTION_NAME, 
                wait=True, # Esperar a que se indexe para ver resultados de inmediato
                points=points
            )
            print(f"💾 Bloque {i}-{fin} subido. Status: {operation_info.status}")

        except Exception as e:
            print(f"❌ Error en lote {i}-{fin}: {e}")

    # Verificación final
    info = client.get_collection(COLLECTION_NAME)
    print(f"\n✅ Proceso terminado. Puntos totales en Qdrant: {info.points_count}")

if __name__ == "__main__":
    main()