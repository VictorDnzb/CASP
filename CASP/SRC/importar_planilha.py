# importar_planilha_corrigido.py
import pandas as pd
import mysql.connector
from datetime import datetime
import re

def debug_print(message):
    print(f"🔍 {message}")

def normalizar_condicao(condicao):
    """Normaliza as condições para o padrão do sistema"""
    if pd.isna(condicao) or not condicao:
        return "Bom"
    
    condicao = str(condicao).strip().upper()
    
    if any(termo in condicao for termo in ['ÓTIMO', 'OTIMO', 'EXCELENTE']):
        return "Ótimo"
    elif any(termo in condicao for termo in ['BOM', 'BOA']):
        return "Bom"
    elif any(termo in condicao for termo in ['RECUPERÁVEL', 'RECUPERAVEL', 'REGULAR']):
        return "Recuperável"
    elif any(termo in condicao for termo in ['PÉSSIMO', 'PESSIMO', 'RUIM']):
        return "Péssimo"
    else:
        return "Bom"

def extrair_dados_linha(linha, sheet_name):
    """Extrai dados de uma linha baseado na estrutura identificada"""
    dados = {
        'patrimonio': '',
        'descricao': '',
        'marca': '',
        'local': sheet_name,
        'codigo_doador': '',
        'condicao': 'Bom'
    }
    
    # Converter a linha para lista
    valores = linha.tolist()
    
    # Estratégia 1: Buscar por padrões conhecidos
    for i, valor in enumerate(valores):
        if pd.isna(valor):
            continue
            
        valor_str = str(valor).strip()
        
        # Identificar número de patrimônio (apenas números)
        if valor_str.isdigit() and len(valor_str) >= 4:
            dados['patrimonio'] = valor_str
            dados['origem'] = 'CPS'
        
        # Identificar "NÃO PATRIMONIADOS"
        elif 'NÃO PATRIMONIADOS' in valor_str.upper() or 'NAO PATRIMONIADOS' in valor_str.upper():
            dados['patrimonio'] = 'NÃO PATRIMONIADOS'
            dados['origem'] = 'Doação'
        
        # Identificar condições
        elif any(cond in valor_str.upper() for cond in ['BOM', 'ÓTIMO', 'OTIMO', 'RUIM', 'PÉSSIMO', 'PESSIMO', 'RECUPERÁVEL', 'RECUPERAVEL']):
            dados['condicao'] = normalizar_condicao(valor_str)
        
        # Identificar marcas conhecidas
        elif any(marca in valor_str.upper() for marca in ['MARELLI', 'LENOVO', 'POSITIVO', 'DELL', 'HP', 'SAMSUNG', 'LG', 'EPSON']):
            dados['marca'] = valor_str
        
        # Descrição geral (texto mais longo)
        elif len(valor_str) > 20 and not valor_str.isdigit():
            if not dados['descricao']:
                dados['descricao'] = valor_str
            else:
                dados['descricao'] += " " + valor_str
    
    # Se não encontrou descrição, usar o primeiro texto longo
    if not dados['descricao']:
        for valor in valores:
            if pd.isna(valor):
                continue
            valor_str = str(valor).strip()
            if len(valor_str) > 10 and not valor_str.isdigit() and 'PATRIMONIO' not in valor_str.upper():
                dados['descricao'] = valor_str
                break
    
    return dados

def processar_aba(sheet_name, df):
    """Processa uma aba específica da planilha"""
    debug_print(f"Processando aba: {sheet_name}")
    
    registros = []
    linhas_processadas = 0
    
    for index, linha in df.iterrows():
        # Pular linhas completamente vazias
        if linha.isna().all():
            continue
            
        # Pular linhas de cabeçalho
        linha_str = ' '.join([str(x) for x in linha if pd.notna(x)])
        if any(termo in linha_str.upper() for termo in ['PATRIMONIO', 'DESCRICAO', 'DESCRIÇÃO', 'MARCA', 'LOCAL', 'CONDICAO', 'CONDIÇÃO']):
            continue
        
        # Extrair dados da linha
        dados = extrair_dados_linha(linha, sheet_name)
        
        # Só adicionar se tem dados válidos
        if dados['descricao'] or dados['patrimonio']:
            registros.append(dados)
            linhas_processadas += 1
            
            if linhas_processadas <= 3:  # Debug das primeiras linhas
                debug_print(f"  Linha {index}: {dados}")
    
    debug_print(f"  ✅ {linhas_processadas} registros extraídos")
    return registros

