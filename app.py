from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg2
from functools import wraps
from fpdf import FPDF
import os
from datetime import datetime


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            flash('Por favor, faça o login para acessar esta página.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = 'ruadasfigueirasnumero8'

# A única variável de ambiente que precisamos
DATABASE_URL = os.environ.get('DATABASE_URL')

@app.route('/')
@login_required
def pagina_inicial():
    return render_template('index.html')

@app.route('/estoque')
@login_required
def ver_estoque():
    termo_busca = request.args.get('busca', '')
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    sql_query = "SELECT * FROM produtos WHERE ativo = TRUE"
    params = []
    if termo_busca:
        sql_query += " AND nome ILIKE %s"
        params.append(f"%{termo_busca}%")
    sql_query += " ORDER BY nome ASC"
    cursor.execute(sql_query, params)
    lista_produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('estoque.html', produtos=lista_produtos, termo_busca=termo_busca)


@app.route('/adicionar-produto', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    if request.method == 'POST':
        nome = request.form['nome_produto']
        quantidade = int(request.form['quantidade_produto'])
        valor_unitario = float(request.form['valor_unitario'])
        responsavel = request.form['nome_responsavel']
        nota_fiscal = request.form['nota_fiscal']
        # MUDANÇA: Usando a nova conexão
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO produtos (nome, quantidade, valor_unitario) VALUES (%s, %s, %s) RETURNING id",
                       (nome, quantidade, valor_unitario))
        novo_produto_id = cursor.fetchone()[0]
        valor_total_movimentacao = quantidade * valor_unitario
        cursor.execute("""
            INSERT INTO movimentacoes 
            (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (novo_produto_id, 'ENTRADA', quantidade, responsavel, nota_fiscal, valor_unitario, valor_total_movimentacao))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Produto "{nome}" adicionado com sucesso!', 'info')
        return redirect(url_for('ver_estoque'))
    return render_template('adicionar_produto.html')

@app.route('/editar-produto-action', methods=['POST'])
@login_required
def editar_produto_action():
    produto_id = request.form['produto_id']
    nome = request.form['nome_produto']
    valor_unitario = float(request.form['valor_unitario'])
    responsavel = request.form['nome_responsavel']
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT quantidade FROM produtos WHERE id = %s", (produto_id,))
    quantidade_atual = cursor.fetchone()[0]
    valor_total_log = quantidade_atual * valor_unitario
    cursor.execute("UPDATE produtos SET nome = %s, valor_unitario = %s WHERE id = %s",
                   (nome, valor_unitario, produto_id))
    cursor.execute("""
        INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
        VALUES (%s, 'EDIÇÃO', %s, %s, 'N/A', %s, %s)""",
        (produto_id, quantidade_atual, responsavel, valor_unitario, valor_total_log))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Produto "{nome}" atualizado com sucesso!', 'info')
    return redirect(url_for('ver_estoque'))


@app.route('/inativar-produto/<int:id>', methods=['GET', 'POST'])
@login_required
def inativar_produto(id):
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    if request.method == 'POST':
        responsavel = request.form['nome_responsavel']
        cursor.execute("SELECT quantidade, valor_unitario FROM produtos WHERE id = %s", (id,))
        produto_dados = cursor.fetchone()
        quantidade_atual = produto_dados[0]
        valor_unitario_atual = float(produto_dados[1])
        valor_total_atual = quantidade_atual * valor_unitario_atual
        cursor.execute("""
            INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (id, 'INATIVAÇÃO', quantidade_atual, responsavel, 'N/A', valor_unitario_atual, valor_total_atual))
        cursor.execute("UPDATE produtos SET ativo = FALSE WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('ver_estoque'))
    cursor.execute("SELECT * FROM produtos WHERE id = %s", (id,))
    produto = cursor.fetchone()
    cursor.close()
    conn.close()
    if produto is None:
        return redirect(url_for('ver_estoque'))
    return render_template('inativar_produto.html', produto=produto)

@app.route('/diminuir-estoque-action', methods=['POST'])
@login_required
def diminuir_estoque_action():
    produto_id = request.form['produto_id']
    quantidade_a_remover = int(request.form['quantidade'])
    responsavel = request.form['nome_responsavel']
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT quantidade, valor_unitario FROM produtos WHERE id = %s", (produto_id,))
    produto_dados = cursor.fetchone()
    estoque_atual = produto_dados[0]
    valor_unitario_atual = float(produto_dados[1])
    if estoque_atual >= quantidade_a_remover:
        valor_total_movimentacao = quantidade_a_remover * valor_unitario_atual
        cursor.execute("UPDATE produtos SET quantidade = quantidade - %s WHERE id = %s", (quantidade_a_remover, produto_id))
        cursor.execute("""
            INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (produto_id, 'SAÍDA', quantidade_a_remover, responsavel, None, valor_unitario_atual, valor_total_movimentacao))
        conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('ver_estoque'))

@app.route('/log')
@login_required
def ver_log():
    termo_busca = request.args.get('busca', '')
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    sql = """
        SELECT m.data_hora, p.nome, m.tipo_movimentacao, m.quantidade, m.nome_responsavel, m.nota_fiscal, m.valor_unitario, m.valor_total
        FROM movimentacoes m JOIN produtos p ON m.produto_id = p.id
    """
    params = []
    if termo_busca:
        sql += " WHERE (p.nome ILIKE %s OR m.tipo_movimentacao ILIKE %s OR m.nome_responsavel ILIKE %s OR m.nota_fiscal ILIKE %s)"
        params = [f"%{termo_busca}%"] * 4
    sql += " ORDER BY m.data_hora DESC"
    cursor.execute(sql, params)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('log.html', logs=logs, termo_busca=termo_busca)

@app.route('/aumentar-estoque-action', methods=['POST'])
@login_required
def aumentar_estoque_action():
    produto_id = request.form['produto_id']
    quantidade_a_adicionar = int(request.form['quantidade'])
    responsavel = request.form['nome_responsavel']
    nota_fiscal = request.form['nota_fiscal']
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT valor_unitario FROM produtos WHERE id = %s", (produto_id,))
    valor_unitario_atual = float(cursor.fetchone()[0])
    valor_total_movimentacao = quantidade_a_adicionar * valor_unitario_atual
    cursor.execute("UPDATE produtos SET quantidade = quantidade + %s WHERE id = %s", (quantidade_a_adicionar, produto_id))
    cursor.execute("""
        INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (produto_id, 'ENTRADA', quantidade_a_adicionar, responsavel, nota_fiscal, valor_unitario_atual, valor_total_movimentacao))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('ver_estoque'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_form = request.form['usuario']
        senha_form = request.form['senha']
        # MUDANÇA: Usando a nova conexão
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario_form,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        if user_data and check_password_hash(user_data[2], senha_form):
            session['loggedin'] = True
            session['id'] = user_data[0]
            session['username'] = user_data[1]
            return redirect(url_for('ver_estoque'))
        else:
            flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/inativos')
@login_required
def ver_inativos():
    termo_busca = request.args.get('busca', '')
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    sql = "SELECT * FROM produtos WHERE ativo = FALSE"
    params = []
    if termo_busca:
        sql += " AND nome ILIKE %s"
        params.append(f"%{termo_busca}%")
    sql += " ORDER BY nome ASC"
    cursor.execute(sql, params)
    lista_produtos_inativos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('inativos.html', produtos=lista_produtos_inativos, termo_busca=termo_busca)

@app.route('/reativar-produto-action', methods=['POST'])
@login_required
def reativar_produto_action():
    produto_id = request.form['produto_id']
    responsavel = request.form['nome_responsavel']
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT quantidade, valor_unitario FROM produtos WHERE id = %s", (produto_id,))
    produto_dados = cursor.fetchone()
    quantidade_atual = produto_dados[0]
    valor_unitario_atual = float(produto_dados[1])
    valor_total_atual = quantidade_atual * valor_unitario_atual
    cursor.execute("UPDATE produtos SET ativo = TRUE WHERE id = %s", (produto_id,))
    cursor.execute("""
        INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (produto_id, 'REATIVAÇÃO', quantidade_atual, responsavel, 'N/A', valor_unitario_atual, valor_total_atual))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Produto reativado com sucesso!', 'info')
    return redirect(url_for('ver_estoque'))


@app.route('/transferencia', methods=['GET', 'POST'])
@login_required
def transferencia():
    # MUDANÇA: Usando a nova conexão
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        cursor.execute("SELECT * FROM produtos WHERE ativo = TRUE ORDER BY nome ASC")
        produtos = cursor.fetchall()
        loja_origem = request.form.get('loja_origem')
        loja_destino = request.form.get('loja_destino')
        responsavel = request.form.get('nome_responsavel')
        produtos_transferidos = []
        for produto in produtos:
            produto_id = produto[0]
            produto_nome = produto[1]
            estoque_atual = produto[2]
            valor_unitario = float(produto[4])
            nome_campo = f"quantidade_{produto_id}"
            quantidade_str = request.form.get(nome_campo)
            if quantidade_str and int(quantidade_str) > 0:
                quantidade_int = int(quantidade_str)
                if quantidade_int > estoque_atual:
                    flash(f"ERRO: A quantidade para '{produto_nome}' ({quantidade_int}) é maior que o estoque ({estoque_atual}). A transferência foi cancelada.", "error")
                    cursor.close()
                    conn.close()
                    return redirect(url_for('transferencia'))
                produtos_transferidos.append({
                    "id": produto_id, "nome": produto_nome, "quantidade": quantidade_int, "valor": valor_unitario
                })
        if not produtos_transferidos:
            flash("Nenhum produto selecionado para transferência.", "error")
            cursor.close()
            conn.close()
            return redirect(url_for('transferencia'))
        for item in produtos_transferidos:
            cursor.execute("UPDATE produtos SET quantidade = quantidade - %s WHERE id = %s", (item['quantidade'], item['id']))
            valor_total_item = item['quantidade'] * item['valor']
            info_transferencia = f"Transferência para: {loja_destino}"
            cursor.execute("""
                INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total)
                VALUES (%s, 'TRANSFERÊNCIA', %s, %s, %s, %s, %s)""",
                (item['id'], item['quantidade'], responsavel, info_transferencia, item['valor'], valor_total_item))
        conn.commit()
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Comprovante de Transferência de Estoque', 0, 1, 'C')
            pdf.ln(10)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f'Loja de Origem: {loja_origem}', 0, 1)
            pdf.cell(0, 10, f'Loja de Destino: {loja_destino}', 0, 1)
            pdf.cell(0, 10, f'Responsável pela Transferência: {responsavel}', 0, 1)
            pdf.cell(0, 10, f"Data da Operação: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
            pdf.ln(10)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(130, 10, 'Produto', 1, 0, 'C')
            pdf.cell(60, 10, 'Quantidade', 1, 1, 'C')
            pdf.set_font('Arial', '', 12)
            for item in produtos_transferidos:
                pdf.cell(130, 10, item['nome'].encode('latin-1', 'replace').decode('latin-1'), 1, 0)
                pdf.cell(60, 10, str(item['quantidade']), 1, 1, 'C')
            pdf.ln(20)
            pdf.cell(0, 10, 'Data de Entrega: ____/____/______', 0, 1)
            pdf.ln(10)
            pdf.cell(0, 10, '_________________________________________', 0, 1, 'C')
            pdf.cell(0, 10, 'Assinatura de Quem Recebeu', 0, 1, 'C')
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_do_arquivo_pdf = f"transferencia_{timestamp}.pdf"
            pdf_file_path = os.path.join('static', nome_do_arquivo_pdf)
            pdf.output(pdf_file_path)
            
            cursor.close()
            conn.close()
            
            return render_template('transferencia_sucesso.html', nome_pdf=nome_do_arquivo_pdf)
        except Exception as e:
            flash(f"Transferência registrada, mas houve um erro ao gerar o PDF: {e}", "error")
            return redirect(url_for('ver_estoque'))

    cursor.execute("SELECT * FROM produtos WHERE ativo = TRUE ORDER BY nome ASC")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('transferencia.html', produtos=produtos)

@app.route('/download/<path:nome_arquivo>')
@login_required
def download_arquivo(nome_arquivo):
    return send_from_directory('static', nome_arquivo, as_attachment=True)

# ROTA TEMPORÁRIA E SECRETA PARA CONFIGURAÇÃO INICIAL NA NUVEM
@app.route('/configuracao-inicial-secreta-12345')
def setup_inicial_secreto():
    # --- DEFINA O USUÁRIO E SENHA DA DONA DA LOJA AQUI ---
    usuario_admin = 'admin' # Ou o nome de usuário que preferir
    senha_admin = '91844720' # <-- TROQUE PELA SENHA REAL E SEGURA

    print("INICIANDO CONFIGURAÇÃO NA NUVEM...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Lógica do setup_database.py
        print("Criando tabelas...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY, nome TEXT NOT NULL UNIQUE, quantidade INTEGER NOT NULL,
            ativo BOOLEAN DEFAULT TRUE, valor_unitario NUMERIC(10, 2) DEFAULT 0.00 );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY, usuario TEXT NOT NULL UNIQUE, senha TEXT NOT NULL );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id SERIAL PRIMARY KEY, produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
            tipo_movimentacao TEXT NOT NULL, quantidade INTEGER NOT NULL, nome_responsavel TEXT NOT NULL,
            nota_fiscal TEXT, data_hora TIMESTAMPTZ DEFAULT NOW(), valor_unitario NUMERIC(10, 2) DEFAULT 0.00,
            valor_total NUMERIC(10, 2) DEFAULT 0.00 );
        """)
        print("Tabelas criadas.")

        # Lógica do create_admin_user.py
        senha_hash = generate_password_hash(senha_admin)
        print("Limpando usuários antigos e criando o administrador...")
        cursor.execute("TRUNCATE TABLE usuarios RESTART IDENTITY") # Limpa a tabela de forma segura
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (usuario_admin, senha_hash))
        print("Usuário administrador criado.")

        conn.commit()
        cursor.close()
        conn.close()

        return "<h1>CONFIGURAÇÃO INICIAL CONCLUÍDA COM SUCESSO!</h1><p>Por favor, delete esta rota ('/configuracao-inicial-secreta-12345') do seu arquivo app.py e envie para o GitHub novamente.</p>"

    except Exception as e:
        return f"<h1>Ocorreu um erro durante a configuração:</h1><p>{e}</p>"

if __name__ == '__main__':
    app.run(debug=True)