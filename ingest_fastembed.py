import json
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models

# ================= CONFIGURACIÓN =================
INPUT_FILE = "chunks_demo.json"
COLLECTION_NAME = "rag_metadata_demo"
QDRANT_URL = "http://localhost:6333"

# Modelo y Nombre del Vector (Para que coincida con MCP)
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_NAME = "fast-paraphrase-multilingual-minilm-l12-v2"

print(f"📥 Cargando modelo: {MODEL_NAME}...")
embedding_model = TextEmbedding(model_name=MODEL_NAME) 
client = QdrantClient(url=QDRANT_URL)

def main():
    print(f"📖 Leyendo archivo: {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print("❌ Error: No encuentro el archivo de chunks.")
        return

    total_chunks = len(chunks)
    
    # 1. Preparar Colección
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            VECTOR_NAME: models.VectorParams(
                size=384,
                distance=models.Distance.COSINE
            )
        }
    )
    print(f"✅ Colección reiniciada para corrección de payload.")

    # 2. Vectorizar
    textos_todos = [c["texto"] for c in chunks]
    print(f"🚀 Vectorizando {total_chunks} items...")
    
    generador_vectores = embedding_model.embed(textos_todos)
    lista_vectores = list(generador_vectores)

    # 3. Subir con el campo 'document' OBLIGATORIO
    BATCH_SIZE = 20
    for i in range(0, total_chunks, BATCH_SIZE):
        fin = min(i + BATCH_SIZE, total_chunks)
        batch_chunks = chunks[i : fin]
        batch_vectores = lista_vectores[i : fin]
        
        points = []
        for idx, vec in enumerate(batch_vectores):
            # Recuperamos el payload original
            payload_actual = batch_chunks[idx]["payload"]
            
            # --- LA CORRECCIÓN MÁGICA ---
            # Agregamos el campo "document" que exige el MCP
            payload_actual["document"] = batch_chunks[idx]["texto"]
            # ----------------------------

            points.append(models.PointStruct(
                id=i + idx,
                vector={VECTOR_NAME: vec.tolist()},
                payload=payload_actual 
            ))
            
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"💾 Subido bloque {i}-{fin}...")

    print("\n🎉 ¡Ingesta Final! El campo 'document' ha sido agregado.")

if __name__ == "__main__":
    main()