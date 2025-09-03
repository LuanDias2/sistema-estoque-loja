import mysql.connector
from mysql.connector import errorcode

# --- COLOQUE SUAS 4 INFORMAÇÕES DA HOSTINGER AQUI ---
DB_CONFIG = {
    'user': 'u395160423_loja_admin',
    'password': '@Luan4556',
    'host': 'localhost', # Geralmente 'localhost'
    'database': 'u395160423_loja_estoque'
}

try:
    print("Conectando ao banco de dados MySQL...")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Criando a tabela 'produtos'...")
    # SQL ajustado para MySQL: INT AUTO_INCREMENT, VARCHAR, DECIMAL, ENGINE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL UNIQUE,
        quantidade INT NOT NULL,
        ativo BOOLEAN DEFAULT TRUE,
        valor_unitario DECIMAL(10, 2) DEFAULT 0.00
    ) ENGINE=InnoDB;
    """)

    print("Criando a tabela 'usuarios'...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario VARCHAR(255) NOT NULL UNIQUE,
        senha VARCHAR(255) NOT NULL
    ) ENGINE=InnoDB;
    """)

    print("Criando a tabela 'movimentacoes'...")
    # SQL ajustado para MySQL: DATETIME, CURRENT_TIMESTAMP
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        produto_id INT NOT NULL,
        tipo_movimentacao VARCHAR(50) NOT NULL,
        quantidade INT NOT NULL,
        nome_responsavel VARCHAR(255) NOT NULL,
        nota_fiscal VARCHAR(255),
        data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        valor_unitario DECIMAL(10, 2) DEFAULT 0.00,
        valor_total DECIMAL(10, 2) DEFAULT 0.00,
        FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE
    ) ENGINE=InnoDB;
    """)

    conn.commit()
    print("\nTabelas prontas para o MySQL!")

except mysql.connector.Error as err:
    print(f"Ocorreu um erro: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("Conexão com MySQL fechada.")