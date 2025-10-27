from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from io import BytesIO
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import unicodedata
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import bcrypt
from functools import wraps


app = Flask(__name__,
           template_folder='SRC/templates',
           static_folder='SRC/static')

CORS(app)
app.secret_key = 'patrimonio_2024'


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'patrimonio'
}

print("=" * 60)
print("🚀 INICIANDO SISTEMA PATRIMÔNIO")
print("=" * 60)

GEMINI_API_KEY = None

if os.path.exists('chat.env'):
    load_dotenv('chat.env')
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    print("✅ chat.env carregado")
elif os.path.exists('.env'):
    load_dotenv('.env')
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    print("✅ .env carregado")
else:
    print("❌ Nenhum arquivo .env encontrado!")

if GEMINI_API_KEY and len(GEMINI_API_KEY) > 20:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"🚀 Gemini CONFIGURADO! Chave: {GEMINI_API_KEY[:10]}...")
else:
    print("❌ Gemini NÃO configurado - chave inválida")

print("=" * 60)

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Erro de conexão MySQL: {e}")
        flash("Erro ao conectar ao banco de dados", 'danger')
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_excel_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}

def create_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode
    ('utf-8'), salt)
    return hashed.decode('utf-8')

def requer_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('tipo_usuario') != 'admin':
            flash('Acesso restrito para administradores!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Erro na verificação de senha: {e}")
        return False

def criar_resposta_gemini(mensagem_usuario):
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    if not GEMINI_API_KEY or len(GEMINI_API_KEY) < 20:
        return "🔧 Assistente não configurado. Configure a chave da API Gemini no arquivo .env"
    
    try:
        
        dados_patrimonio = buscar_dados_para_ia(mensagem_usuario)
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 800,
        }

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        prompt = f"""
        Você é um assistente especializado no sistema de Gestão de Patrimônio Escolar da ETEC Ilza Nascimento Pintus.

        CONTEXTO DO SISTEMA:
        - Cadastro de patrimônios com: nome, descrição, localização, condição, origem, marca, código doador (7 números), código CPS (7 números), quantidade
        - Condições possíveis: Ótimo, Bom, Recuperável, Péssimo
        - Funcionalidades: Cadastrar, Listar, Editar, Deletar, Relatório PDF, Importar Excel, Dashboard
        - Origem é sempre em MAIÚSCULAS sem acentos
        - Códigos devem ter exatamente 7 números

        DADOS ATUAIS DO BANCO DE DADOS:
        {dados_patrimonio}

        Seja útil, objetivo e responda em português de forma clara e direta.
        Use os dados acima para responder perguntas específicas sobre patrimônios.

         **INSTRUÇÕES DE FORMATAÇÃO:**
        - Use negrito para títulos e informações importantes
        - Use quebras de linha entre parágrafos constantemente
        - Use emojis relevantes (🏢, 📊, 🔍, 📝, etc.)
        - Use listas com marcadores (•) para enumerar itens
        - Seja claro, objetivo e organizado

        PERGUNTA DO USUÁRIO: {mensagem_usuario}


        RESPOSTA FORMATADA:
        """

        response = model.generate_content(prompt)
        
       
        resposta_formatada = formatar_resposta_ia(response.text.strip())
        return resposta_formatada

    except Exception as e:
        print(f"Erro no Gemini: {e}")
        return "🤖 Estou com instabilidade no momento. Posso ajudar com: cadastro de patrimônios, relatórios PDF, importação Excel, condições (Ótimo, Bom, Recuperável, Péssimo) e códigos de 7 números."


def formatar_resposta_ia(resposta):
    """
    Versão simples para formatar respostas
    """
    # Substituições básicas
    substituicoes = {
        '**': '<strong>',
        '*': '<em>',
        '\n\n': '</p><p>',
        '\n': '<br>',
        '• ': '<li>',
        ' - ': '<li>'
    }
    
    for antigo, novo in substituicoes.items():
        resposta = resposta.replace(antigo, novo)
    
    # Fechar tags de lista
    resposta = resposta.replace('<li>', '<li>')
    
    return f'<p>{resposta}</p>'

