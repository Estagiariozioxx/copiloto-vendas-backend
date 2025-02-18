import os
import mysql.connector
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do MySQL
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
#FAZENDA,ESTADO,MUNICÍPIO,Nº ANIMAL,LOTE,RAÇA,CATEGORIA,ECC,CICLICIDADE,PROTOCOLO,IMPLANTE P4,EMPRESA,GnRH NA IA,PGF NO D0,Dose PGF retirada,Marca PGF retirada,Dose CE,eCG,DOSE eCG,TOURO,RAÇA TOURO,EMPRESA TOURO,INSEMINADOR,Nº da IATF,DG,VAZIA COM OU SEM CL,PERDA
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()




    # Criando a tabela "inseminacao" baseada na estrutura da planilha
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inseminacao (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fazenda VARCHAR(255),
            estado VARCHAR(10),
            municipio VARCHAR(255),
            numero_animal VARCHAR(50),
            lote VARCHAR(50),
            raca VARCHAR(50),
            categoria VARCHAR(100),
            ecc FLOAT,
            ciclicidade INT,
            protocolo VARCHAR(100),
            implante_p4 VARCHAR(100),
            empresa VARCHAR(100),
            grhh_na_ia INT,
            pgf_no_do INT,
            dose_pgf_retirada VARCHAR(50),
            marca_pgf_retirada VARCHAR(100),
            dose_ce VARCHAR(50),
            ecg VARCHAR(50),
            dose_ecg VARCHAR(50),
            touro VARCHAR(100),
            raca_touro VARCHAR(50),
            empresa_touro VARCHAR(100),
            inseminador VARCHAR(100),
            numero_iate VARCHAR(50),
            dg INT,
            vazia_com_ou_sem_cl INT,
            perda INT
        )
    """)

    # Criando a tabela "historico_chat" para salvar o histórico de conversas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_chat (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat_id VARCHAR(50),
            mensagem TEXT,
            remetente ENUM('user', 'bot'),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

# Criar as tabelas ao iniciar
create_tables()
