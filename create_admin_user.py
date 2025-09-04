from werkzeug.security import generate_password_hash
import psycopg2
import os

# Lê a conexão do ambiente, que será fornecida pelo Fly.io
DATABASE_URL = os.environ.get('DATABASE_URL')

usuario = input("Digite o nome do usuário administrador: ")
senha = input(f"Digite a senha para o usuário '{usuario}': ")

senha_hash = generate_password_hash(senha)

try:
    # Volta a usar a conexão do psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Limpando usuários antigos...")
    # TRUNCATE TABLE ... RESTART IDENTITY é a forma do PostgreSQL de zerar a tabela e o contador de IDs
    cursor.execute("TRUNCATE TABLE usuarios RESTART IDENTITY")

    print(f"Criando o usuário '{usuario}'...")
    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))
    
    conn.commit()
    
    print("\nUsuário administrador criado com sucesso!")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
finally:
    if 'conn' in locals():
        cursor.close()
        conn.close()
        print("Conexão com PostgreSQL fechada.")