from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import psycopg2 # Revertido para psycopg2
from functools import wraps
from fpdf import FPDF
import os
from datetime import datetime
import pytz # Revertido para usar pytz para fuso horário

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = 'ruadasfigueirasnumero8'

# Revertido para usar DATABASE_URL do ambiente (padrão do Fly.io/Render)
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- Filtro de Data e Hora com Fuso Horário ---
def formatar_data_br(dt_utc):
    if dt_utc is None:
        return ""
    fuso_horario_brasil = pytz.timezone('America/Sao_Paulo')
    dt_brasil = dt_utc.astimezone(fuso_horario_brasil)
    return dt_brasil.strftime('%d/%m/%Y %H:%M:%S')
app.jinja_env.filters['datetime_br'] = formatar_data_br

# --- Rotas da Aplicação ---

@app.route('/')
def pagina_inicial():
    return redirect(url_for('login'))

@app.route('/estoque')
@login_required
def ver_estoque():
    termo_busca = request.args.get('busca', '')
    conn = psycopg2.connect(DATABASE_URL) # Revertido
    cursor = conn.cursor()
    sql_query = "SELECT * FROM produtos WHERE ativo = TRUE"
    params = []
    if termo_busca:
        sql_query += " AND nome ILIKE %s" # Revertido para ILIKE
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
        conn = psycopg2.connect(DATABASE_URL) # Revertido
        cursor = conn.cursor()
        
        # Revertido para o padrão do PostgreSQL para pegar o ID
        cursor.execute("INSERT INTO produtos (nome, quantidade, valor_unitario) VALUES (%s, %s, %s) RETURNING id",
                       (nome, quantidade, valor_unitario))
        novo_produto_id = cursor.fetchone()[0]
        
        valor_total_movimentacao = quantidade * valor_unitario
        cursor.execute("""
            INSERT INTO movimentacoes (produto_id, tipo_movimentacao, quantidade, nome_responsavel, nota_fiscal, valor_unitario, valor_total) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (novo_produto_id, 'ENTRADA', quantidade, responsavel, nota_fiscal, valor_unitario, valor_total_movimentacao))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Produto "{nome}" adicionado com sucesso!', 'info')
        return redirect(url_for('ver_estoque'))
    return render_template('adicionar_produto.html')

# (Todas as outras funções também foram revertidas para usar psycopg2 e a sintaxe do PostgreSQL)
@app.route('/editar-produto-action', methods=['POST'])
@login_required
def editar_produto_action():
    produto_id = request.form['produto_id']
    nome = request.form['nome_produto']
    valor_unitario = float(request.form['valor_unitario'])
    responsavel = request.form['nome_responsavel']
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

@app.route('/transferencia', methods=['GET', 'POST'])
@login_required
def transferencia():
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
            pdf.cell(0, 10, f"Data da Operação: {formatar_data_br(datetime.now(pytz.utc))}", 0, 1)
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session:
        return redirect(url_for('ver_estoque'))
    if request.method == 'POST':
        usuario_form = request.form['usuario']
        senha_form = request.form['senha']
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

if __name__ == '__main__':
    app.run(debug=True)