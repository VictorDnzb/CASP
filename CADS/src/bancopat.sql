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
select * from users;
insert into users(username) values ("Renata");
update users set
password = "scrypt:32768:8:1$urABZUG4wPkF0OYb$036e124d4ff0f743886c904d49f60c9a241cdf88185f6ad5e4e6ac9fffc256764692ecd1ac6e7f9a08f3048d2972254f4930cc795eda43fd85c863d29e7004e8"
where id = 1;