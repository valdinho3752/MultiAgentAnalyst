import os
import pandas as pd
from sqlalchemy import text
from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from dotenv import load_dotenv, find_dotenv

# Importar configuración de base de datos local
try:
    from .database import get_engine
except ImportError:
    from database import get_engine

load_dotenv(find_dotenv())

# --- Tool Definition ---

def execute_sql_query(query: str) -> str:
    """
    Ejecuta una consulta SQL SELECT en la base de datos PostgreSQL 'rag_db' y devuelve los resultados.

    Args:
        query: La sentencia SQL SELECT válida a ejecutar.

    Returns:
        String con representación JSON (orient='records') del DataFrame resultante,
        o un mensaje de error si falla.
    """
    print(f"DEBUG: Executing SQL: {query}")
    
    # Validaciones básicas de seguridad (aunque el SQL Agent ya debe filtrar)
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]
    if any(cmd in query.upper() for cmd in forbidden):
        return "ERROR: Solo se permiten consultas SELECT (Lectura)."

    engine = get_engine()
    if not engine:
        return "ERROR: No hay conexión a la base de datos."

    try:
        # Usar pandas para leer SQL directamente a DataFrame
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        
        # Convertir a JSON string para retorno ligero
        if df.empty:
            return "RESULT: La consulta no devolvió filas."
        
        # Limitar filas por seguridad de contexto (opcional, ajustables)
        # result_json = df.head(100).to_json(orient='records', date_format='iso')
        result_json = df.to_json(orient='records', date_format='iso')
        return f"SUCCESS: {result_json}"

    except Exception as e:
        return f"ERROR executing query: {str(e)}"


# --- Agent Definition ---

root_agent = Agent(
    # model='gemini-3-flash-preview',
    model= os.getenv("LLM_MODEL_EXECUTOR"),
    name='executor_agent',
    description='Agente Ejecutor de SQL. Se conecta a PostgreSQL para recuperar datos reales.',
    instruction="""
    Eres el **Agente Ejecutor**. Tu ÚNICA responsabilidad es recibir sentencias SQL validadas, ejecutarlas contra la base de datos PostgreSQL real y devolver los datos resultantes.
    
    No analizas, no generas SQL, no discutes. Solo ejecutas y reportas.
    
    Usa la herramienta `execute_sql_query(query)` para cualquier input que parezca SQL.
    Siempre devuelve el resultado, no solo un mensaje de éxito. Si la consulta falla, devuelve el error exacto.
    """,
    tools=[FunctionTool(execute_sql_query)]
)

# Exponemos este agente en el puerto 10004
app = to_a2a(root_agent, host="executor_agent", port=10004)
