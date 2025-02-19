# src/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from src.database import get_db_connection, create_tables
from src.ingest_data import insert_into_mysql

# Importações do LangChain
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# Carrega as variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  # LangChain utiliza essa variável

print("teste")
print("teste = " + OPENAI_API_KEY)

app = FastAPI()

# Configuração do CORS
origins = [
    "http://localhost:3000",  # Frontend rodando nessa porta
    "http://127.0.0.1:3000",
    "*"  # Para testes; em produção, especifique as origens permitidas
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Função para recuperar dados relevantes da tabela 'inseminacao'
def retrieve_relevant_data(query: str) -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        like_query = f"%{query}%"
        cursor.execute(
            """
            SELECT fazenda, municipio, raca, categoria, protocolo 
            FROM inseminacao 
            WHERE fazenda LIKE %s OR municipio LIKE %s OR raca LIKE %s OR categoria LIKE %s OR protocolo LIKE %s
            LIMIT 3
            """,
            (like_query, like_query, like_query, like_query, like_query)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        context = ""
        for row in rows:
            context += (
                f"Fazenda: {row['fazenda']}, Município: {row['municipio']}, "
                f"Raça: {row['raca']}, Categoria: {row['categoria']}, Protocolo: {row['protocolo']}\n"
            )
        return context
    except Exception as e:
        print("Erro na recuperação de dados relevantes:", e)
        return ""

# Evento de startup para criar as tabelas e inserir os dados do CSV (se necessário)
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
    chat_id: str  # Cada chat deve ter um ID único para preservar seu histórico

@app.get("/")
async def root():
    return {"message": "Copiloto de Vendas Backend Ativo!"}

@app.post("/chat")
async def chat_endpoint(chat_request: ChatRequest):
    chat_id = chat_request.chat_id
    user_message = chat_request.message

    # 1. Salva a mensagem do usuário no banco de dados
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO historico_chat (chat_id, mensagem, remetente) VALUES (%s, %s, %s)",
            (chat_id, user_message, "user")
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao salvar mensagem do usuário.")

    # 2. Recupera o histórico do chat para montar o contexto
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT mensagem, remetente FROM historico_chat WHERE chat_id = %s ORDER BY timestamp ASC",
            (chat_id,)
        )
        history = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao recuperar histórico do chat.")

    # 3. Recupera dados relevantes da tabela 'inseminacao' com base na mensagem do usuário
    relevant_data = retrieve_relevant_data(user_message)

    # 4. Constrói o contexto do sistema injetando os dados do banco
    system_content = (
        "Você é um assistente de vendas de inseminação de gado. "
        "Responda apenas perguntas relacionadas aos dados presentes no banco de dados. "
        "Utilize os seguintes dados, se relevantes, para fundamentar suas respostas:\n"
    )
    if relevant_data:
        system_content += relevant_data
    else:
        system_content += "Nenhum dado relevante encontrado."

    # 5. Constrói a conversa usando os tipos de mensagem do LangChain
    messages_chain = []
    messages_chain.append(SystemMessage(content=system_content))
    for entry in history:
        if entry["remetente"] == "user":
            messages_chain.append(HumanMessage(content=entry["mensagem"]))
        elif entry["remetente"] == "bot":
            messages_chain.append(AIMessage(content=entry["mensagem"]))
    # Garante que a última mensagem do usuário esteja presente
    messages_chain.append(HumanMessage(content=user_message))

    # 6. Chama o modelo via LangChain
    try:
        llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")
        response = llm(messages_chain)
        bot_reply = response.content.strip()
    except Exception as e:
        print("Erro na chamada do LangChain:", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta via LangChain: {str(e)}")

    # 7. Salva a resposta do bot no banco de dados
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO historico_chat (chat_id, mensagem, remetente) VALUES (%s, %s, %s)",
            (chat_id, bot_reply, "bot")
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao salvar mensagem do bot.")

    # Retorna a resposta para o frontend
    return {"response": bot_reply}
