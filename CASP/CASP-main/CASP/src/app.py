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


app = Flask(__name__)
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

@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin123':
            session['usuario'] = username
            session['nome_usuario'] = 'Administrador'
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Credenciais inválidas', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso', 'info')
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
        
        # Total de patrimônios
        cursor.execute("SELECT COUNT(*) as total FROM patrimonio")
        total_patrimonios = cursor.fetchone()['total']
        
        # Distribuição por condição - CORRIGIDO
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
        
        # Debug: Verificar dados no console
        print("Condições encontradas:", condicoes)
        
        # Top localizações
        cursor.execute("SELECT localizacao, COUNT(*) as count FROM patrimonio GROUP BY localizacao ORDER BY count DESC LIMIT 5")
        localizacoes = cursor.fetchall()
        
        # Cadastros recentes (30 dias)
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

    # Coletar dados do formulário
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

    # Validar campos obrigatórios
    campos_obrigatorios = ['nome', 'descricao', 'localizacao', 'condicao', 'origem']
    for campo in campos_obrigatorios:
        if not dados[campo]:
            flash(f'Campo obrigatório não preenchido: {campo}', 'danger')
            return redirect(url_for('cadastro'))

    # Validar quantidade
    try:
        dados['quantidade'] = int(dados['quantidade'])
        if dados['quantidade'] <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
    except ValueError:
        flash('Quantidade deve ser um número válido maior que zero', 'danger')
        return redirect(url_for('cadastro'))

    # Processar imagem
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

    # Inserir no banco
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
            session['nome_usuario']
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