def buscar_dados_para_ia(pergunta):
    """
    Busca dados relevantes do banco baseado na pergunta do usuário
    """
    conn = get_db_connection()
    if not conn:
        return "❌ *Erro de conexão com o banco de dados*"
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        pergunta_lower = pergunta.lower()
        
        # Análise da pergunta para decidir quais dados buscar
        if any(palavra in pergunta_lower for palavra in ['quantos', 'total', 'quantidade', 'contar', 'número']):
            # Buscar estatísticas
            cursor.execute("SELECT COUNT(*) as total FROM patrimonio")
            total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT condicao, COUNT(*) as count 
                FROM patrimonio 
                GROUP BY condicao
            """)
            condicoes = cursor.fetchall()
            
            return f"""
            📊 **ESTATÍSTICAS GERAIS**
            
            • **Total de patrimônios:** {total}
            • **Distribuição por condição:**
               - Ótimo: {next((c['count'] for c in condicoes if c['condicao'] == 'Ótimo'), 0)}
               - Bom: {next((c['count'] for c in condicoes if c['condicao'] == 'Bom'), 0)}
               - Recuperável: {next((c['count'] for c in condicoes if c['condicao'] == 'Recuperável'), 0)}
               - Péssimo: {next((c['count'] for c in condicoes if c['condicao'] == 'Péssimo'), 0)}
            """
        
        elif any(palavra in pergunta_lower for palavra in ['localização', 'localizacao', 'sala', 'laboratório', 'laboratorio']):
            # Buscar por localização
            cursor.execute("""
                SELECT nome, localizacao, condicao, quantidade 
                FROM patrimonio 
                ORDER BY localizacao, nome
                LIMIT 50
            """)
            patrimonios = cursor.fetchall()
            
            return f"""
            PATRIMÔNIOS POR LOCALIZAÇÃO (primeiros 50):
            {[f"{p['localizacao']} - {p['nome']} ({p['condicao']}) - Qtd: {p['quantidade']}" for p in patrimonios]}
            """
        
        elif any(palavra in pergunta_lower for palavra in ['condição', 'condicao', 'estado', 'conservação']):
            # Buscar por condição
            cursor.execute("""
                SELECT nome, condicao, localizacao 
                FROM patrimonio 
                ORDER BY condicao, nome
                LIMIT 50
            """)
            patrimonios = cursor.fetchall()
            
            return f"""
            PATRIMÔNIOS POR CONDIÇÃO (primeiros 50):
            {[f"{p['condicao']} - {p['nome']} - Local: {p['localizacao']}" for p in patrimonios]}
            """
        
        elif any(palavra in pergunta_lower for palavra in ['todos', 'listar', 'mostrar', 'patrimônios']):
            # Buscar todos os patrimônios (limitado)
            cursor.execute("""
                SELECT nome, descricao, localizacao, condicao, origem, quantidade 
                FROM patrimonio 
                ORDER BY nome
                LIMIT 30
            """)
            patrimonios = cursor.fetchall()
            
            return f"""
            LISTA DE PATRIMÔNIOS (primeiros 30):
            {[f"{p['nome']} - {p['localizacao']} - {p['condicao']} - Qtd: {p['quantidade']}" for p in patrimonios]}
            """
        
        else:
            # Buscar dados gerais para contexto
            cursor.execute("SELECT COUNT(*) as total FROM patrimonio")
            total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT nome, localizacao, condicao 
                FROM patrimonio 
                ORDER BY data_cadastro DESC 
                LIMIT 10
            """)
            recentes = cursor.fetchall()
            
            return f"""
            CONTEXTO GERAL:
            - Total de patrimônios no sistema: {total}
            - Patrimônios recentes: {[f"{r['nome']} ({r['localizacao']}) - {r['condicao']}" for r in recentes]}
            """
    
    except Exception as e:
        print(f"Erro ao buscar dados para IA: {e}")
        return f"Erro ao acessar banco de dados: {str(e)}"
    
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def criar_usuario_admin():
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            )
        """)
        
        admin_password = hash_password('admin123')
        
        cursor.execute("""
            INSERT IGNORE INTO usuarios (username, password_hash, ativo) 
            VALUES (%s, %s, %s)
        """, ('admin', admin_password, True))
        
        conn.commit()
        print("✅ Tabela de usuários criada e admin configurado!")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário admin: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Mudei para 'username' para não conflitar
        password = request.form.get('password')
        tipo = request.form.get('tipo')
        
        if tipo == 'convidado':
            # Login como convidado
            session['usuario'] = 'Convidado'
            session['tipo_usuario'] = 'convidado'
            flash('Entrou como convidado. Acesso apenas para visualização.', 'info')
            return redirect(url_for('dashboard'))
        
        elif tipo == 'admin':
            # Login como admin - usando mysql-connector em vez de SQLAlchemy
            conn = get_db_connection()
            if not conn:
                flash('Erro de conexão com o banco', 'danger')
                return render_template('login.html')
            
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM usuarios WHERE username = %s AND ativo = TRUE", (username,))
                usuario_db = cursor.fetchone()
                
                if usuario_db and check_password(password, usuario_db['password_hash']):
                    session['usuario'] = usuario_db['username']
                    session['user_id'] = usuario_db['id']
                    
                    flash(f'Login realizado com sucesso! Bem-vindo, {usuario_db["username"]}', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Credenciais inválidas', 'danger')
                
            except Exception as e:
                flash(f'Erro no login: {str(e)}', 'danger')
            finally:
                if conn and conn.is_connected():
                    cursor.close()
                    conn.close()
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('dashboard.html', stats={})
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total FROM patrimonio")
        total_patrimonios = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN LOWER(condicao) LIKE '%ótimo%' OR LOWER(condicao) LIKE '%otimo%' THEN 'Ótimo'
                    WHEN LOWER(condicao) LIKE '%bom%' THEN 'Bom'
                    WHEN LOWER(condicao) LIKE '%recuperável%' OR LOWER(condicao) LIKE '%recuperavel%' THEN 'Recuperável'
                    WHEN LOWER(condicao) LIKE '%péssimo%' OR LOWER(condicao) LIKE '%pessimo%' THEN 'Péssimo'
                    ELSE condicao
                END as condicao_normalizada,
                COUNT(*) as count 
            FROM patrimonio 
            GROUP BY condicao_normalizada
        """)
        condicoes = cursor.fetchall()
        
        cursor.execute("SELECT localizacao, COUNT(*) as count FROM patrimonio GROUP BY localizacao ORDER BY count DESC LIMIT 5")
        localizacoes = cursor.fetchall()
        
        cursor.execute("""
            SELECT DATE(data_cadastro) as data, COUNT(*) as count 
            FROM patrimonio 
            WHERE data_cadastro >= DATE_SUB(NOW(), INTERVAL 30 DAY) 
            GROUP BY DATE(data_cadastro) 
            ORDER BY data
        """)
        cadastros_recentes = cursor.fetchall()
        
        stats = {
            'total_patrimonios': total_patrimonios,
            'condicoes': condicoes,
            'localizacoes': localizacoes,
            'cadastros_recentes': cadastros_recentes
        }
        
        return render_template('dashboard.html', stats=stats)
    
    except Error as e:
        print(f"Erro no dashboard: {e}")
        flash(f'Erro ao carregar estatísticas: {str(e)}', 'danger')
        return render_template('dashboard.html', stats={})
    
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/cadastro')
def cadastro():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

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

    campos_obrigatorios = ['nome', 'localizacao', 'condicao', 'origem']
    for campo in campos_obrigatorios:
        if not dados[campo]:
            flash(f'Campo obrigatório não preenchido: {campo}', 'danger')
            return redirect(url_for('cadastro'))

    try:
        dados['quantidade'] = int(dados['quantidade'])
        if dados['quantidade'] <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
    except ValueError:
        flash('Quantidade deve ser um número válido maior que zero', 'danger')
        return redirect(url_for('cadastro'))

    dados['origem'] = dados['origem'].upper()
    dados['origem'] = ''.join(
        c for c in unicodedata.normalize('NFD', dados['origem'])
        if unicodedata.category(c) != 'Mn'
    )

    if dados['codigo_doador']:
        if not dados['codigo_doador'].isdigit() or len(dados['codigo_doador']) != 7:
            flash('Código do Doador deve conter exatamente 7 números', 'danger')
            return redirect(url_for('cadastro'))

    if dados['codigo_cps']:
        if not dados['codigo_cps'].isdigit() or len(dados['codigo_cps']) != 7:
            flash('Código CPS deve conter exatamente 7 números', 'danger')
            return redirect(url_for('cadastro'))

    dados['imagem'] = None
    if 'imagem' in request.files:
        file = request.files['imagem']
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                dados['imagem'] = filename
            else:
                flash('Tipo de arquivo não permitido. Use PNG, JPG, JPEG, GIF ou WEBP', 'danger')
                return redirect(url_for('cadastro'))

    conn = get_db_connection()
    if not conn:
        flash('Erro de conexão com o banco de dados', 'danger')
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
            dados['quantidade'], dados['imagem'],
            session['usuario']
        ))
        
        conn.commit()
        flash('Patrimônio cadastrado com sucesso!', 'success')
        
    except Error as e:
        conn.rollback()
        flash(f'Erro ao cadastrar patrimônio: {str(e)}', 'danger')
        
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('listar'))

