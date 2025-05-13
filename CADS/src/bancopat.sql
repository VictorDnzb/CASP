drop database patrimonio; 

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
    codigo_doador VARCHAR(100),
    codigo_cps VARCHAR(100),
    quantidade INT DEFAULT 1,
    imagem VARCHAR(255),
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_cadastro VARCHAR(100)
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

select * from patrimonio;