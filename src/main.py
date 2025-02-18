import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from src.database import get_db_connection, create_tables
from src.ingest_data import insert_into_mysql
#from langchain.llms import OpenAI

# Carrega as variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializa a LLM
#llm = OpenAI(openai_api_key=OPENAI_API_KEY, temperature=0.7)

app = FastAPI()

# Evento de startup para criar as tabelas e inserir os dados do CSV se necessário
@app.on_event("startup")
async def startup_event():
    print("Criando as tabelas (se ainda não existirem)...")
    create_tables()
    print("Verificando e inserindo dados do CSV (se a tabela estiver vazia)...")
    insert_into_mysql()
    print("Tarefas de startup concluídas.")

# Modelo de requisição para o endpoint do chat
class ChatRequest(BaseModel):
    message: str
    chat_id: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Buscar informações na base vetorizada (presumindo que a função query_vector_db esteja implementada)
        from src.vector_db import query_vector_db
        matches = query_vector_db(request.message)
        
        # Buscar informações no MySQL
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Note que 'matches' deve conter IDs compatíveis; essa query é um exemplo
        cursor.execute("SELECT * FROM inseminacao WHERE id IN (%s)" % ",".join(map(str, matches)))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        if results:
            context = "\n".join([f"{r['fazenda']} - {r['categoria']} - {r['protocolo']}" for r in results])
        else:
            context = "Nenhuma informação relevante encontrada na base."

        prompt = f"Com base no seguinte contexto:\n{context}\nResponda a esta pergunta:\n{request.message}"
        response = llm.predict(prompt)

        # Salvar no histórico do chat
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historico_chat (chat_id, mensagem, remetente) VALUES (%s, %s, %s)",
                       (request.chat_id, request.message, "user"))
        cursor.execute("INSERT INTO historico_chat (chat_id, mensagem, remetente) VALUES (%s, %s, %s)",
                       (request.chat_id, response, "bot"))
        conn.commit()
        cursor.close()
        conn.close()

        return {"response": response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Copiloto de Vendas Backend Ativo!"}
