# Importamos a ferramenta "liquidificador" que já vem com o Flask
from werkzeug.security import generate_password_hash
import psycopg2

# As informações de conexão são as mesmas que usamos no app.py
DB_HOST = "localhost"
DB_NAME = "loja_estoque"
DB_USER = "postgres"
DB_PASS = "04039401093" # <<<<<<< COLOQUE SUA SENHA AQUI!

# Pedimos os dados no terminal
usuario = input("Digite o nome do usuário administrador: ")
senha = input(f"Digite a senha para o usuário '{usuario}': ")

# Aqui a mágica acontece: transformamos a senha em "vitamina" (hash)
senha_hash = generate_password_hash(senha)

try:
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cursor = conn.cursor()

    # Para garantir que teremos um único usuário, primeiro limpamos a tabela
    print("Limpando usuários antigos...")
    cursor.execute("DELETE FROM usuarios")

    # Agora, inserimos o novo usuário com a SENHA HASH, e não a senha real
    print(f"Criando o usuário '{usuario}'...")
    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario, senha_hash))

    conn.commit()
    cursor.close()
    conn.close()

    print("\nUsuário administrador criado com sucesso!")
    print("Lembre-se de usar este usuário e a senha original para fazer o login no sistema.")

except Exception as e:
    print(f"Ocorreu um erro: {e}")