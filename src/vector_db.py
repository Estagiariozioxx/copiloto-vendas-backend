# src/vector_db.py
import os
import math
import openai
from dotenv import load_dotenv

load_dotenv()

# Dicionários para armazenar os embeddings de cada coluna
farm_embeddings = {}       # Para a coluna 'fazenda'
raca_embeddings = {}        # Para a coluna 'raca'
municipio_embeddings = {}   # Para a coluna 'municipio'
implante_embeddings = {}    # Para a coluna 'implante_p4'
empresa_embeddings = {}     # Para a coluna 'empresa'

def normalize_vector(v):
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v

def get_embedding(text: str, engine: str = "text-embedding-ada-002"):
    """
    Gera um embedding para o texto fornecido usando a API do OpenAI.
    Converte cada componente para float, arredonda e normaliza o vetor.
    """
    response = openai.embeddings.create(input=[text], model=engine)
    embedding = response.data[0].embedding
    embedding = [round(float(x), 6) for x in embedding]
    embedding = normalize_vector(embedding)
    return embedding

# Funções para adicionar embeddings

def add_farm_embedding(farm_id: str, farm_name: str):
    embedding = get_embedding(farm_name, engine="text-embedding-ada-002")
    farm_embeddings[farm_id] = {"name": farm_name, "embedding": embedding}

def add_raca_embedding(raca: str):
    raca_processed = raca.strip()
    raca_id = raca_processed.lower().replace(" ", "_")
    raca_id = raca_id.encode("ascii", "ignore").decode("ascii")
    embedding = get_embedding(raca_processed, engine="text-embedding-ada-002")
    raca_embeddings[raca_id] = {"name": raca_processed, "embedding": embedding}

def add_municipio_embedding(municipio: str):
    municipio_processed = municipio.strip()
    municipio_id = municipio_processed.lower().replace(" ", "_")
    municipio_id = municipio_id.encode("ascii", "ignore").decode("ascii")
    embedding = get_embedding(municipio_processed, engine="text-embedding-ada-002")
    municipio_embeddings[municipio_id] = {"name": municipio_processed, "embedding": embedding}

def add_implante_embedding(implante: str):
    implante_processed = implante.strip()
    implante_id = implante_processed.lower().replace(" ", "_")
    implante_id = implante_id.encode("ascii", "ignore").decode("ascii")
    embedding = get_embedding(implante_processed, engine="text-embedding-ada-002")
    implante_embeddings[implante_id] = {"name": implante_processed, "embedding": embedding}

def add_empresa_embedding(empresa: str):
    empresa_processed = empresa.strip()
    empresa_id = empresa_processed.lower().replace(" ", "_")
    empresa_id = empresa_id.encode("ascii", "ignore").decode("ascii")
    embedding = get_embedding(empresa_processed, engine="text-embedding-ada-002")
    empresa_embeddings[empresa_id] = {"name": empresa_processed, "embedding": embedding}

# Função para calcular similaridade cosseno
def cosine_similarity(a, b):
    return sum(x * y for x, y in zip(a, b))

# Funções para realizar buscas semânticas com log de similaridade

def search_farm(query: str, top_k: int = 1, threshold: float = 0.83):
    query_embedding = get_embedding(query, engine="text-embedding-ada-002")
    similarities = []
    for farm_id, data in farm_embeddings.items():
        sim = cosine_similarity(query_embedding, data["embedding"])
        similarities.append((sim, data["name"]))
    similarities.sort(key=lambda x: x[0], reverse=True)
    if similarities:
        best_similarity, best_name = similarities[0]
        similarity_pct = best_similarity * 100
        print(f"[LOG] (Fazenda) Para a query '{query}', o melhor match foi '{best_name}' com similaridade de {similarity_pct:.2f}%")
        if best_similarity >= threshold:
            return [best_name]
    print(f"[LOG] (Fazenda) Para a query '{query}', nenhum match atingiu o limiar de {threshold*100:.2f}%.")
    return []

def search_raca(query: str, top_k: int = 1, threshold: float = 0.83):
    query_embedding = get_embedding(query, engine="text-embedding-ada-002")
    similarities = []
    for raca_id, data in raca_embeddings.items():
        sim = cosine_similarity(query_embedding, data["embedding"])
        similarities.append((sim, data["name"]))
    similarities.sort(key=lambda x: x[0], reverse=True)
    if similarities:
        best_similarity, best_name = similarities[0]
        similarity_pct = best_similarity * 100
        print(f"[LOG] (Raça) Para a query '{query}', o melhor match foi '{best_name}' com similaridade de {similarity_pct:.2f}%")
        if best_similarity >= threshold:
            return [best_name]
    print(f"[LOG] (Raça) Para a query '{query}', nenhum match atingiu o limiar de {threshold*100:.2f}%.")
    return []

def search_municipio(query: str, top_k: int = 1, threshold: float = 0.83):
    query_embedding = get_embedding(query, engine="text-embedding-ada-002")
    similarities = []
    for municipio_id, data in municipio_embeddings.items():
        sim = cosine_similarity(query_embedding, data["embedding"])
        similarities.append((sim, data["name"]))
    similarities.sort(key=lambda x: x[0], reverse=True)
    if similarities:
        best_similarity, best_name = similarities[0]
        similarity_pct = best_similarity * 100
        print(f"[LOG] (Município) Para a query '{query}', o melhor match foi '{best_name}' com similaridade de {similarity_pct:.2f}%")
        if best_similarity >= threshold:
            return [best_name]
    print(f"[LOG] (Município) Para a query '{query}', nenhum match atingiu o limiar de {threshold*100:.2f}%.")
    return []

def search_implante(query: str, top_k: int = 1, threshold: float = 0.83):
    query_embedding = get_embedding(query, engine="text-embedding-ada-002")
    similarities = []
    for implante_id, data in implante_embeddings.items():
        sim = cosine_similarity(query_embedding, data["embedding"])
        similarities.append((sim, data["name"]))
    similarities.sort(key=lambda x: x[0], reverse=True)
    if similarities:
        best_similarity, best_name = similarities[0]
        similarity_pct = best_similarity * 100
        print(f"[LOG] (Implante) Para a query '{query}', o melhor match foi '{best_name}' com similaridade de {similarity_pct:.2f}%")
        if best_similarity >= threshold:
            return [best_name]
    print(f"[LOG] (Implante) Para a query '{query}', nenhum match atingiu o limiar de {threshold*100:.2f}%.")
    return []

def search_empresa(query: str, top_k: int = 1, threshold: float = 0.83):
    query_embedding = get_embedding(query, engine="text-embedding-ada-002")
    similarities = []
    for empresa_id, data in empresa_embeddings.items():
        sim = cosine_similarity(query_embedding, data["embedding"])
        similarities.append((sim, data["name"]))
    similarities.sort(key=lambda x: x[0], reverse=True)
    if similarities:
        best_similarity, best_name = similarities[0]
        similarity_pct = best_similarity * 100
        print(f"[LOG] (Empresa) Para a query '{query}', o melhor match foi '{best_name}' com similaridade de {similarity_pct:.2f}%")
        if best_similarity >= threshold:
            return [best_name]
    print(f"[LOG] (Empresa) Para a query '{query}', nenhum match atingiu o limiar de {threshold*100:.2f}%.")
    return []