from flask import request, jsonify
import requests
import json

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'Mensagem vazia'}), 400
        
        ollama_url = "http://localhost:11434/api/chat"
        
        payload = {
            "model": "llama2",
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em gestão de patrimônio escolar. Ajude com questões sobre inventário, manutenção, cadastro e gestão de patrimônios. Seja útil, direto e objetivo em suas respostas. Responda em português."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "stream": False
        }
        
        response = requests.post(ollama_url, json=payload, timeout=30)
        response.raise_for_status()
        
        ai_response = response.json()
        return jsonify({
            'response': ai_response['message']['content']
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Serviço Ollama não está disponível'}), 503
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Tempo limite excedido'}), 408
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500

@app.route('/api/chat/status')
def chat_status():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = response.json().get('models', [])
        return jsonify({
            'status': 'online',
            'models': models
        })
    except Exception:
        return jsonify({'status': 'offline'}), 503


@app.route('/listar')
def listar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        return render_template('listar.html', patrimonios=[], filtro={})
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        filtro = request.args
        query = "SELECT * FROM patrimonio WHERE 1=1"
        params = []
        
        # Aplicar filtros
        if filtro.get('nome'):
            query += " AND nome LIKE %s"
            params.append(f"%{filtro['nome']}%")
            
        if filtro.get('localizacao'):
            query += " AND localizacao LIKE %s"
            params.append(f"%{filtro['localizacao']}%")
            
        if filtro.get('condicao'):
            query += " AND condicao = %s"
            params.append(filtro['condicao'])
            
        if filtro.get('origem'):
            query += " AND origem = %s"
            params.append(filtro['origem'])
        
        # Ordenação
        query += " ORDER BY data_cadastro DESC"
        
        cursor.execute(query, params)
        patrimonios = cursor.fetchall()
        
        return render_template('listar.html', patrimonios=patrimonios, filtro=filtro)
    
    except Error as e:
        flash(f'Erro ao buscar patrimônios: {str(e)}', 'danger')
        return render_template('listar.html', patrimonios=[], filtro={})
    
    finally:
        if conn.is_connected():
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
            # Coletar dados do formulário
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

            # Validar campos obrigatórios
            campos_obrigatorios = ['nome', 'localizacao', 'condicao', 'origem']
            for campo in campos_obrigatorios:
                if not dados[campo]:
                    flash(f'Campo obrigatório não preenchido: {campo}', 'danger')
                    return redirect(url_for('editar_patrimonio', id=id))

            # Validar quantidade
            try:
                dados['quantidade'] = int(dados['quantidade'])
                if dados['quantidade'] <= 0:
                    raise ValueError("Quantidade deve ser maior que zero")
            except ValueError:
                flash('Quantidade deve ser um número válido maior que zero', 'danger')
                return redirect(url_for('editar_patrimonio', id=id))

            # Processar nova imagem
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

            # Verificar se a tabela tem as colunas de atualização
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'patrimonio' 
                AND COLUMN_NAME IN ('data_atualizacao', 'usuario_atualizacao')
            """)
            colunas_existentes = [col['COLUMN_NAME'] for col in cursor.fetchall()]

            # Montar query de update dinamicamente
            campos_update = [
                "nome = %s", "descricao = %s", "localizacao = %s",
                "condicao = %s", "origem = %s", "marca = %s",
                "codigo_doador = %s", "codigo_cps = %s", "quantidade = %s"
            ]
            
            params = [
                dados['nome'], dados['descricao'], dados['localizacao'],
                dados['condicao'], dados['origem'], dados['marca'],
                dados['codigo_doador'], dados['codigo_cps'], dados['quantidade']
            ]

            # Adicionar imagem se fornecida
            if nova_imagem:
                campos_update.append("imagem = %s")
                params.append(nova_imagem)

            # Adicionar campos de atualização se existirem
            if 'data_atualizacao' in colunas_existentes:
                campos_update.append("data_atualizacao = NOW()")
            
            if 'usuario_atualizacao' in colunas_existentes:
                campos_update.append("usuario_atualizacao = %s")
                params.append(session['nome_usuario'])

            # Query final
            query = f"UPDATE patrimonio SET {', '.join(campos_update)} WHERE id = %s"
            params.append(id)

            cursor.execute(query, params)
            conn.commit()

            if cursor.rowcount > 0:
                flash('Patrimônio atualizado com sucesso!', 'success')
            else:
                flash('Nenhuma alteração foi realizada ou patrimônio não encontrado.', 'info')

            return redirect(url_for('listar'))

        else:
            # Carregar dados para edição (GET)
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

        # Criar PDF
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
        
        # Título
        elements.append(Paragraph("RELATÓRIO DE PATRIMÔNIOS", styles['Title']))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Tabela de dados
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
            
            # Ajustar largura das colunas
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
        # Ler arquivo
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # Validar colunas obrigatórias
        colunas_obrigatorias = ['nome', 'localizacao', 'condicao', 'quantidade']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltantes:
            flash(f'Colunas obrigatórias faltando: {", ".join(colunas_faltantes)}', 'danger')
            return redirect(url_for('importar_excel'))

        conn = get_db_connection()
        if not conn:
            flash('Erro de conexão com o banco', 'danger')
            return redirect(url_for('importar_excel'))

        cursor = conn.cursor()
        sucessos = 0
        erros = []

        for index, row in df.iterrows():
            try:
                # Preparar dados
                dados = {
                    'nome': str(row['nome']).strip(),
                    'localizacao': str(row['localizacao']).strip(),
                    'condicao': str(row['condicao']).strip(),
                    'quantidade': int(row['quantidade']),
                    'descricao': str(row['descricao']).strip() if 'descricao' in df.columns else '',
                    'origem': str(row['origem']).strip() if 'origem' in df.columns else 'Desconhecida',
                    'marca': str(row['marca']).strip() if 'marca' in df.columns else '',
                    'codigo_doador': str(row.get('codigo_doador', '')).strip(),
                    'codigo_cps': str(row.get('codigo_cps', '')).strip()
                }

                # Validar dados
                if not all([dados['nome'], dados['localizacao'], dados['condicao']]):
                    raise ValueError("Campos obrigatórios em branco")

                # Inserir no banco
                query = """
                INSERT INTO patrimonio (
                    nome, descricao, localizacao, condicao, origem, marca,
                    codigo_doador, codigo_cps, quantidade, data_cadastro, usuario_cadastro
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """
                
                cursor.execute(query, (
                    dados['nome'], dados['descricao'], dados['localizacao'],
                    dados['condicao'], dados['origem'], dados['marca'],
                    dados['codigo_doador'], dados['codigo_cps'],
                    dados['quantidade'], session['nome_usuario']
                ))
                
                sucessos += 1

            except Exception as e:
                erros.append(f"Linha {index + 2}: {str(e)}")

        conn.commit()
        
        if sucessos > 0:
            flash(f'Importação concluída! {sucessos} patrimônios importados com sucesso.', 'success')
        if erros:
            flash(f'Erros encontrados: {len(erros)} linhas não puderam ser importadas.', 'warning')

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
        
        return jsonify({
            'total': total,
            'condicoes': condicoes
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

# =============================================
# APIs PARA MOBILE
# =============================================

@app.route('/api/patrimonio/<codigo>')
def api_buscar_patrimonio(codigo):
    """API para buscar patrimônio por código CPS ou doador"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erro de conexão com o banco'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar por código CPS ou código doador
        cursor.execute("""
            SELECT 
                id, nome, descricao, localizacao, condicao, origem, 
                marca, codigo_doador, codigo_cps, quantidade,
                DATE_FORMAT(data_cadastro, '%%d/%%m/%%Y') as data_cadastro_formatada,
                usuario_cadastro
            FROM patrimonio 
            WHERE codigo_cps = %s OR codigo_doador = %s
            LIMIT 1
        """, (codigo, codigo))
        
        patrimonio = cursor.fetchone()
        
        if patrimonio:
            return jsonify({
                'success': True,
                'encontrado': True,
                'patrimonio': patrimonio,
                'mensagem': 'Patrimônio encontrado com sucesso'
            })
        else:
            return jsonify({
                'success': True,
                'encontrado': False,
                'patrimonio': None,
                'mensagem': 'Nenhum patrimônio encontrado com este código'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro na consulta: {str(e)}'
        }), 500
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/patrimonio/scan', methods=['POST'])
def api_scan_patrimonio():
    """API para scanear múltiplos códigos de uma vez"""
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
    """API para verificar status do servidor"""
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
    """Página mobile para consulta"""
    return render_template('mobile.html')

@app.route('/qrcode')
def qrcode_scanner():
    """Página com scanner de QR Code"""
    return render_template('qrcode.html')

if __name__ == '__main__':
    create_upload_folder()
    
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Conexão com o banco estabelecida!")
        test_conn.close()
    else:
        print("❌ Falha na conexão com o banco!")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
