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
    password VARCHAR(255) NOT NULL,
    username_acess int not null,
	tentativas int default 0
);

insert into users(username, password, username_acess) values ("admin", "", 0);
drop table users;
/* Username acess 0 significa que ele não está bloqueado, username acess 1 significa que ele está bloqueado. */

update users set
password = "scrypt:32768:8:1$hhzDefW5iNKB67hp$0b660ccad6f5dc3534f32964e93d0767223c014056f42eb26b116923226599f2afd85e909d8a005fd4c58688178a5b82b0bae354331ae706ab1e2780403ab1f3"
where id = 1;

select * from patrimonio;
select * from users;