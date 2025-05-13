from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory
from werkzeug.utils import secure_filename
from io import BytesIO
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_segura'  # Altere para uma chave única

# Configurações
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuração do Banco de Dados - ATUALIZE COM SEUS DADOS!
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',          # Seu usuário MySQL
    'password': '',          # Sua senha MySQL
    'database': 'patrimonio' # Nome do banco
}

# Helper Functions
def get_db_connection():
    """Estabelece conexão com o MySQL"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Erro de conexão MySQL: {e}")
        return None

def allowed_file(filename):
    """Verifica extensões permitidas"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    """Cria pasta de uploads se não existir"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# Rotas Básicas
@app.route('/')
def index():
    """Rota principal"""
    if 'usuario' in session:
        return redirect(url_for('listar'))
    return redirect(url_for('login'))

from werkzeug.security import generate_password_hash, check_password_hash

# Simulando banco de dados de usuários
users = {
    'Renata': generate_password_hash('1234')  # Armazenando a senha com hash
}

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Autenticação de usuário"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verificar se o usuário existe e se a senha está correta
        stored_password_hash = users.get(username)
        if stored_password_hash and check_password_hash(stored_password_hash, password):
            session['usuario'] = username
            session['nome_usuario'] = 'Administrador'
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('cadastro'))

        flash('Credenciais inválidas', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Encerra a sessão"""
    session.clear()
    flash('Logout realizado com sucesso', 'info')
    return redirect(url_for('login'))

# Rotas de Patrimônio
@app.route('/cadastro')
def cadastro():
    """Exibe formulário de cadastro"""
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    """Processa o cadastro de patrimônio"""
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Coleta dados do formulário
    dados = {
        'nome': request.form.get('nome', '').strip(),
        'descricao': request.form.get('descricao', '').strip(),
        'localizacao': request.form.get('localizacao', '').strip(),
        'condicao': request.form.get('condicao', '').strip(),
        'origem': request.form.get('origem', '').strip(),
        'marca': request.form.get('marca', '').strip(),
        'codigo_doador': request.form.get('codigo_doador', '').strip(),
        'codigo_cps': request.form.get('codigo_cps', '').strip(),
        'quantidade': request.form.get('quantidade', '1').strip()
    }

    # Validação básica
    if not all([dados['nome'], dados['descricao'], dados['localizacao'], dados['condicao'], dados['origem']]):
        flash('Preencha todos os campos obrigatórios', 'danger')
        return redirect(url_for('cadastro'))

    # Processa upload de imagem
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                dados['imagem'] = filename
            else:
                flash('Tipo de arquivo não permitido', 'danger')

    # Conexão com o banco
    conn = get_db_connection()
    if not conn:
        flash("Erro ao conectar ao banco de dados", "danger")
        return redirect(url_for('cadastro'))
    
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO patrimonio (
            nome, descricao, localizacao, condicao, origem,
            marca, codigo_doador, codigo_cps, quantidade, imagem,
            data_cadastro, usuario_cadastro
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """
        
        cursor.execute(query, (
            dados['nome'], dados['descricao'], dados['localizacao'],
            dados['condicao'], dados['origem'], dados['marca'],
            dados['codigo_doador'], dados['codigo_cps'],
            dados['quantidade'], dados.get('imagem'),
            session['nome_usuario']
        ))
        
        conn.commit()
        flash('Patrimônio cadastrado com sucesso!', 'success')
    except Error as e:
        conn.rollback()
        flash(f'Erro ao cadastrar: {str(e)}', 'danger')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('listar'))

@app.route('/listar')
def listar():
    """Lista todos os patrimônios"""
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash("Erro ao conectar ao banco de dados", 'danger')
        return render_template('listar.html', patrimonios=[], filtro={})
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Filtros
        filtro = request.args
        query = "SELECT * FROM patrimonio WHERE 1=1"
        params = []
        
        campos_validos = ['nome', 'descricao', 'localizacao', 'condicao', 'origem']
        for campo in campos_validos:
            if filtro.get(campo):
                query += f" AND {campo} LIKE %s"
                params.append(f"%{filtro[campo]}%")
        
        cursor.execute(query, params)
        patrimonios = cursor.fetchall()
        
        return render_template('listar.html', patrimonios=patrimonios, filtro=filtro)
    
    except Error as e:
        flash(f'Erro ao buscar dados: {str(e)}', 'danger')
        return render_template('listar.html', patrimonios=[], filtro={})
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/relatorio-pdf')
def gerar_relatorio_pdf():
    """Gera relatório em PDF"""
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash("Erro de conexão com o banco", 'danger')
        return redirect(url_for('listar'))

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT nome, descricao, localizacao, condicao, origem,
                   marca, codigo_doador, codigo_cps, quantidade,
                   DATE_FORMAT(data_cadastro, '%%d/%%m/%%Y') as data
            FROM patrimonio
        """)
        dados = cursor.fetchall()

        # Cria PDF em memória
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Configura elementos do PDF
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        elements.append(Paragraph("Relatório de Patrimônios", styles['Title']))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Paragraph(" ", styles['Normal']))  # Espaço

        # Tabela de dados
        tabela_dados = [['Nome', 'Localização', 'Condição', 'Quantidade']]
        for item in dados:
            tabela_dados.append([
                item['nome'],
                item['localizacao'],
                item['condicao'],
                str(item['quantidade'])
            ])

        # Estilo da tabela
        tabela = Table(tabela_dados, colWidths=[2*inch, 2*inch, 1.5*inch, 1*inch])
        estilo = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ])
        tabela.setStyle(estilo)
        elements.append(tabela)

        # Gera o PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Configura o download
        filename = f"relatorio_patrimonio_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('listar'))
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/imagens/<filename>')
def servir_imagem(filename):
    """Serve imagens do patrimônio"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Inicialização
if __name__ == '__main__':
    create_upload_folder()
    app.run(host='0.0.0.0', port=5000, debug=True)

