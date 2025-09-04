import psycopg2
import os

# Lê a conexão do ambiente, que será fornecida pelo Fly.io
DATABASE_URL = os.environ.get('DATABASE_URL')

try:
    print("Conectando ao banco de dados PostgreSQL...")
    # Volta a usar a conexão do psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("Criando a tabela 'produtos'...")
    # SQL revertido para a sintaxe do PostgreSQL (SERIAL, TEXT, etc.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL UNIQUE,
        quantidade INTEGER NOT NULL,
        ativo BOOLEAN DEFAULT TRUE,
        valor_unitario NUMERIC(10, 2) DEFAULT 0.00
    );
    """)

    print("Criando a tabela 'usuarios'...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        usuario TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL
    );
    """)

    print("Criando a tabela 'movimentacoes'...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id SERIAL PRIMARY KEY,
        produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
        tipo_movimentacao TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        nome_responsavel TEXT NOT NULL,
        nota_fiscal TEXT,
        data_hora TIMESTAMPTZ DEFAULT NOW(),
        valor_unitario NUMERIC(10, 2) DEFAULT 0.00,
        valor_total NUMERIC(10, 2) DEFAULT 0.00
    );
    """)

    conn.commit()
    print("\nEstrutura de tabelas para PostgreSQL está pronta!")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
finally:
    if 'conn' in locals() and not conn.closed:
        cursor.close()
        conn.close()
        print("Conexão com PostgreSQL fechada.")