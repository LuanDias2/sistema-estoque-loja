from werkzeug.security import generate_password_hash
import psycopg2
import os

# Agora ele também lê a conexão do ambiente
DATABASE_URL = os.environ.get('DATABASE_URL')

usuario = input("Digite o nome do usuário administrador: ")
senha = input(f"Digite a senha para o usuário '{usuario}': ")

senha_hash = generate_password_hash(senha)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Limpando usuários antigos...")
    cursor.execute("DELETE FROM usuarios")

    print(f"Criando o usuário '{usuario}'...")
    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\nUsuário administrador criado com sucesso!")

except Exception as e:
    print(f"Ocorreu um erro: {e}")