@app.route('/listar')
def listar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Capturar parâmetros de filtro da URL
    filtro = {
        'nome': request.args.get('nome', '').strip(),
        'localizacao': request.args.get('localizacao', '').strip(),
        'codigo_cps': request.args.get('codigo_cps', '').strip(),
        'codigo_doador': request.args.get('codigo_doador', '').strip(),
        'condicao': request.args.get('condicao', '').strip(),
        'origem': request.args.get('origem', '').strip()
    }
    
    conn = get_db_connection()
    if not conn:
        flash("Erro de conexão com o banco", 'danger')
        return render_template('listar.html', patrimonios=[], filtro=filtro)
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Query base
        query = """
            SELECT 
                id, nome, descricao, localizacao, condicao, origem,
                marca, codigo_doador, codigo_cps, quantidade, imagem,
                DATE_FORMAT(data_cadastro, '%d/%m/%Y %H:%i') as data_cadastro_formatada,
                usuario_cadastro
            FROM patrimonio 
            WHERE 1=1
        """
        params = []
        
        # Aplicar filtros
        if filtro['nome']:
            query += " AND nome LIKE %s"
            params.append(f"%{filtro['nome']}%")
        
        if filtro['localizacao']:
            query += " AND localizacao LIKE %s"
            params.append(f"%{filtro['localizacao']}%")
        
        if filtro['codigo_cps']:
            query += " AND codigo_cps = %s"
            params.append(filtro['codigo_cps'])
        
        if filtro['codigo_doador']:
            query += " AND codigo_doador = %s"
            params.append(filtro['codigo_doador'])
        
        # Filtro de condição - suporta múltiplas condições separadas por vírgula
        if filtro['condicao']:
            condicoes = [cond.strip() for cond in filtro['condicao'].split(',')]
            placeholders = ','.join(['%s'] * len(condicoes))
            query += f" AND condicao IN ({placeholders})"
            params.extend(condicoes)
        
        if filtro['origem']:
            query += " AND origem = %s"
            params.append(filtro['origem'])
        
        # Ordenação
        query += " ORDER BY data_cadastro DESC"
        
        cursor.execute(query, params)
        patrimonios = cursor.fetchall()
        
        # Adicionar mensagem informativa sobre o filtro
        if filtro['condicao']:
            condicoes_filtro = [cond.strip() for cond in filtro['condicao'].split(',')]
            if len(condicoes_filtro) > 1:
                flash(f'Mostrando patrimônios em condições: {", ".join(condicoes_filtro)}', 'info')
            else:
                flash(f'Mostrando patrimônios em condição: {condicoes_filtro[0]}', 'info')
        
        return render_template('listar.html', patrimonios=patrimonios, filtro=filtro)
        
    except Exception as e:
        flash(f'Erro ao carregar patrimônios: {str(e)}', 'danger')
        return render_template('listar.html', patrimonios=[], filtro=filtro)
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_patrimonio(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash("Erro de conexão com o banco", 'danger')
        return redirect(url_for('listar'))

    try:
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            dados = {
                'nome': request.form.get('nome', '').strip(),
                'descricao': request.form.get('descricao', '').strip(),
                'localizacao': request.form.get('localizacao', '').strip(),
                'condicao': request.form.get('condicao', '').strip(),
                'origem': request.form.get('origem', '').strip(),
                'marca': request.form.get('marca', '').strip(),
                'codigo_doador': request.form.get('codigo_doador', '').strip(),
                'codigo_cps': request.form.get('codigo_cps', '').strip(),
                'quantidade': request.form.get('quantidade', '1').strip(),
                'id': id
            }

            campos_obrigatorios = ['nome', 'localizacao', 'condicao', 'origem']
            for campo in campos_obrigatorios:
                if not dados[campo]:
                    flash(f'Campo obrigatório não preenchido: {campo}', 'danger')
                    return redirect(url_for('editar_patrimonio', id=id))

            try:
                dados['quantidade'] = int(dados['quantidade'])
                if dados['quantidade'] <= 0:
                    raise ValueError("Quantidade deve ser maior que zero")
            except ValueError:
                flash('Quantidade deve ser um número válido maior que zero', 'danger')
                return redirect(url_for('editar_patrimonio', id=id))

            dados['origem'] = dados['origem'].upper()
            dados['origem'] = ''.join(
                c for c in unicodedata.normalize('NFD', dados['origem'])
                if unicodedata.category(c) != 'Mn'
            )

            if dados['codigo_doador']:
                if not dados['codigo_doador'].isdigit() or len(dados['codigo_doador']) != 7:
                    flash('Código do Doador deve conter exatamente 7 números', 'danger')
                    return redirect(url_for('editar_patrimonio', id=id))

            if dados['codigo_cps']:
                if not dados['codigo_cps'].isdigit() or len(dados['codigo_cps']) != 7:
                    flash('Código CPS deve conter exatamente 7 números', 'danger')
                    return redirect(url_for('editar_patrimonio', id=id))

            nova_imagem = None
            if 'imagem' in request.files:
                file = request.files['imagem']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + filename
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        nova_imagem = filename
                    else:
                        flash('Tipo de arquivo não permitido', 'danger')
                        return redirect(url_for('editar_patrimonio', id=id))

            query = """
            UPDATE patrimonio SET 
                nome = %s, descricao = %s, localizacao = %s, condicao = %s, 
                origem = %s, marca = %s, codigo_doador = %s, codigo_cps = %s, 
                quantidade = %s, usuario_cadastro = %s
            """
            params = [
                dados['nome'], dados['descricao'], dados['localizacao'],
                dados['condicao'], dados['origem'], dados['marca'],
                dados['codigo_doador'], dados['codigo_cps'], dados['quantidade'],
                session['usuario']
            ]

            if nova_imagem:
                query += ", imagem = %s"
                params.append(nova_imagem)

            query += " WHERE id = %s"
            params.append(id)

            cursor.execute(query, params)
            conn.commit()

            if cursor.rowcount > 0:
                flash('Patrimônio atualizado com sucesso!', 'success')
            else:
                flash('Nenhuma alteração foi realizada ou patrimônio não encontrado.', 'info')

            return redirect(url_for('listar'))

        else:
            cursor.execute("SELECT * FROM patrimonio WHERE id = %s", (id,))
            patrimonio = cursor.fetchone()

            if not patrimonio:
                flash('Patrimônio não encontrado', 'danger')
                return redirect(url_for('listar'))

            return render_template('editar.html', patrimonio=patrimonio)

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Erro ao editar patrimônio: {str(e)}', 'danger')
        return redirect(url_for('listar'))
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/relatorio-pdf')
def gerar_relatorio_pdf():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        if not conn:
            flash("Erro de conexão com o banco", 'danger')
            return redirect(url_for('listar'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""  
            SELECT nome, descricao, localizacao, condicao, quantidade, marca, origem
            FROM patrimonio
            ORDER BY localizacao, nome
        """)
        dados = cursor.fetchall()

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph("RELATÓRIO DE PATRIMÔNIOS", styles['Title']))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        tabela_dados = [['Nome', 'Localização', 'Condição', 'Qtd', 'Marca', 'Origem']]
        
        for item in dados:
            tabela_dados.append([
                item['nome'][:30] + '...' if len(item['nome']) > 30 else item['nome'],
                item['localizacao'],
                item['condicao'],
                str(item['quantidade']),
                item['marca'] or '-',
                item['origem']
            ])

        tabela = Table(tabela_dados, colWidths=[200, 100, 80, 50, 100, 100])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('ALIGN', (0,1), (-1,-1), 'LEFT'),
            ('ALIGN', (3,1), (3,-1), 'CENTER'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        
        elements.append(tabela)
        doc.build(elements)
        buffer.seek(0)
        
        filename = f"relatorio_patrimonio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename)
        
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('listar'))
        
    finally:
        if 'cursor' in locals(): cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/exportar-excel')
def exportar_excel():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        if not conn:
            flash("Erro de conexão com o banco", 'danger')
            return redirect(url_for('listar'))
        
        query = """
        SELECT nome, descricao, localizacao, condicao, origem, marca, 
               codigo_doador, codigo_cps, quantidade, 
               DATE_FORMAT(data_cadastro, '%d/%m/%Y %H:%i') as data_cadastro, 
               usuario_cadastro
        FROM patrimonio 
        ORDER BY data_cadastro DESC
        """
        
        df = pd.read_sql(query, conn)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Patrimônios', index=False)
            
            worksheet = writer.sheets['Patrimônios']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
        
        output.seek(0)
        filename = f"patrimonios_exportados_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename)
        
    except Exception as e:
        flash(f'Erro ao exportar Excel: {str(e)}', 'danger')
        return redirect(url_for('listar'))
        
    finally:
        if conn and conn.is_connected():
            conn.close()

def extrair_dados_linha(row, sheet_name, origem_padrao):
    dados = {
        'nome': '',
        'descricao': '',
        'localizacao': sheet_name,
        'condicao': 'Bom',
        'origem': origem_padrao,
        'marca': '',
        'codigo_doador': '',
        'codigo_cps': '',
        'quantidade': 1
    }
    
    for col_name, cell_value in row.items():
        if pd.isna(cell_value):
            continue
            
        str_value = str(cell_value).strip()
        col_lower = str(col_name).lower()
        
        if any(keyword in col_lower for keyword in ['patrimonio', 'número', 'numero', 'código', 'codigo']):
            if str_value.isdigit() and len(str_value) == 7:
                if not dados['codigo_doador']:
                    dados['codigo_doador'] = str_value
                elif not dados['codigo_cps']:
                    dados['codigo_cps'] = str_value
        
        elif any(keyword in col_lower for keyword in ['descrição', 'descricao', 'nome']):
            if not dados['nome']:
                dados['nome'] = str_value
            elif not dados['descricao']:
                dados['descricao'] = str_value
        
        elif 'marca' in col_lower:
            dados['marca'] = str_value
        
        elif 'local' in col_lower and str_value and str_value != sheet_name:
            dados['localizacao'] = str_value
        
        elif any(keyword in col_lower for keyword in ['condição', 'condicao', 'condições']):
            dados['condicao'] = str_value
        
        elif 'doador' in col_lower and str_value.isdigit() and len(str_value) == 7:
            dados['codigo_doador'] = str_value
    
    if not dados['nome'] and dados['descricao']:
        dados['nome'] = dados['descricao'][:100]
    
    if "não patrimoniado" in dados['nome'].lower() or "itens não" in dados['nome'].lower():
        dados['nome'] = dados['nome'].replace("ITENS NÃO PATRIMONIADOS", "").replace("NÃO PATRIMONIADOS", "").strip()
    
    dados['origem'] = dados['origem'].upper()
    
    return dados

def normalizar_condicao(condicao):
    condicao_lower = str(condicao).lower().strip()
    
    if any(palavra in condicao_lower for palavra in ['ótimo', 'otimo', 'excelente', 'novo']):
        return 'Ótimo'
    elif any(palavra in condicao_lower for palavra in ['bom', 'boa', 'regular']):
        return 'Bom'
    elif any(palavra in condicao_lower for palavra in ['recuperável', 'recuperavel', 'recuperacao', 'conserto']):
        return 'Recuperável'
    elif any(palavra in condicao_lower for palavra in ['péssimo', 'pessimo', 'ruim', 'inutilizavel']):
        return 'Péssimo'
    else:
        return 'Bom'

@app.route('/importar-excel', methods=['GET', 'POST'])
def importar_excel():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('importar_excel.html')

    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('importar_excel'))

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('importar_excel'))

    if not allowed_excel_file(file.filename):
        flash('Tipo de arquivo não permitido. Use XLSX, XLS ou CSV', 'danger')
        return redirect(url_for('importar_excel'))

    try:
        origem_padrao = request.form.get('defaultOrigin', 'GOVERNO ESTADUAL').strip().upper()
        
        if file.filename.endswith('.csv'):
            dfs = {'Dados': pd.read_csv(file)}
        else:
            xls = pd.ExcelFile(file)
            dfs = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names}
        
        conn = get_db_connection()
        if not conn:
            flash('Erro de conexão com o banco', 'danger')
            return redirect(url_for('importar_excel'))

        cursor = conn.cursor()
        total_sucessos = 0
        total_erros = []
        abas_processadas = []

        for sheet_name, df in dfs.items():
            if df.empty:
                continue
                
            sucessos_aba = 0
            erros_aba = []
            
            df = df.dropna(how='all')
            df = df.reset_index(drop=True)
            
            for index, row in df.iterrows():
                try:
                    dados = extrair_dados_linha(row, sheet_name, origem_padrao)
                    
                    if not dados['nome'] or not dados['localizacao']:
                        continue
                    
                    if dados['codigo_doador'] and (len(dados['codigo_doador']) != 7 or not dados['codigo_doador'].isdigit()):
                        dados['codigo_doador'] = ''
                    
                    if dados['codigo_cps'] and (len(dados['codigo_cps']) != 7 or not dados['codigo_cps'].isdigit()):
                        dados['codigo_cps'] = ''
                    
                    condicao_normalizada = normalizar_condicao(dados['condicao'])
                    
                    query = """
                    INSERT INTO patrimonio (
                        nome, descricao, localizacao, condicao, origem, marca,
                        codigo_doador, codigo_cps, quantidade, data_cadastro, usuario_cadastro
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                    """
                    
                    cursor.execute(query, (
                        dados['nome'], dados['descricao'], dados['localizacao'],
                        condicao_normalizada, dados['origem'], dados['marca'],
                        dados['codigo_doador'], dados['codigo_cps'],
                        dados['quantidade'], session['usuario']
                    ))
                    
                    sucessos_aba += 1
                    
                except Exception as e:
                    erros_aba.append(f"Aba {sheet_name}, Linha {index + 2}: {str(e)}")
            
            if sucessos_aba > 0:
                abas_processadas.append(f"{sheet_name} ({sucessos_aba} itens)")
                total_sucessos += sucessos_aba
            
            total_erros.extend(erros_aba)
        
        conn.commit()
        
        if total_sucessos > 0:
            mensagem = f'Importação concluída! {total_sucessos} patrimônios importados de {len(abas_processadas)} abas.'
            if abas_processadas:
                mensagem += f' Abas: {", ".join(abas_processadas)}'
            flash(mensagem, 'success')
        
        if total_erros:
            flash(f'Erros encontrados: {len(total_erros)} linhas não importadas.', 'warning')
        
        return redirect(url_for('listar'))

    except Exception as e:
        flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
        return redirect(url_for('importar_excel'))
        
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/imagens/<filename>')
def servir_imagem(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/stats')
def api_stats():
    if 'usuario' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erro de conexão'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total FROM patrimonio")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT condicao, COUNT(*) as count FROM patrimonio GROUP BY condicao")
        condicoes = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(DISTINCT localizacao) as total_localizacoes FROM patrimonio")
        total_localizacoes = cursor.fetchone()['total_localizacoes']
        
        cursor.execute("SELECT localizacao, COUNT(*) as count FROM patrimonio GROUP BY localizacao ORDER BY count DESC LIMIT 5")
        localizacoes = cursor.fetchall()
        
        return jsonify({
            'total': total,
            'condicoes': condicoes,
            'total_localizacoes': total_localizacoes,
            'localizacoes': localizacoes
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/health")
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route('/api/patrimonios')
def api_patrimonios():
    if 'usuario' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erro de conexão'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, localizacao, condicao, origem, quantidade
            FROM patrimonio 
            ORDER BY nome
        """)
        patrimonios = cursor.fetchall()
        
        return jsonify(patrimonios)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/patrimonio/scan', methods=['POST'])
def api_scan_patrimonio():
    try:
        data = request.get_json()
        if not data or 'codigos' not in data:
            return jsonify({'error': 'Lista de códigos necessária'}), 400
        
        codigos = data['codigos']
        resultados = []
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erro de conexão'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        for codigo in codigos:
            cursor.execute("""
                SELECT nome, localizacao, condicao, origem, codigo_cps, codigo_doador
                FROM patrimonio 
                WHERE codigo_cps = %s OR codigo_doador = %s
                LIMIT 1
            """, (codigo, codigo))
            
            patrimonio = cursor.fetchone()
            resultados.append({
                'codigo': codigo,
                'encontrado': patrimonio is not None,
                'patrimonio': patrimonio
            })
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'total': len(resultados),
            'encontrados': sum(1 for r in resultados if r['encontrado'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/status')
def api_status():
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            return jsonify({
                'status': 'online',
                'mensagem': 'Sistema funcionando normalmente',
                'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            })
        else:
            return jsonify({'status': 'error', 'mensagem': 'Erro no banco'}), 500
    except:
        return jsonify({'status': 'error', 'mensagem': 'Erro de conexão'}), 500



@app.route('/mobile')
@app.route('/app')
def mobile_app():
    return render_template('mobile.html')

@app.route('/api/mobile/status')
def mobile_api_status():
    from datetime import datetime
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'version': '1.0.0'
    })

@app.route('/api/mobile/patrimonio/<codigo>')
def mobile_consultar_patrimonio(codigo):
    conn = get_db_connection()
    if not conn:
        return jsonify({
            'success': False,
            'error': 'Erro de conexão com o banco'
        }), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar por código CPS ou código doador
        cursor.execute("""
            SELECT 
                nome, descricao, localizacao, condicao, origem, 
                marca, codigo_doador, codigo_cps, quantidade,
                DATE_FORMAT(data_cadastro, '%d/%m/%Y') as data_cadastro_formatada
            FROM patrimonio 
            WHERE codigo_cps = %s OR codigo_doador = %s
            LIMIT 1
        """, (codigo, codigo))
        
        patrimonio = cursor.fetchone()
        
        if patrimonio:
            return jsonify({
                'success': True,
                'encontrado': True,
                'patrimonio': {
                    'nome': patrimonio['nome'] or '',
                    'descricao': patrimonio['descricao'] or '',
                    'localizacao': patrimonio['localizacao'] or '',
                    'condicao': patrimonio['condicao'] or '',
                    'origem': patrimonio['origem'] or '',
                    'quantidade': patrimonio['quantidade'] or 1,
                    'marca': patrimonio['marca'] or '',
                    'codigo_cps': patrimonio['codigo_cps'] or '',
                    'codigo_doador': patrimonio['codigo_doador'] or '',
                    'data_cadastro_formatada': patrimonio['data_cadastro_formatada'] or ''
                }
            })
        else:
            return jsonify({
                'success': True,
                'encontrado': False,
                'mensagem': 'Nenhum patrimônio encontrado com este código'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    

@app.route('/alterar', methods=['GET', 'POST'])
def alterar_senha():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if nova_senha != confirmar_senha:
            flash('As novas senhas não coincidem', 'danger')
            return render_template('alterar_senha.html')
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT password_hash FROM usuarios WHERE username = %s", (session['usuario'],))
            usuario = cursor.fetchone()
            
            if usuario and check_password(senha_atual, usuario['password_hash']):
                nova_senha_hash = hash_password(nova_senha)
                cursor.execute("UPDATE usuarios SET password_hash = %s WHERE username = %s", 
                             (nova_senha_hash, session['usuario']))
                conn.commit()
                flash('Senha alterada com sucesso!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Senha atual incorreta', 'danger')
                
        except Exception as e:
            flash(f'Erro ao alterar senha: {str(e)}', 'danger')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('alterar_senha.html')

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Mensagem vazia'}), 400

        resposta = criar_resposta_gemini(user_message)
        
        return jsonify({
            'response': resposta,
            'type': 'gemini',
            'source': 'Google Gemini Flash'
        })

    except Exception as e:
        print(f"Erro no chat: {e}")
        return jsonify({
            'response': '🔧 Estou com dificuldades técnicas. Posso ajudar com: como cadastrar patrimônio, gerar relatórios PDF, importar dados do Excel ou ver a lista de patrimônios.',
            'type': 'error_fallback'
        })

@app.route('/api/chat/status')
def chat_status():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and len(api_key) > 20:
        return jsonify({
            'status': 'online',
            'type': 'google_gemini',
            'model': 'Gemini 2.5 Flash',  
            'features': ['IA Gratuita', 'Contexto Patrimonial', 'Respostas Naturais']
        })
    else:
        return jsonify({
            'status': 'offline',
            'type': 'google_gemini',
            'model': 'Gemini 2.5 Flash', 
            'features': ['IA Gratuita', 'Contexto Patrimonial', 'Respostas Naturais']
        })


if __name__ == '__main__':
    create_upload_folder()
    criar_usuario_admin()
    
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Conexão com o banco estabelecida!")
        test_conn.close()
    else:
        print("❌ Falha na conexão com o banco!")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
