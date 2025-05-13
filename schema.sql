-- laticinios_armazem/schema.sql

-- Tabela para usuários
CREATE TABLE IF NOT EXISTS usuarios (
    username TEXT PRIMARY KEY,
    senha TEXT NOT NULL,
    funcao TEXT NOT NULL CHECK (funcao IN ('gerente', 'operador')),
    nome TEXT NOT NULL
);

-- Tabela para catálogo de produtos
CREATE TABLE IF NOT EXISTS produtos_catalogo (
    id_produto TEXT PRIMARY KEY,
    nome TEXT NOT NULL
);

-- Tabela para áreas de armazenamento
CREATE TABLE IF NOT EXISTS areas_armazem (
    id_area TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo_armazenamento TEXT NOT NULL CHECK (tipo_armazenamento IN ('refrigerado', 'congelado', 'seco'))
);

-- Tabela para produtos nas áreas (estoque)
CREATE TABLE IF NOT EXISTS produtos_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_area TEXT NOT NULL,
    id_catalogo_produto TEXT NOT NULL,
    nome TEXT NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade >= 0),
    data_validade DATE NOT NULL,
    lote TEXT NOT NULL,
    FOREIGN KEY (id_area) REFERENCES areas_armazem(id_area),
    FOREIGN KEY (id_catalogo_produto) REFERENCES produtos_catalogo(id_produto),
    UNIQUE(id_area, id_catalogo_produto, lote)
);

-- Tabela para vendas
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_catalogo_produto TEXT NOT NULL,
    nome TEXT NOT NULL,
    lote TEXT NOT NULL,
    data_validade_produto TEXT NOT NULL,
    quantidade_vendida INTEGER NOT NULL CHECK (quantidade_vendida > 0),
    destino TEXT NOT NULL,
    area_origem_id TEXT NOT NULL,
    usuario_responsavel TEXT NOT NULL,
    data_hora DATETIME NOT NULL,
    FOREIGN KEY (id_catalogo_produto) REFERENCES produtos_catalogo(id_produto),
    FOREIGN KEY (area_origem_id) REFERENCES areas_armazem(id_area),
    FOREIGN KEY (usuario_responsavel) REFERENCES usuarios(username)
);