# src/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from src.database import get_db_connection, create_tables
from src.ingest_data import insert_into_mysql, index_farm_names

# Importações do LangChain
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# Importação para a busca semântica de fazendas
from src.vector_db import search_farm

# Carrega as variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  # LangChain utiliza essa variável

print("teste")
print("teste = " + OPENAI_API_KEY)

app = FastAPI()

# Configuração do CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"  # Em produção, especifique as origens permitidas
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def adjust_user_query(user_query: str) -> str:
    """
    Se a consulta do usuário mencionar (ou tiver similaridade com) um nome de fazenda,
    ajusta a query acrescentando uma instrução para filtrar os registros por essa fazenda.
    """
    matched_farms = search_farm(user_query, top_k=1)
    if matched_farms:
        # Acrescenta ao prompt que devem ser considerados apenas registros da fazenda encontrada
        return f"{user_query}. Considere apenas registros da fazenda '{matched_farms[0]}'."
    return user_query

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

Based on the user's question: "{user_query}", generate a valid SQL SELECT query that retrieves only the necessary columns to answer the question. **Do not use "SELECT *" unless there is absolutely no alternative.** Return only the SQL query without any additional explanation.
"""
    llm_for_sql = ChatOpenAI(temperature=0.0, model_name="gpt-4")
    messages = [SystemMessage(content=prompt)]
    sql_response = llm_for_sql(messages)
    return sql_response.content.strip()

def parse_selected_columns(sql_query: str) -> list:
    lower_query = sql_query.lower()
    select_index = lower_query.find("select")
    from_index = lower_query.find("from")
    if select_index == -1 or from_index == -1 or from_index < select_index:
        return []
    select_part = sql_query[select_index + len("select"):from_index].strip()
    if "*" in select_part:
        return []
    raw_columns = select_part.split(",")
    parsed_cols = []
    for col in raw_columns:
        col = col.strip()
        if " as " in col.lower():
            # Usa a parte após "AS" como nome da coluna
            alias = col.split(" as ")[1].strip()
            col = alias
        elif "." in col:
            col = col.split(".")[-1].strip()
        parsed_cols.append(col)
    return parsed_cols


def execute_sql_query(sql_query: str) -> str:
    try:
        selected_cols = parse_selected_columns(sql_query)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        print(f"[DEBUG] Executando SQL: {sql_query}")  # Log da consulta
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        print(f"[DEBUG] Número de registros retornados: {len(rows)}")  # Log do número de registros
        # Opcional: log dos primeiros registros para verificação
        if rows:
            print("[DEBUG] Primeiro registro:", rows[0])
        cursor.close()
        conn.close()
        if not rows:
            return "Nenhum registro encontrado."
        if not selected_cols:
            selected_cols = list(rows[0].keys())
        results = ""
        for row in rows:
            line_parts = []
            for col in selected_cols:
                value = row.get(col, "N/A")
                line_parts.append(f"{col}: {value}")
            results += " | ".join(line_parts) + "\n"
        return results.strip()
    except Exception as e:
        print("Erro na execução do SQL gerado:", e)
        return "Erro ao recuperar dados com o SQL gerado."


@app.on_event("startup")
async def startup_event():
    print("Criando as tabelas (se ainda não existirem)...")
    create_tables()
    print("Verificando e inserindo dados do CSV (se a tabela estiver vazia)...")
    insert_into_mysql()
    print("Indexando nomes de fazenda para busca semântica...")
    index_farm_names()
    print("Tarefas de startup concluídas.")

class ChatRequest(BaseModel):
    message: str
    chat_id: str

@app.get("/")
async def root():
    return {"message": "Copiloto de Vendas Backend Ativo!"}

@app.post("/chat")
async def chat_endpoint(chat_request: ChatRequest):
    chat_id = chat_request.chat_id
    user_message = chat_request.message

    # Salva a mensagem do usuário no banco de dados
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

    # Recupera o histórico do chat para montar o contexto
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

    # Ajusta a consulta do usuário incorporando a busca semântica para 'fazenda'
    adjusted_query = adjust_user_query(user_message)

    # Gera a consulta SQL dinamicamente com base na query ajustada
    try:
        print("Query ajustada:", adjusted_query)
        generated_sql = generate_sql_query(adjusted_query)
        print("SQL gerado:", generated_sql)
        relevant_data = execute_sql_query(generated_sql)
        print(f"Relevant Data: {relevant_data}")
    except Exception as e:
        print("Erro na geração/execução do SQL:", e)
        relevant_data = "Erro ao recuperar dados com o SQL gerado."

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
        "- ecc: Valor numérico (ex.: 2.1).\n"
        "- ciclicidade: Indicador de ciclo (0 ou 1).\n"
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
        "Utilize a formatação em **Markdown** para organizar sua resposta de forma clara e amigável. "
        "Apresente cada registro encontrado como um item de uma lista com texto em cor preta, utilizando cabeçalhos e bullet points. "
        "Caso os dados sejam melhor apresentados em formato de lista ou parágrafos, utilize o formato que achar mais claro.\n\n"
        "Sempre o texto da resposta em cor preta. "

        "Não diga que você consultou o banco de dados, apenas responda. "
        "Utilize os dados a seguir, se relevantes, para fundamentar suas respostas.\n\n"
        f"{table_explanation}\n"
        "Dados recuperados com base na consulta SQL gerada:\n"
        f"{relevant_data}"
    )


    messages_chain = []
    messages_chain.append(SystemMessage(content=system_content))
    for entry in history:
        if entry["remetente"] == "user":
            messages_chain.append(HumanMessage(content=entry["mensagem"]))
        elif entry["remetente"] == "bot":
            messages_chain.append(AIMessage(content=entry["mensagem"]))
    messages_chain.append(HumanMessage(content=user_message))

    try:
        llm = ChatOpenAI(temperature=0.7, model_name="gpt-4o-mini")
        response = llm(messages_chain)
        bot_reply = response.content.strip()
    except Exception as e:
        print("Erro na chamada do LangChain:", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resposta via LangChain: {str(e)}")

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

    return {"response": bot_reply}
