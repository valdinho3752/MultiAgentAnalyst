import asyncio
from fastmcp import Client

async def test_server():
    # En Docker, intenta con /mcp o /sse según lo que diga el log de inicio
    url = "http://localhost:8080/mcp" 
    
    print(f"--- 🔗 Intentando conectar a Docker en {url} ---")
    # try:
    async with Client(url) as client:
        tools = await client.list_tools()
        print(f"✅ Conectado! Herramientas: {[t.name for t in tools]}")
        
        
        # Prueba la herramienta real
        # query = "dame tablas que tengan informacion sobre petroleo y gas"
        query = "Necesito datos de las exportaciones de gas natural por departamento"
        print(f"--- 🧠 Buscando tablas para: '{query}' ---")
        
        result = await client.call_tool(
            "search_relevant_tables", {"query": query, "limit": 2}
        )
        
        # El resultado es texto (string representación de la lista)
        # print(f"--- 📄 Resultado crudo: {result.content[0].text[:200]}... ---")
        
        import ast
        try:
            resultados_lista = ast.literal_eval(result.content[0].text)
            print(f"--- ✅ Encontradas {len(resultados_lista)} tablas ---")
            for i, res in enumerate(resultados_lista):
                payload = res.get("payload", {})
                print(f"[{i+1}] Score: {score:.4f}")
                print(f"    Payload: {payload}")
        except:
             print(f"--- 📄 Resultado no parseable: {result.content[0].text} ---")
    # except Exception as e:
    #     print(f"--- ❌ Error: {e} ---")

if __name__ == "__main__":
    asyncio.run(test_server())