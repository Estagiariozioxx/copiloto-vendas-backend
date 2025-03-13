# src/ingest_data.py
import csv
import os
from src.database import get_db_connection

# Caminho para o CSV (ajuste conforme necessário)
file_path = "/app/planilha2.csv"

# Abrir e ler o CSV usando csv.DictReader
with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=",")
    rows = list(reader)

# Função para renomear chaves conforme necessário
def rename_keys(row):
    mapping = {
        "GnRH NA IA": "grhh_na_ia",
        "PGF NO D0": "pgf_no_do",
        "Nº da IATF": "numero_iate",
        "DOSE eCG": "dose_ecg"
    }
    for old_key, new_key in mapping.items():
        if old_key in row:
            row[new_key] = row.pop(old_key)
    return row

# Aplicar a renomeação em todas as linhas
rows = [rename_keys(row) for row in rows]

def insert_into_mysql():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar se a tabela "inseminacao" já possui dados
    cursor.execute("SELECT COUNT(*) FROM inseminacao")
    count = cursor.fetchone()[0]

    if count > 0:
        print("Dados já inseridos. Pulando a inserção.")
    else:
        for row in rows:
            try:
                # Conversões necessárias
                ecc = float(row["ECC"])
                ciclicidade = int(row["CICLICIDADE"])
                grhh_na_ia = int(row["grhh_na_ia"])
                pgf_no_do = int(row["pgf_no_do"])
                dg_str = row["DG"]
                dg = int(''.join(filter(str.isdigit, dg_str))) if any(c.isdigit() for c in dg_str) else 0
                vazia = int(row["VAZIA COM OU SEM CL"])
                perda = int(row["PERDA"])
            except Exception as e:
                print("Erro na conversão de tipos para a linha:", row)
                print("Erro:", e)
                continue  # pula a linha se houver erro de conversão

            cursor.execute("""
                INSERT INTO inseminacao (
                    fazenda, estado, municipio, numero_animal, lote, raca, categoria, ecc, 
                    ciclicidade, protocolo, implante_p4, empresa, grhh_na_ia, pgf_no_do, 
                    dose_pgf_retirada, marca_pgf_retirada, dose_ce, ecg, dose_ecg, touro, 
                    raca_touro, empresa_touro, inseminador, numero_iatf, dg, vazia_com_ou_sem_cl, perda
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row["FAZENDA"],
                row["ESTADO"],
                row["MUNICÍPIO"],
                row["Nº ANIMAL"],
                row["LOTE"],
                row["RAÇA"],
                row["CATEGORIA"],
                ecc,
                ciclicidade,
                row["PROTOCOLO"],
                row["IMPLANTE P4"],
                row["EMPRESA"],
                grhh_na_ia,
                pgf_no_do,
                row["Dose PGF retirada"],
                row["Marca PGF retirada"],
                row["Dose CE"],
                row["eCG"],
                row["dose_ecg"],
                row["TOURO"],
                row["RAÇA TOURO"],
                row["EMPRESA TOURO"],
                row["INSEMINADOR"],
                row["numero_iate"],
                dg,
                vazia,
                perda
            ))
        print("Dados inseridos com sucesso.")

    conn.commit()
    cursor.close()
    conn.close()

# Funções para indexação de embeddings para diferentes colunas

import logging

logging.basicConfig(level=logging.INFO)

def index_farm_names():
    from src.vector_db import add_farm_embedding
    unique_farms = set(row["FAZENDA"] for row in rows)
    for farm in unique_farms:
        words = farm.split()
        if words and words[0].lower() == "fazenda":
            farm_processed = " ".join(words[1:]).strip()
        else:
            farm_processed = farm.strip()
        farm_id = farm_processed.lower().replace(" ", "_")
        farm_id = farm_id.encode("ascii", "ignore").decode("ascii")
        add_farm_embedding(farm_id, farm_processed)
    logging.info("Indexação de nomes de fazenda concluída.")

def index_raca_embeddings():
    from src.vector_db import add_raca_embedding
    unique_racas = set(row["RAÇA"] for row in rows)
    for raca in unique_racas:
        logging.info("Raça: " + raca)
        add_raca_embedding(raca)
    logging.info("Indexação de raças concluída.")

def index_municipio_embeddings():
    """
    Indexa os valores únicos da coluna 'MUNICÍPIO' utilizando embeddings.
    """
    from src.vector_db import add_municipio_embedding
    unique_municipios = set(row["MUNICÍPIO"] for row in rows)
    for municipio in unique_municipios:
        add_municipio_embedding(municipio)
    print("Indexação de municípios concluída.")

def index_implante_embeddings():
    """
    Indexa os valores únicos da coluna 'IMPLANTE P4' utilizando embeddings.
    """
    from src.vector_db import add_implante_embedding
    unique_implantes = set(row["IMPLANTE P4"] for row in rows)
    for implante in unique_implantes:
        add_implante_embedding(implante)
    print("Indexação de implantes concluída.")

def index_empresa_embeddings():
    """
    Indexa os valores únicos da coluna 'EMPRESA' utilizando embeddings.
    """
    from src.vector_db import add_empresa_embedding
    unique_empresas = set(row["EMPRESA"] for row in rows)
    for empresa in unique_empresas:
        add_empresa_embedding(empresa)
    print("Indexação de empresas concluída.")

if __name__ == '__main__':
    insert_into_mysql()
    index_farm_names()
    index_raca_embeddings()
    index_municipio_embeddings()
    index_implante_embeddings()
    index_empresa_embeddings()
