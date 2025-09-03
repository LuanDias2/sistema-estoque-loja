from werkzeug.security import generate_password_hash
import mysql.connector

# --- COLOQUE SUAS 4 INFORMAÇÕES DA HOSTINGER AQUI ---
DB_CONFIG = {
    'user': 'u395160423_loja_admin',
    'password': '@Luan4556',
    'host': 'localhost', # Geralmente 'localhost'
    'database': 'u395160423_loja_estoque'
}

usuario = input("Digite o nome do usuário administrador: ")
senha = input(f"Digite a senha para o usuário '{usuario}': ")

senha_hash = generate_password_hash(senha)

try:
    # Nova forma de conectar, específica para MySQL
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("Limpando usuários antigos...")
    # TRUNCATE TABLE é um comando eficiente para zerar a tabela no MySQL
    cursor.execute("TRUNCATE TABLE usuarios")

    print(f"Criando o usuário '{usuario}'...")
    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))
    
    conn.commit()
    
    print("\nUsuário administrador criado com sucesso!")

except mysql.connector.Error as err:
    print(f"Ocorreu um erro: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("Conexão com MySQL fechada.")