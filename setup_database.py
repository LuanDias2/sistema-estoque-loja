import psycopg2

# --- INFORMAÇÕES DE CONEXÃO COM O POSTGRESQL ---
# Altere estes dados de acordo com a sua instalação!
DB_HOST = "localhost"
DB_NAME = "loja_estoque"
DB_USER = "postgres"
DB_PASS = "04039401093"  # <<<<<<< COLOQUE A SENHA QUE VOCÊ DEFINIU NA INSTALAÇÃO AQUI!

try:
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cursor = conn.cursor()

    print("Criando a tabela 'produtos'...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL UNIQUE,
        descricao TEXT,
        quantidade INTEGER NOT NULL
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
        produto_id INTEGER NOT NULL REFERENCES produtos(id),
        tipo_movimentacao TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        nome_responsavel TEXT NOT NULL,
        nota_fiscal TEXT,
        data_hora TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("\nTabelas criadas com sucesso! O banco de dados está pronto.")

except Exception as e:
    print(f"Ocorreu um erro: {e}")