def importar_planilha():
    caminho_planilha = "LEVANTAMENTO 2024.xlsx"
    
    debug_print("Iniciando importação da planilha...")
    
    try:
        # Ler a planilha
        planilha = pd.ExcelFile(caminho_planilha)
        debug_print(f"Abas encontradas: {len(planilha.sheet_names)}")
        
        todos_registros = []
        
        # Processar cada aba (exceto as vazias)
        for sheet_name in planilha.sheet_names:
            if sheet_name in ['Planilha1', 'Planilha2', 'Planilha4', 'Macedo', 'HARDWARE', 'ROBÔ', 'TCC']:
                debug_print(f"⏭️  Pulando aba: {sheet_name}")
                continue
                
            try:
                # Ler a aba
                df = pd.read_excel(planilha, sheet_name=sheet_name)
                
                # Processar apenas se tiver dados
                if not df.empty and len(df) > 1:
                    registros_aba = processar_aba(sheet_name, df)
                    todos_registros.extend(registros_aba)
                    
            except Exception as e:
                debug_print(f"❌ Erro na aba {sheet_name}: {e}")
                continue
        
        debug_print(f"\n📊 Total de registros extraídos: {len(todos_registros)}")
        
        if not todos_registros:
            debug_print("❌ Nenhum registro válido encontrado")
            return
        
        # Conectar ao banco
        debug_print("Conectando ao banco de dados...")
        conexao = mysql.connector.connect(
            host="localhost", 
            user="root", 
            password="", 
            database="patrimonio"
        )
        cursor = conexao.cursor()
        
        # Inserir no banco
        inseridos = 0
        for i, registro in enumerate(todos_registros, 1):
            try:
                # Preparar dados
                nome = registro['descricao'] if registro['descricao'] else f"Item {i}"
                patrimonio = registro['patrimonio']
                
                # Determinar origem e códigos
                if patrimonio == 'NÃO PATRIMONIADOS':
                    origem = 'Doação'
                    codigo_cps = ''
                    codigo_doador = patrimonio
                else:
                    origem = 'CPS' if patrimonio else 'Doação'
                    codigo_cps = patrimonio if patrimonio and patrimonio != 'NÃO PATRIMONIADOS' else ''
                    codigo_doador = ''
                
                # Inserir no banco
                cursor.execute("""
                    INSERT INTO patrimonio (
                        nome, descricao, localizacao, condicao, origem, 
                        marca, codigo_doador, codigo_cps, quantidade, 
                        usuario_cadastro, data_cadastro
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    nome, nome, registro['local'], registro['condicao'], origem,
                    registro['marca'], codigo_doador, codigo_cps,
                    1, "importador_planilha", datetime.now()
                ))
                
                inseridos += 1
                
                if inseridos % 50 == 0:  # Feedback a cada 50 registros
                    debug_print(f"📦 {inseridos} registros inseridos...")
                    
            except Exception as e:
                debug_print(f"❌ Erro no registro {i}: {e}")
                continue
        
        conexao.commit()
        debug_print(f"✅ Importação concluída! {inseridos} registros inseridos no banco")
        
        cursor.close()
        conexao.close()
        
        # Estatísticas finais
        debug_print("\n📈 ESTATÍSTICAS FINAIS:")
        condicoes = {}
        locais = {}
        for registro in todos_registros[:inseridos]:  # Apenas os inseridos
            condicoes[registro['condicao']] = condicoes.get(registro['condicao'], 0) + 1
            locais[registro['local']] = locais.get(registro['local'], 0) + 1
        
        debug_print("Condições:")
        for cond, count in condicoes.items():
            debug_print(f"  {cond}: {count}")
            
        debug_print("Locais mais comuns:")
        for local, count in list(sorted(locais.items(), key=lambda x: x[1], reverse=True))[:5]:
            debug_print(f"  {local}: {count}")
        
    except Exception as e:
        debug_print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    importar_planilha()
