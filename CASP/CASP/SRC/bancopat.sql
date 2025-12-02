CREATE DATABASE patrimonio;

USE patrimonio;

CREATE TABLE patrimonio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT NOT NULL,
    localizacao VARCHAR(100) NOT NULL,
    condicao VARCHAR(50) NOT NULL,
    origem VARCHAR(50) NOT NULL,
    marca VARCHAR(100),
    codigo_doador VARCHAR(7),
    codigo_cps VARCHAR(7),
    quantidade INT DEFAULT 1,
    imagem VARCHAR(255),
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_cadastro VARCHAR(100)
);


ALTER TABLE patrimonio 
ADD COLUMN data_atualizacao DATETIME NULL AFTER data_cadastro,
ADD COLUMN usuario_atualizacao VARCHAR(100) NULL AFTER usuario_cadastro;

delete from patrimonio where localizacao = "ESTEVAM FERRI";


CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO usuarios (username, password_hash, ativo) 
VALUES ('admin', 'senha123', TRUE);

INSERT INTO usuarios (username, password_hash, ativo) 
VALUES ('EtecIlza', 'senha123', TRUE);

select * from usuarios;

