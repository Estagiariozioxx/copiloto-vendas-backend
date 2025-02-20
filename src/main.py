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

# Função para gerar dinamicamente uma consulta SQL baseada na pergunta do usuário,
# utilizando a estrutura da tabela 'inseminacao'.
def generate_sql_query(user_query: str) -> str:
    prompt = f"""
You are an expert SQL developer. Below is the structure of the table 'inseminacao':

- id: Primary key, auto-increment.
- fazenda: Name of the farm. (e.g., "Fazenda Santa Luzia")
- estado: Brazilian state. (e.g., "BA")
- municipio: Municipality. (e.g., "Salvador")
- numero_animal: Animal identification number. (e.g., "300001")
- lote: Identifier of the animal's lot. (e.g., "LT0701SN")
- raca: Breed of the animal. (e.g., "Angus")
- categoria: Classification of the cow (e.g., "Primípara", "Multípara", etc.)
- ecc: Numeric value (e.g., 2.1)
- ciclicidade: Cycle indicator (0 or 1).
- protocolo: Protocol used (e.g., "7 dias")
- implante_p4: Product used as progestagen implant (e.g., "CIDR")
- empresa: Company of the implant (e.g., "Bayer")
- grhh_na_ia: GnRH usage during insemination (0 or 1).
- pgf_no_do: PGF usage indicator on day 0 (0 or 1).
- dose_pgf_retirada: PGF dose when implant is removed (e.g., "1")
- marca_pgf_retirada: Brand of PGF (e.g., "Lutalise")
- dose_ce: Dose of ce (e.g., "0.5 mg")
- ecg: Name of the eCG product (e.g., "Folligon")
- dose_ecg: eCG dosage (e.g., "300 UI")
- touro: Bull identifier (e.g., "Touro5001")
- raca_touro: Bull breed (e.g., "Nelore")
- empresa_touro: Bull semen supplier (e.g., "Genex")
- inseminador: Name of the inseminator (e.g., "Joana Mendes")
- numero_iatf: IATF number (e.g., "IATF 4001")
- dg: Gestation confirmation indicator (0 or 1).
- vazia_com_ou_sem_cl: Indicator if the cow is empty with/without corpus luteum (0 or 1).
- perda: Gestation loss indicator (0 or 1).

Based on the user's question: "{user_query}", generate a valid SQL SELECT query that retrieves the most relevant records from the table "inseminacao". Return only the SQL query without any additional explanation.
"""
    llm_for_sql = ChatOpenAI(temperature=0.0, model_name="gpt-3.5-turbo")
    messages = [SystemMessage(content=prompt)]
    sql_response = llm_for_sql(messages)
    return sql_response.content.strip()

# Função para executar a consulta SQL gerada e formatar os resultados
def execute_sql_query(sql_query: str) -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        results = ""
        for row in rows:
            results += (
                f"Fazenda: {row.get('fazenda', 'N/A')}, Município: {row.get('municipio', 'N/A')}, "
                f"Raça: {row.get('raca', 'N/A')}, Categoria: {row.get('categoria', 'N/A')}, "
                f"Protocolo: {row.get('protocolo', 'N/A')}\n"
            )
        return results if results else "Nenhum registro encontrado."
    except Exception as e:
        print("Erro na execução do SQL gerado:", e)
        return "Erro ao recuperar dados com o SQL gerado."

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

    # 3. Gera a consulta SQL dinamicamente com base na pergunta do usuário
    try:
        generated_sql = generate_sql_query(user_message)
        print("SQL gerado:", generated_sql)
        relevant_data = execute_sql_query(generated_sql)
    except Exception as e:
        print("Erro na geração/execução do SQL:", e)
        relevant_data = "Erro ao recuperar dados com o SQL gerado."

    # 4. Cria o contexto do sistema, injetando os dados recuperados e a explicação da estrutura da tabela
    table_explanation = (
        "A tabela 'inseminacao' está estruturada com as seguintes colunas:\n"
        "- id: Chave primária autoincrementável.\n"
        "- fazenda: Nome da fazenda (ex.: 'Fazenda Santa Luzia').\n"
        "- estado: Estado (ex.: 'BA').\n"
        "- municipio: Município (ex.: 'Salvador').\n"
        "- numero_animal: Número do animal (ex.: '300001').\n"
        "- lote: Identificação do lote (ex.: 'LT0701SN').\n"
        "- raca: Raça do animal (ex.: 'Angus').\n"
        "- categoria: Classificação da vaca (ex.: 'Primípara').\n"
        "- ecc: Espessura do coxim de carne (ex.: 2.1).\n"
        "- ciclicidade: 0 ou 1 indicando se a vaca está cíclica.\n"
        "- protocolo: Protocolo de sincronização (ex.: '7 dias').\n"
        "- implante_p4: Produto do implante (ex.: 'CIDR').\n"
        "- empresa: Empresa do implante (ex.: 'Bayer').\n"
        "- grhh_na_ia: Uso de GnRH na IA (0 ou 1).\n"
        "- pgf_no_do: Uso de PGF no dia 0 (0 ou 1).\n"
        "- dose_pgf_retirada: Dose de PGF (ex.: '1').\n"
        "- marca_pgf_retirada: Marca do PGF (ex.: 'Lutalise').\n"
        "- dose_ce: Dose de CE (ex.: '0.5 mg').\n"
        "- ecg: Produto de eCG (ex.: 'Folligon').\n"
        "- dose_ecg: Dosagem de eCG (ex.: '300 UI').\n"
        "- touro: Identificação do touro (ex.: 'Touro5001').\n"
        "- raca_touro: Raça do touro (ex.: 'Nelore').\n"
        "- empresa_touro: Empresa fornecedora do sêmen (ex.: 'Genex').\n"
        "- inseminador: Nome do inseminador (ex.: 'Joana Mendes').\n"
        "- numero_iatf: Número da IATF (ex.: 'IATF 4001').\n"
        "- dg: Indica confirmação de gestação (0 ou 1).\n"
        "- vazia_com_ou_sem_cl: Estado pós-inseminação (0 ou 1).\n"
        "- perda: Indicação de perda de gestação (0 ou 1).\n"
    )

    system_content = (
        "Você é um assistente de vendas de inseminação de gado. "
        "Responda apenas perguntas relacionadas aos dados presentes no banco de dados. "
        "Utilize os dados a seguir, se relevantes, para fundamentar suas respostas.\n\n"
        f"{table_explanation}\n"
        "Dados recuperados com base na consulta SQL gerada:\n"
        f"{relevant_data}"
    )

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

    # 6. Chama o modelo via LangChain para gerar a resposta final
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
