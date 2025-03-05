# src/vector_db.py
import os
import math
import openai
from dotenv import load_dotenv

load_dotenv()

# Dicionário para armazenar os embeddings das fazendas.
# Chave: ID gerado para a fazenda; Valor: dicionário com "name" e "embedding"
farm_embeddings = {}

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

def add_farm_embedding(farm_id: str, farm_name: str):
    """
    Gera e armazena o embedding para o nome de uma fazenda.
    """
    embedding = get_embedding(farm_name, engine="text-embedding-ada-002")
    farm_embeddings[farm_id] = {"name": farm_name, "embedding": embedding}

def cosine_similarity(a, b):
    """
    Calcula a similaridade cosseno entre dois vetores.
    Como os vetores já estão normalizados, é apenas o produto escalar.
    """
    return sum(x * y for x, y in zip(a, b))

def search_farm(query: str, top_k: int = 1, threshold: float = 0.83):
    """
    Realiza a busca semântica para encontrar os nomes de fazenda mais similares
    ao texto da consulta.
    
    Retorna uma lista com o nome da fazenda se a similaridade do melhor match
    for superior ao limiar; caso contrário, retorna uma lista vazia.
    Também registra em log o percentual de similaridade do melhor match.
    """
    query_embedding = get_embedding(query, engine="text-embedding-ada-002")
    similarities = []
    for farm_id, data in farm_embeddings.items():
        sim = cosine_similarity(query_embedding, data["embedding"])
        similarities.append((sim, data["name"]))
    # Ordena os resultados pela similaridade em ordem decrescente
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    if similarities:
        best_similarity, best_name = similarities[0]
        # Converte para percentual e formata com duas casas decimais
        similarity_pct = best_similarity * 100
        print(f"[LOG] Para a query '{query}', o melhor match foi '{best_name}' com similaridade de {similarity_pct:.2f}%")
        if best_similarity >= threshold:
            return [best_name]
    
    print(f"[LOG] Para a query '{query}', nenhum match atingiu o limiar de {threshold * 100:.2f}%.")
    return []