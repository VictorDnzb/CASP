# CADS
Trabalho de conclusão de curso(CADS), sistema de gestão patrimonial.

Este guia contém instruções detalhadas para clonar, instalar e configurar o sistema em sua máquina local.

Pré-requisitos
Antes de começar, certifique-se de que os seguintes requisitos estejam atendidos:

Python 3.13+ instalado
MySQL Server instalado e configurado
Git instalado para clonar o repositório
Ambiente virtual configurado para Python (opcional, mas recomendado)
Clonando o Repositório
Abra um terminal e navegue até o diretório onde deseja clonar o repositório.
Execute o seguinte comando para clonar o repositório:
   git clone https://github.com/jeancosta4/patrimonio.git
Entre no diretório do projeto:
    cd nome-do-repositorio
Instalando o Ambiente
Configurando o Ambiente Virtual (Recomendado) Crie um ambiente virtual:

python -m venv venv
Ative o ambiente virtual: 4.1 No Windows:
venv\Scripts\activate
4.2 No Linux/Mac:

source venv/bin/activate
Instalando as Dependências Instale as dependências do projeto:
pip install -r requirements.txt
Configuração do Banco de Dados
Crie um banco de dados MySQL para o sistema: Execute o arquivo db_setup.sql no Mysql.

Inicie o servidor Flask:
flask run
Acesse o sistema no navegador: http://127.0.0.1:5000
