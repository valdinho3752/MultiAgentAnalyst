import os
import asyncio
import httpx
import json
from uuid import uuid4
from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, SendMessageSuccessResponse, Task, Message

# --- Helper Functions for A2A Communication ---

async def helper_send_a2a_message(url: str, text: str) -> str:
    """Sends a message to an A2A agent and extracts the text response."""
    print(f"DEBUG: Connecting to agent at {url}...")
    try:
        async with httpx.AsyncClient(timeout=None) as http_client:
            resolver = A2ACardResolver(http_client, base_url=url)
            card = await resolver.get_agent_card()
            client = A2AClient(http_client, card)

            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(
                    message={
                        "role": "user",
                        "parts": [{"kind": "text", "text": text}],
                        "messageId": uuid4().hex,
                    }
                )
            )
            response = await client.send_message(request)
            
            if isinstance(response.root, SendMessageSuccessResponse):
                result = response.root.result
                if isinstance(result, Task):
                    if result.history:
                        for msg in reversed(result.history):
                            if msg.role == 'agent':
                                if msg.parts and msg.parts[0].root.kind == 'text':
                                    return msg.parts[0].root.text
                elif isinstance(result, Message):
                     if result.parts and result.parts[0].root.kind == 'text':
                        return result.parts[0].root.text
            
            return f"Error: Invalid A2A Response structure: {response}"
    except Exception as e:
        return f"Error connecting to agent: {str(e)}"

# --- Tool Definitions ---

async def ask_rag_agent(query: str) -> str:
    """
    Consulta al 'Data Scout' (RAG Agent) para verificar si existen datos relevantes en la base de datos.
    Retorna un JSON indicando si hay info ('existing_info': true/false) y qué tablas usar.
    """
    RAG_URL = "http://rag_agent:10001"
    return await helper_send_a2a_message(RAG_URL, query)

async def ask_sql_agent(user_query: str, rag_context: str) -> str:
    """
    Solicita al 'SQL Architect' (SQL Agent) que genere una consulta SQL.
    REQUIERE haber consultado al RAG Agent primero.
    
    Args:
        user_query: La pregunta original del usuario.
        rag_context: El JSON completo retornado por ask_rag_agent.
    """
    SQL_URL = "http://sql_agent:10002"
    
    # Preparamos el prompt compuesto para el SQL Agent
    full_input = f"""
    User Query: {user_query}
    
    RAG Analysis:
    {rag_context}
    """
    return await helper_send_a2a_message(SQL_URL, full_input)
async def ask_executor_agent(sql_query: str) -> str:
    """
    Solicita al 'Executor Agent' ejecutar una consulta SQL y devolver los datos como DataFrame (JSON).
    
    Args:
        sql_query: La consulta SQL generada por el SQL Agent.
    """
    EXECUTOR_URL = "http://executor_agent:10004"
    return await helper_send_a2a_message(EXECUTOR_URL, sql_query)

# --- Agent Definition ---

root_agent = Agent(
    # model='gemini-3-flash-preview',
    model= os.getenv("LLM_MODEL_ORCHESTRATOR"),
    name='orchestrator_agent',
    description='Coordinador inteligente que gestiona la búsqueda de datos, generación de SQL y ejecución.',
    instruction="""
    Eres el **Orquestador de Datos**. Tu trabajo es responder a las preguntas de negocio del usuario coordinando a tres agentes especialistas.
    
    ### TUS HERRAMIENTAS
    1. `ask_rag_agent(query)`: Úsala SIEMPRE primero para ver si tenemos datos.
    2. `ask_sql_agent(user_query, rag_context)`: Úsala SOLO SI el RAG confirma que hay datos (`existing_info: true`).
    3. `ask_executor_agent(sql_query)`: Úsala para ejecutar el SQL generado y obtener los datos reales.
    
    ### FLUJO DE PENSAMIENTO
    1. El usuario hace una pregunta (ej. "Dame la deuda 2021").
    2. ¿Es un saludo? -> Responde amablemente y espera.
    3. ¿Pide datos? -> Llama a `ask_rag_agent`.
    4. Analiza la respuesta del RAG.
       - CASO A: `existing_info: false` -> Dile al usuario: "Lo siento, verifiqué en nuestra base de datos y no tenemos información sobre [tema]".
       - CASO B: `existing_info: true` -> Llama a `ask_sql_agent` con el contexto del RAG.
    5. Analiza la respuesta del SQL Agent.
       - Si devuelve un SQL válido: Llama a `ask_executor_agent`.
    6. Con los datos del Executor (JSON), responde al usuario con la información final.
    
    NO inventes SQL ni datos. Confía en tus agentes.
    """,
    tools=[FunctionTool(ask_rag_agent), FunctionTool(ask_sql_agent), FunctionTool(ask_executor_agent)]
)

# Exponemos este agente en el puerto 10003
app = to_a2a(root_agent, port=10003)
