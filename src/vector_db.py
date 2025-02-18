import os
from dotenv import load_dotenv
from langchain_community.embeddings import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

# Carregar variáveis de ambiente
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Cria uma instância do Pinecone usando sua API Key
pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "inseminacao"

# Verifica se o índice existe; caso contrário, cria-o
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,       # Certifique-se de que a dimensão corresponde ao tamanho dos seus embeddings
        metric="euclidean",   # Ou outro métrico, conforme sua necessidade
        spec=ServerlessSpec(
            cloud="aws",      # Ajuste conforme seu provedor se necessário
            region="us-west-2"  # Ajuste para a região apropriada
        )
    )

# Obter referência ao índice criado
index = pc.index(index_name)

# Cria uma instância do OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

def add_to_vector_db(text):
    """Gera o embedding para o texto e o insere (upsert) no índice usando o próprio texto como ID."""
    vector = embeddings.embed_query(text)
    index.upsert([(text, vector)])

def query_vector_db(query):
    """Gera o embedding para a consulta, faz a query no índice e retorna os IDs dos melhores resultados."""
    vector = embeddings.embed_query(query)
    results = index.query(vector, top_k=5, include_metadata=True)
    return [match["id"] for match in results["matches"]]
