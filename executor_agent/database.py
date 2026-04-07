from sqlalchemy import create_engine
from dotenv import load_dotenv, find_dotenv
import os

# Cargar .env desde ADK o local
load_dotenv(find_dotenv())

# Vars del servidor RAG
host = os.getenv("HOST_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")
database = os.getenv("DATABASE_DB")
port = os.getenv("PORT_DB")

# URL de conexión PostgreSQL
url_db = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

print(f"DEBUG: Connecting to DB at {host}:{port}/{database} as {user}")

# Crear Motor
engine = create_engine(url_db, pool_pre_ping=True, echo=False)
try:
    with engine.connect() as connection:
        print("DEBUG: Connection successful!")
except Exception as e:
    print(f"WARNING: Could not connect to database at startup, but engine is ready: {e}")

def get_engine():
    return engine
