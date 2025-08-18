from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory
from werkzeug.utils import secure_filename
from io import BytesIO
import os
from datetime import datetime
import csv
import mysql.connector
from mysql.connector import Error

# Importações do ReportLab (adicionar estas)
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
        flash("Erro ao conectar ao banco de dados", 'danger')
    return None

def allowed_file(filename):
    """Verifica extensões permitidas"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Autenticação de usuário"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Autenticação simples (substitua por consulta ao banco)
        if username == 'admin' and password == 'admin123':
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

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

# ... (mantenha as outras importações e configurações existentes)




@app.route('/relatorio-pdf')
def gerar_relatorio_pdf():
    """Gera relatório em PDF com layout otimizado"""
    if 'usuario' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        if not conn:
            flash("Erro de conexão com o banco", 'danger')
            return redirect(url_for('listar'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""  
            SELECT nome, localizacao, condicao, quantidade
            FROM patrimonio
            ORDER BY localizacao, nome
        """)
        dados = cursor.fetchall()

        # Configurações do PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),  # Usar orientação paisagem
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()

        
        
        # Estilo personalizado para texto longo
        long_text_style = ParagraphStyle(
            'long_text',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            spaceBefore=2,
            spaceAfter=2,
            wordWrap='CJK'  # Melhor quebra de palavras
        )
        
        # Título e cabeçalho
        elements.append(Paragraph("<b>Relatório de Patrimônios</b>", styles['Title']))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 12))  # Espaço
        
        # Preparar dados da tabela
        tabela_dados = [
            [
                Paragraph('<b>Nome</b>', styles['Normal']),
                Paragraph('<b>Localização</b>', styles['Normal']),
                Paragraph('<b>Condição</b>', styles['Normal']),
                Paragraph('<b>Quantidade</b>', styles['Normal'])
            ]
        ]
        
        # Processar cada item
        for item in dados:
            # Tratar nomes longos com quebra de linha
            nome = item['nome']
            if len(nome) > 60:  # Se for muito longo, dividir em partes
                parts = [nome[i:i+60] for i in range(0, len(nome), 60)]
                nome = '<br/>'.join(parts)
            
            tabela_dados.append([
                Paragraph(nome, long_text_style),
                Paragraph(item['localizacao'], long_text_style),
                Paragraph(item['condicao'], long_text_style),
                Paragraph(str(item['quantidade']), long_text_style)
            ])

        # Criar tabela com larguras proporcionais
        tabela = Table(
            tabela_dados,
            colWidths=[doc.width*0.55, doc.width*0.20, doc.width*0.15, doc.width*0.10],
            repeatRows=1  # Repetir cabeçalho em cada página
        )
        
        # Estilo avançado para a tabela
        estilo = TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            
            # Alinhamento dos dados
            ('ALIGN', (0,1), (-1,-1), 'LEFT'),
            ('ALIGN', (3,1), (3,-1), 'CENTER'),  # Quantidade centralizada
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            
            # Bordas e grid
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            
            # Quebra de texto
            ('WORDWRAP', (0,0), (-1,-1), True),
            
            # Padding para melhor legibilidade
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ])
        
        # Zebrado para melhor legibilidade
        for i in range(1, len(tabela_dados)):
            if i % 2 == 1:
                estilo.add('BACKGROUND', (0,i), (-1,i), colors.HexColor('#f8f8f8'))
        
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
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/imagens/<filename>')
def servir_imagem(filename):
    """Serve imagens do patrimônio"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

from flask import send_file
import pandas as pd
from io import BytesIO
import os

# ... (outras importações existentes)

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
            # Processar dados do formulário
            dados = {
                'nome': request.form.get('nome'),
                'descricao': request.form.get('descricao'),
                'localizacao': request.form.get('localizacao'),
                'condicao': request.form.get('condicao'),
                'origem': request.form.get('origem'),
                'marca': request.form.get('marca'),
                'codigo_doador': request.form.get('codigo_doador'),
                'codigo_cps': request.form.get('codigo_cps'),
                'quantidade': int(request.form.get('quantidade', 0)),  # Converter para int
                'id': id
            }

            # Verificar campos obrigatórios
            if not all([dados['nome'], dados['localizacao'], dados['condicao'], dados['origem']]) or dados['quantidade'] <= 0:
                flash('Preencha todos os campos obrigatórios corretamente', 'danger')
                return redirect(url_for('editar_patrimonio', id=id))

            # Processar upload de imagem
            filename = None
            if 'imagem' in request.files:
                file = request.files['imagem']
                if file and file.filename != '':
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    else:
                        flash('Tipo de arquivo não permitido', 'danger')
                        return redirect(url_for('editar_patrimonio', id=id))

            # Obter a imagem atual se existir
            cursor.execute("SELECT imagem FROM patrimonio WHERE id = %s", (id,))
            patrimonio_atual = cursor.fetchone()
            imagem_atual = patrimonio_atual['imagem'] if patrimonio_atual else None

            # Montar SQL
            query = """
                UPDATE patrimonio SET
                    nome = %s,
                    descricao = %s,
                    localizacao = %s,
                    condicao = %s,
                    origem = %s,
                    marca = %s,
                    codigo_doador = %s,
                    codigo_cps = %s,
                    quantidade = %s,
                    data_atualizacao = NOW(),
                    usuario_atualizacao = %s
            """

            params = [
                dados['nome'], dados['descricao'], dados['localizacao'],
                dados['condicao'], dados['origem'], dados['marca'],
                dados['codigo_doador'], dados['codigo_cps'],
                dados['quantidade'], session['nome_usuario']
            ]

            # Adicionar imagem se foi enviada nova
            if filename:
                query += ", imagem = %s"
                params.append(filename)
            elif imagem_atual:
                # Manter a imagem atual se não foi enviada nova
                query += ", imagem = %s"
                params.append(imagem_atual)

            query += " WHERE id = %s"
            params.append(id)

            cursor.execute(query, params)
            conn.commit()

            if cursor.rowcount > 0:
                flash('Patrimônio atualizado com sucesso!', 'success')
            else:
                flash('Nenhum patrimônio foi alterado. Verifique os dados.', 'warning')

            return redirect(url_for('listar'))

        else:
            # Método GET - mostrar formulário
            cursor.execute("SELECT * FROM patrimonio WHERE id = %s", (id,))
            patrimonio = cursor.fetchone()

            if not patrimonio:
                flash('Patrimônio não encontrado', 'danger')
                return redirect(url_for('listar'))

            return render_template('editar.html', patrimonio=patrimonio)

    except ValueError:
        flash('Quantidade deve ser um número válido', 'danger')
        return redirect(url_for('editar_patrimonio', id=id))
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao atualizar patrimônio: {str(e)}', 'danger')
        return redirect(url_for('listar'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/exportar-excel')
def exportar_excel():
    """Exporta os dados de patrimônio para Excel"""
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash("Erro ao conectar ao banco de dados", 'danger')
        return redirect(url_for('listar'))
    
    try:
        # Busca todos os patrimônios
        query = "SELECT * FROM patrimonio"
        df = pd.read_sql(query, conn)
        
        # Cria um arquivo Excel em memória
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, sheet_name='Patrimônios', index=False)
        writer.close()
        output.seek(0)
        
        # Configura o download
        filename = f"patrimonios_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'Erro ao exportar Excel: {str(e)}', 'danger')
        return redirect(url_for('listar'))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/importar-excel', methods=['GET', 'POST'])
def importar_excel():
    """Importa dados de patrimônio de arquivo Excel com organização igual ao PDF"""
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(request.url)
        
        if file and allowed_excel_file(file.filename):
            try:
                # Lê o arquivo Excel
                df = pd.read_excel(file)
                
                # Verifica as colunas necessárias (igual ao PDF)
                required_columns = ['nome', 'localizacao', 'condicao', 'quantidade']
                missing_cols = [col for col in required_columns if col not in df.columns]
                
                if missing_cols:
                    flash(f'Colunas obrigatórias faltando: {", ".join(missing_cols)}', 'danger')
                    return redirect(request.url)
                
                # Conecta ao banco
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Contadores para relatório
                total = 0
                sucesso = 0
                erros = []
                
                # Processa cada linha
                for idx, row in df.iterrows():
                    total += 1
                    try:
                        # Mapeia os campos conforme o PDF
                        dados = {
                            'nome': str(row['nome']).strip(),
                            'localizacao': str(row['localizacao']).strip(),
                            'condicao': str(row['condicao']).strip(),
                            'quantidade': int(row['quantidade']) if pd.notna(row['quantidade']) else 1,
                            'descricao': str(row['descricao']).strip() if 'descricao' in df.columns else '',
                            'origem': str(row['origem']).strip() if 'origem' in df.columns else 'Desconhecida',
                            'marca': str(row['marca']).strip() if 'marca' in df.columns else '',
                            'codigo_doador': str(row['codigo_doador']).strip() if 'codigo_doador' in df.columns else '',
                            'codigo_cps': str(row['codigo_cps']).strip() if 'codigo_cps' in df.columns else ''
                        }
                        
                        # Validação básica
                        if not dados['nome'] or not dados['localizacao'] or not dados['condicao']:
                            raise ValueError("Campos obrigatórios não preenchidos")
                            
                        # Insere no banco
                        cursor.execute("""
                            INSERT INTO patrimonio (
                                nome, descricao, localizacao, condicao, origem,
                                marca, codigo_doador, codigo_cps, quantidade,
                                usuario_cadastro, data_cadastro
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            dados['nome'], dados['descricao'], dados['localizacao'],
                            dados['condicao'], dados['origem'], dados['marca'],
                            dados['codigo_doador'], dados['codigo_cps'],
                            dados['quantidade'], session['nome_usuario']
                        ))
                        sucesso += 1
                        
                    except Exception as e:
                        erros.append(f"Linha {idx+2}: {str(e)}")
                
                conn.commit()
                
                # Mensagem de resultado
                msg = f"Importação concluída: {sucesso}/{total} itens importados"
                if erros:
                    msg += f". Erros: {', '.join(erros[:3])}"  # Mostra apenas os 3 primeiros erros
                    if len(erros) > 3:
                        msg += f" (e mais {len(erros)-3} erros)"
                
                flash(msg, 'success' if sucesso == total else 'warning')
                
            except Exception as e:
                if conn:
                    conn.rollback()
                flash(f'Erro ao importar: {str(e)}', 'danger')
                app.logger.error(f"Erro na importação: {str(e)}")
            finally:
                if conn and conn.is_connected():
                    cursor.close()
                    conn.close()
            
            return redirect(url_for('listar'))
    
    return render_template('importar_excel.html')

def allowed_excel_file(filename):
    """Verifica se a extensão é permitida para Excel"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}
# Inicialização
if __name__ == '__main__':
    create_upload_folder()
    
    # Verificar conexão com o banco
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Conexão com o banco estabelecida!")
        test_conn.close()
    else:
        print("❌ Falha na conexão com o banco!")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
